from necroassembler.tokenizer import Tokenizer
from necroassembler.utils import (pack_byte, pack_le32u, pack_le16u,
                                  pack_be32u, pack_be16u, in_bit_range,
                                  in_bit_range_decimal, pack_bits, is_valid_name)
from necroassembler.exceptions import (UnknownLabel, UnsupportedNestedMacro, NotInMacroRecordingMode,
                                       AddressOverlap, NegativeSignNotAllowed, NotInRepeatMode,
                                       UnsupportedNestedRepeat,
                                       AlignmentError, NotInBitRange, OnlyForwardAddressesAllowed,
                                       InvalidArgumentsForDirective, LabelNotAllowed, InvalidDefine,
                                       SectionAlreadyDefined, SymbolAlreadyExported)
from necroassembler.macros import Macro
from necroassembler.linker import Dummy


def opcode(*name):
    def wrapper(f):
        f.opcode = name
        return f
    return wrapper


def directive(*name):
    def wrapper(f):
        f.directive = name
        return f
    return wrapper


def pre_link(f):
    f.pre_link = True
    return f


def post_link(f):
    f.post_link = True
    return f


class LabelData:

    alignment = 1
    offset = 0
    bits = None
    hook = None
    filter = None

    def __init__(self, label, size, bits_size, relative):
        self.label = label
        self.size = size
        self.bits_size = bits_size
        self.relative = relative


class Assembler:

    hex_prefixes = ()
    hex_suffixes = ()
    bin_prefixes = ()
    bin_suffixes = ()
    oct_prefixes = ()
    oct_suffixes = ()
    dec_prefixes = ()
    dec_suffixes = ()

    case_sensitive = False

    fill_value = 0

    big_endian = False

    defines = {}

    def __init__(self):
        self.instructions = {}
        self.directives = {}
        self.assembled_bytes = bytearray()
        self.labels = {}
        self.pre_link_passes = []
        self.post_link_passes = []
        self.current_org = 0x00
        self.current_org_end = 0
        self.org_counter = 0
        self.labels_addresses = {}
        self.macros = {}
        self.macro_recording = None
        self.repeat = None
        self.log = False
        self.sections = {}
        self.current_section = None
        self.exports = []

        # avoid subclasses to overwrite parent
        # class variables by making a copy
        self.defines = self.defines.copy()
        self.hex_prefixes = tuple(self.hex_prefixes)
        self.hex_suffixes = tuple(self.hex_suffixes)
        self.bin_prefixes = tuple(self.bin_prefixes)
        self.bin_suffixes = tuple(self.bin_suffixes)
        self.oct_prefixes = tuple(self.oct_prefixes)
        self.oct_suffixes = tuple(self.oct_suffixes)
        self.dec_prefixes = tuple(self.dec_prefixes)
        self.dec_suffixes = tuple(self.dec_suffixes)

        self._register_internal_directives()
        self._discover()

        self.register_defines()
        self.register_directives()
        self.register_instructions()

    def _register_internal_directives(self):
        self.register_directive('macro', self.macro_start)
        self.register_directive('endmacro', self.macro_end)
        self.register_directive('org', self.directive_org)
        self.register_directive('include', self.directive_include)
        self.register_directive('incbin', self.directive_incbin)
        self.register_directive('inccsv', self.directive_inccsv)
        self.register_directive('inccsv_le16', self.directive_inccsv_le16)
        self.register_directive('incjson', self.directive_incjson)
        self.register_directive('define', self.directive_define)
        self.register_directive('db', self.directive_db)
        self.register_directive('byte', self.directive_db)
        self.register_directive('dw', self.directive_dw)
        self.register_directive('word', self.directive_dw)
        self.register_directive('dd', self.directive_dd)
        self.register_directive('dl', self.directive_dd)
        self.register_directive('dword', self.directive_dd)
        self.register_directive('db_to_ascii', self.directive_db_to_ascii)
        self.register_directive('dw_to_ascii', self.directive_dw_to_ascii)
        self.register_directive('db_to_asciiz', self.directive_db_to_asciiz)
        self.register_directive('dw_to_asciiz', self.directive_dw_to_asciiz)
        self.register_directive('fill', self.directive_fill)
        self.register_directive('ram', self.directive_ram)
        self.register_directive('log', self.directive_log)
        self.register_directive('align', self.directive_align)
        self.register_directive('repeat', self.directive_repeat)
        self.register_directive('endrepeat', self.directive_end_repeat)
        self.register_directive('goto', self.directive_goto)
        self.register_directive('upto', self.directive_upto)
        self.register_directive('section', self.directive_section)
        self.register_directive('export', self.directive_export)

    def register_directives(self):
        pass

    def register_defines(self):
        pass

    def _discover(self):

        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr):
                if hasattr(attr, 'opcode'):
                    for symbol in attr.opcode:
                        self.register_instruction(symbol, attr)
                if hasattr(attr, 'directive'):
                    for symbol in attr.directive:
                        self.register_directive(symbol, attr)
                if hasattr(attr, 'pre_link'):
                    if attr.pre_link:
                        self.pre_link_passes.append(attr)
                if hasattr(attr, 'post_link'):
                    if attr.post_link:
                        self.post_link_passes.append(attr)

    def register_instructions(self):
        pass

    def macro_start(self, instr):
        if self.macro_recording is not None:
            raise UnsupportedNestedMacro(instr)
        self.macro_recording = Macro(instr.tokens[1:])
        key = instr.tokens[1]
        if not self.case_sensitive:
            key = key.upper()
        self.macros[key] = self.macro_recording

    def macro_end(self, instr):
        if self.macro_recording is None:
            raise NotInMacroRecordingMode(instr)
        self.macro_recording = None

    def assemble(self, code, context=None):
        tokenizer = Tokenizer(context=context)
        tokenizer.parse(code)

        for statement in tokenizer.statements:
            current_index = len(self.assembled_bytes)
            statement.assemble(self)
            if self.log:
                new_index = len(self.assembled_bytes)
                if new_index == current_index:
                    print('not assembled {0}'.format(statement))
                else:
                    print('assembled {0} -> ({1}) at 0x{2:x}'.format(statement,
                                                                     ','.join(['0x{0:02x}'.format(x) for x in self.assembled_bytes[current_index:]]), current_index))

        # check if we need to fill something
        if self.current_org_end > 0:
            if self.current_org + self.org_counter < self.current_org_end:
                blob = bytes([self.fill_value] * ((self.current_org_end + 1) -
                                                  (self.current_org + self.org_counter)))
                self.append_assembled_bytes(blob)

        # fix opened section
        if self.current_section:
            self.sections[self.current_section]['end'] = self.pc
            self.sections[self.current_section]['size'] = len(
                self.assembled_bytes) - self.sections[self.current_section]['offset']

    def assemble_file(self, filename):
        with open(filename) as f:
            self.assemble(f.read(), filename)

    def save(self, filename):
        with open(filename, 'wb') as handle:
            handle.write(self.assembled_bytes)

    def _resolve_labels(self, linker):
        for address in self.labels_addresses:
            data = self.labels_addresses[address]
            label = data.label
            is_relative = data.relative != 0

            absolute_address = self.get_label_absolute_address_by_name(label)
            if not is_relative:
                true_address = absolute_address
            else:
                true_address = self.get_label_relative_address_by_name(
                    label, data.relative)

            if true_address is None:
                true_address = linker.resolve_unknown_symbol(
                    self, address, data)
                absolute_address = true_address

            if data.hook:
                data.hook(address, true_address)
                continue

            if absolute_address % data.alignment != 0:
                raise AlignmentError(label)

            size = data.size
            total_bits = data.bits_size

            if not is_relative and true_address < 0:
                raise OnlyForwardAddressesAllowed(label, true_address)

            if not in_bit_range_decimal(true_address, total_bits, signed=is_relative):
                raise NotInBitRange(true_address, total_bits, label)

            if data.filter:
                true_address = data.filter(true_address)

            if data.bits:
                true_address = pack_bits(0, (data.bits, true_address))

            for i in range(0, size):
                value = (true_address >> (8 * i)) & 0xFF
                if self.big_endian:
                    self.assembled_bytes[address + ((size-1) - i)] |= value
                else:
                    self.assembled_bytes[address + i] |= value

            if self.log:
                print('label "{0}" translated to ({1}) at address {2}'.format(
                    label, ','.join(['0x{0:02x}'.format(x) for x in self.assembled_bytes[address:address+size]]), hex(address)))


    def link(self, linker=None):

        if not linker:
            linker = Dummy()

        for _pass in self.pre_link_passes:
            if hasattr(_pass, '__self__') and _pass.__self__ == self:
                _pass()
            else:
                _pass(self)

        self._resolve_labels(linker)

        for _pass in self.post_link_passes:
            if hasattr(_pass, '__self__') and _pass.__self__ == self:
                _pass()
            else:
                _pass(self)

        self.assembled_bytes = linker.link(self)

    @property
    def pc(self):
        return self.current_org + self.org_counter

    def add_label_translation(self, label,
                              size, bits_size,
                              offset=0, alignment=1, bits=None, filter=None,
                              relative=0, hook=None):
        index = len(self.assembled_bytes) + offset
        label_data = LabelData(label, size, bits_size, relative)
        label_data.offset = offset
        label_data.alignment = alignment
        label_data.bits = bits
        label_data.hook = hook
        label_data.filter = filter
        self.labels_addresses[index] = label_data

    def _internal_parse_integer(self, token):
        # first check for an ascii char
        if token[0] == '\'' and token[2] == '\'':
            return ord(token[1:2]), False

        for prefix in self.hex_prefixes:
            if token.startswith(prefix):
                return int(token[len(prefix):], 16), False

        for prefix in self.bin_prefixes:
            if token.startswith(prefix):
                return int(token[len(prefix):], 2), False

        for prefix in self.oct_prefixes:
            if token.startswith(prefix):
                return int(token[len(prefix):], 8), False

        for prefix in self.dec_prefixes:
            if token.startswith(prefix):
                return int(token[len(prefix):], 10), True

        for suffix in self.hex_suffixes:
            if token.endswith(suffix):
                if token[:-len(suffix)].isdigit():
                    return int(token[0:-len(suffix)], 16), False

        for suffix in self.bin_suffixes:
            if token.endswith(suffix):
                if token[:-len(suffix)].isdigit():
                    return int(token[0:-len(suffix)], 2), False

        for suffix in self.oct_suffixes:
            if token.endswith(suffix):
                if token[:-len(suffix)].isdigit():
                    return int(token[0:-len(suffix)], 8), False

        for suffix in self.dec_suffixes:
            if token.endswith(suffix):
                if token[:-len(suffix)].isdigit():
                    return int(token[0:-len(suffix)], 10), True

        try:
            return int(token), True
        except ValueError:
            return None, False

    def parse_integer(self, token, number_of_bits, signed):
        token, pre_formula, post_formula = self._get_math_formula(token)
        value, decimal = self._internal_parse_integer(token)
        if value is None:
            return None
        value = self.apply_math_formula(pre_formula, post_formula, value)

        # check for invalid combos
        if not decimal and value < 0:
            raise NegativeSignNotAllowed()
        # fix negative values
        if decimal:
            if not signed:
                if value < 0:
                    max_value = pow(2, number_of_bits)
                    value += max_value
                    if value < max_value // 2:
                        raise NotInBitRange(value, number_of_bits)
            else:
                if not in_bit_range_decimal(value, number_of_bits, signed=True):
                    raise NotInBitRange(value, number_of_bits)
                return value

        if not in_bit_range(value, number_of_bits):
            raise NotInBitRange(value, number_of_bits)
        return value

    def parse_integer_or_label(self, label,
                               size, bits_size, relative=0,
                               offset=0, alignment=1, bits=None, filter=None,
                               hook=None, signed=False):
        if relative != 0:
            signed = True
        value = self.parse_integer(label, bits_size, signed)
        # label ?
        if value is None:
            self.add_label_translation(label=label,
                                       size=size,
                                       bits_size=bits_size,
                                       relative=relative,
                                       offset=offset,
                                       alignment=alignment,
                                       bits=bits,
                                       filter=filter,
                                       hook=hook)
            return 0
        return value

    def apply_math_formula(self, pre_formula, post_formula, value):
        low_counter = 0
        shifted_value = 0
        has_shifted_value = False

        for op in pre_formula:
            if op == '>':
                value >>= 8
            elif op == '<':
                shifted_value |= ((value >> (8 * low_counter))
                                  & 0xFF) << (8 * low_counter)
                low_counter += 1
                has_shifted_value = True

        if has_shifted_value:
            value = shifted_value

        ops = []
        current_command = None
        current_arg = ''
        for char in post_formula:
            if char in ('+', '-', '*', '/', '&', '|'):
                if current_command is not None:
                    ops.append((current_command, current_arg))
                current_command = char
                current_arg = ''
            else:
                current_arg += char

        if current_command is not None:
            ops.append((current_command, current_arg))

        for command, arg in ops:
            arg_value = 1
            if arg:
                arg_value = self.parse_integer(arg, 64, False)
                if arg_value is None:
                    arg_value = self.get_label_absolute_address_by_name(arg)
                    if arg_value is None:
                        raise UnknownLabel(arg)
            if command == '+':
                value += arg_value
            elif command == '-':
                value -= arg_value
            elif command == '*':
                value *= arg_value
            elif command == '/':
                value //= arg_value
            elif command == '&':
                value &= arg_value
            elif command == '|':
                value |= arg_value

        return value

    def get_label_absolute_address(self, label):
        return label['org'] + label['base']

    def get_label_absolute_address_by_name(self, name):
        name, pre_formula, post_formula = self._get_math_formula(name)
        if not name in self.labels:
            return None
        return self.apply_math_formula(pre_formula, post_formula, self.get_label_absolute_address(self.labels[name]))

    def get_label_relative_address(self, label, start):
        return self.get_label_absolute_address(label) - start

    def get_label_relative_address_by_name(self, name, start):
        name, pre_formula, post_formula = self._get_math_formula(name)
        if not name in self.labels:
            return None
        return self.apply_math_formula(pre_formula, post_formula, self.get_label_relative_address(self.labels[name], start))

    def change_org(self, start, end=0):

        if end > 0 and end < start:
            raise AddressOverlap()

        previous_org = self.current_org
        previous_org_end = self.current_org_end
        previous_org_counter = self.org_counter

        self.current_org = start
        self.current_org_end = end
        self.org_counter = 0
        # check if need to fill
        if previous_org_end > 0:
            # overlap check:
            if previous_org + previous_org_counter > self.current_org:
                raise AddressOverlap()
            # NOTE: we have to NOT set org_counter here! (leave it as 0, as this is a new one .org)
            # new org is is higher than the previous end
            if self.current_org > previous_org_end:
                blob = bytes([self.fill_value] * ((previous_org_end + 1) -
                                                  (previous_org + previous_org_counter)))
                self.assembled_bytes += blob
            # new org is lower than previous end but higher than previous start
            elif self.current_org <= previous_org_end and self.current_org > previous_org:
                blob = bytes([self.fill_value] * (self.current_org -
                                                  (previous_org + previous_org_counter)))
                self.assembled_bytes += blob
            else:
                raise AddressOverlap()

    def directive_org(self, instr):
        if len(instr.tokens) not in (2, 3):
            raise InvalidArgumentsForDirective(instr)
        new_org_start = self.parse_integer(instr.tokens[1], 64, False)
        if new_org_start is None:
            raise InvalidArgumentsForDirective(instr)
        new_org_end = 0
        if len(instr.tokens) == 3:
            new_org_end = self.parse_integer(instr.tokens[2], 64, False)
            if new_org_end is None:
                raise InvalidArgumentsForDirective(instr)

        self.change_org(new_org_start, new_org_end)

    def directive_define(self, instr):
        if len(instr.tokens) != 3:
            raise InvalidArgumentsForDirective(instr)
        self.defines[instr.tokens[1]] = instr.tokens[2]

    def append_assembled_bytes(self, blob):
        self.assembled_bytes += blob
        self.org_counter += len(blob)

    def directive_dw(self, instr):
        for token in instr.tokens[1:]:
            blob = b''
            if token[0] in ('"', '\''):
                blob = token[1:-1].encode('utf16')
            else:
                value = self.parse_integer_or_label(
                    label=token, bits_size=16, size=2)
                if self.big_endian:
                    blob = pack_be16u(value)
                else:
                    blob = pack_le16u(value)
            self.append_assembled_bytes(blob)

    def directive_dd(self, instr):
        for token in instr.tokens[1:]:
            blob = b''
            if token[0] in ('"', '\''):
                blob = token[1:-1].encode('utf32')
            else:
                value = self.parse_integer_or_label(
                    label=token, bits_size=32, size=4)
                if self.big_endian:
                    blob = pack_be32u(value)
                else:
                    blob = pack_le32u(value)
            self.append_assembled_bytes(blob)

    def directive_dw_to_ascii(self, instr):
        def dw_to_str(address, true_address):
            blob = format(true_address, '05d').encode('ascii')
            for b in blob:
                self.assembled_bytes[address] = b
                address += 1

        for token in instr.tokens[1:]:
            if token[0] in ('"', '\''):
                blob = str(int(token[1:-1].encode('utf16'))).encode('ascii')
            else:
                value = self.parse_integer(token, 16, False)
                if value is None:
                    self.add_label_translation(
                        label=token, bits_size=16, size=2, hook=dw_to_str)
                    blob = bytes(5)
                else:
                    blob = str(value).encode('ascii')
            self.append_assembled_bytes(blob)

    def directive_dw_to_asciiz(self, instr):
        self.directive_dw_to_ascii(instr)
        self.append_assembled_bytes(b'\x00')

    def directive_log(self, instr):
        if len(instr.tokens) > 1:
            if instr.tokens[1].upper() == 'ON':
                self.log = True
            elif instr.tokens[1].upper() == 'OFF':
                self.log = False
            else:
                InvalidArgumentsForDirective()
        else:
            self.log = True

    def directive_fill(self, instr):
        if len(instr.tokens) not in (2, 3):
            raise InvalidArgumentsForDirective(instr)
        size = self.parse_integer(instr.tokens[1], 64, False)
        if size is None:
            raise InvalidArgumentsForDirective(instr)
        value = self.fill_value
        if len(instr.tokens) == 3:
            value = self.parse_integer(instr.tokens[2], 8, False)
            if value is None:
                raise InvalidArgumentsForDirective(instr)
        blob = bytes([value] * size)
        self.append_assembled_bytes(blob)

    def directive_goto(self, instr):
        if len(instr.tokens) not in (2, 3):
            raise InvalidArgumentsForDirective(instr)
        offset = self.parse_integer(instr.tokens[1], 64, False)
        if offset is None:
            raise InvalidArgumentsForDirective(instr)
        if offset < len(self.assembled_bytes):
            raise AddressOverlap(instr)
        value = self.fill_value
        if len(instr.tokens) == 3:
            value = self.parse_integer(instr.tokens[2], 8, False)
            if value is None:
                raise InvalidArgumentsForDirective(instr)
        blob = bytes([value] * (offset - self.pc))
        self.append_assembled_bytes(blob)

    def directive_upto(self, instr):
        if len(instr.tokens) not in (2, 3):
            raise InvalidArgumentsForDirective(instr)
        offset = self.parse_integer(instr.tokens[1], 64, False)
        if offset is None:
            raise InvalidArgumentsForDirective(instr)
        if offset < len(self.assembled_bytes):
            raise AddressOverlap(instr)
        value = self.fill_value
        if len(instr.tokens) == 3:
            value = self.parse_integer(instr.tokens[2], 8, False)
            if value is None:
                raise InvalidArgumentsForDirective(instr)
        blob = bytes([value] * (offset - (self.pc - self.current_org)))
        self.append_assembled_bytes(blob)

    def directive_ram(self, instr):
        if len(instr.tokens) != 2:
            raise InvalidArgumentsForDirective(instr)
        size = self.parse_integer(instr.tokens[1], 64, False)
        if size is None or size < 1:
            raise InvalidArgumentsForDirective(instr)
        self.org_counter += size

    def directive_align(self, instr):
        if len(instr.tokens) != 2:
            raise InvalidArgumentsForDirective(instr)
        size = self.parse_integer(instr.tokens[1], 64, False)
        if size is None:
            raise InvalidArgumentsForDirective(instr)

        mod = (self.current_org + self.org_counter) % size
        if mod != 0:
            blob = bytes([self.fill_value]) * (size - mod)
            self.append_assembled_bytes(blob)

    def directive_repeat(self, instr):
        if self.repeat is not None:
            raise UnsupportedNestedRepeat(instr)
        if len(instr.tokens) != 2:
            raise InvalidArgumentsForDirective(instr)
        size = self.parse_integer(instr.tokens[1], 64, False)
        if size is None or size <= 0:
            raise InvalidArgumentsForDirective(instr)

        self.repeat = (size, len(self.assembled_bytes))

    def directive_end_repeat(self, instr):
        if self.repeat is None:
            raise NotInRepeatMode(instr)

        size, index = self.repeat
        self.repeat = None
        blob = self.assembled_bytes[index:]
        for i in range(0, size-1):
            self.append_assembled_bytes(blob)

    def directive_db_to_ascii(self, instr):
        def db_to_str(address, true_address):
            blob = format(true_address, '03d').encode('ascii')
            for b in blob:
                self.assembled_bytes[address] = b
                address += 1

        for token in instr.tokens[1:]:
            if token[0] in ('"', '\''):
                blob = str(int(token[1:-1].encode('ascii'))).encode('ascii')
            else:
                value = self.parse_integer(token, 8, False)
                if value is None:
                    self.add_label_translation(
                        label=token, bits_size=8, size=1, hook=db_to_str)
                    blob = bytes(3)
                else:
                    blob = str(value).encode('ascii')
            self.append_assembled_bytes(blob)

    def directive_db_to_asciiz(self, instr):
        self.directive_db_to_ascii(instr)
        self.append_assembled_bytes(b'\x00')

    def parse_bytes_or_ascii(self, tokens):
        blob = b''
        for token in tokens:
            if token[0] in ('"', '\''):
                blob += token[1:-1].encode('ascii')
            else:
                value = self.parse_integer(token, 8, False)
                if value is None:
                    raise LabelNotAllowed()
                blob += pack_byte(value)
        return blob

    def directive_db(self, instr):
        for token in instr.tokens[1:]:
            if token[0] in ('"', '\''):
                blob = token[1:-1].encode('ascii')
            else:
                value = self.parse_integer_or_label(
                    label=token, bits_size=8, size=1)
                blob = pack_byte(value)
            self.append_assembled_bytes(blob)

    def stringify(self, value):
        if value[0] in ('"', '\''):
            value = value[1:-1]
        return value

    def directive_include(self, instr):
        if len(instr.tokens) != 2:
            raise InvalidArgumentsForDirective(instr)
        filename = self.stringify(instr.tokens[1])
        with open(filename) as f:
            self.assemble(f.read(), context=filename)

    def directive_incbin(self, instr):
        if len(instr.tokens) != 2:
            raise InvalidArgumentsForDirective(instr)
        filename = self.stringify(instr.tokens[1])
        with open(filename, 'rb') as f:
            blob = f.read()
            self.append_assembled_bytes(blob)

    def directive_section(self, instr):
        if len(instr.tokens) not in (3, 4):
            raise InvalidArgumentsForDirective(instr)
        name = self.stringify(instr.tokens[1])
        if name in self.sections:
            raise SectionAlreadyDefined(instr)
        permissions = instr.tokens[2]
        if not all([True if letter in 'RWXE' else False for letter in permissions]):
            raise InvalidArgumentsForDirective(instr)
        if len(instr.tokens) == 4:
            new_org_start = self.parse_integer(instr.tokens[3], 64, False)
            if new_org_start is None:
                raise InvalidArgumentsForDirective(instr)
            self.change_org(new_org_start, 0)
        if self.current_section:
            self.sections[self.current_section]['end'] = self.pc
            self.sections[self.current_section]['size'] = len(
                self.assembled_bytes) - self.sections[self.current_section]['offset']
        self.current_section = name
        self.sections[self.current_section] = {
            'start': self.pc, 'offset': len(self.assembled_bytes), 'permissions': permissions}

    def directive_export(self, instr):
        if len(instr.tokens) != 2:
            raise InvalidArgumentsForDirective(instr)
        name = self.stringify(instr.tokens[1])
        if name in self.exports:
            raise SymbolAlreadyExported(instr)
        self.exports.append(name)

    def directive_inccsv(self, instr):
        if len(instr.tokens) != 2:
            raise InvalidArgumentsForDirective(instr)
        import csv
        filename = self.stringify(instr.tokens[1])
        blob = b''
        with open(filename, 'r') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                for column in row:
                    value = self.parse_integer(column, 8, False)
                    if value is None:
                        raise LabelNotAllowed(instr)
                    blob += bytes((value,))

        self.append_assembled_bytes(blob)

    def directive_inccsv_le16(self, instr):
        if len(instr.tokens) != 2:
            raise InvalidArgumentsForDirective(instr)
        import csv
        filename = self.stringify(instr.tokens[1])
        blob = b''
        with open(filename, 'r') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                for column in row:
                    value = self.parse_integer(column, 16, False)
                    if value is None:
                        raise LabelNotAllowed(instr)
                    blob += pack_le16u(value)

        self.append_assembled_bytes(blob)

    def directive_incjson(self, instr):
        if len(instr.tokens) != 3:
            raise InvalidArgumentsForDirective(instr)
        import json
        filename = self.stringify(instr.tokens[1])
        key = self.stringify(instr.tokens[2])
        blob = b''
        with open(filename, 'rb') as f:
            parsed = json.load(f)
            keys = key.split('.')
            for key_part in keys:
                parsed = parsed[key_part]
            for item in parsed:
                if not isinstance(item, int):
                    item = self.parse_integer(item, 8, False)
                    if item is None:
                        raise LabelNotAllowed(instr)
                blob += bytes((item,))

        self.append_assembled_bytes(blob)

    def _get_math_formula(self, token):
        pre_formula = ''
        post_formula = ''
        for char in token:
            if char in ('<', '>'):
                pre_formula += char
            else:
                break

        in_math = False
        valid_chars = 0
        for char in token[len(pre_formula):]:
            if not in_math:
                if char in ('+', '-', '*', '/', '&', '|'):
                    if valid_chars < 1:
                        break
                    in_math = True
                    post_formula += char
                else:
                    valid_chars += 1
            else:
                post_formula += char

        if len(post_formula) > 0:
            return token[len(pre_formula):len(token)-len(post_formula)], pre_formula, post_formula

        return token[len(pre_formula):], pre_formula, post_formula

    def register_instruction(self, code, logic):
        key = code
        if not self.case_sensitive:
            key = key.upper()
        self.instructions[key] = logic

    def register_directive(self, name, logic):
        key = name
        if not self.case_sensitive:
            key = key.upper()
        self.directives[key] = logic

    def register_define(self, name, value):
        if not is_valid_name(name):
            raise InvalidDefine()
        self.defines[name] = value

    @classmethod
    def main(cls, pre_link_passes=[], post_link_passes=[], linker=None):
        import sys
        import os
        try:
            *sources, destination = sys.argv[1:]
        except ValueError:
            print('usage: {0} <sources> <destination>'.format(
                os.path.basename(sys.argv[0])))
            return
        asm = cls()
        asm.pre_link_passes += pre_link_passes
        asm.post_link_passes += post_link_passes
        for source in sources:
            asm.assemble_file(source)
        asm.link(linker=linker)
        asm.save(destination)
