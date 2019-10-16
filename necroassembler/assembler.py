from necroassembler.tokenizer import Tokenizer
from necroassembler.utils import pack, pack_byte, pack_le32u, pack_le16u, in_bit_range_signed, in_bit_range, pack_bits
from necroassembler.exceptions import (UnknownLabel, UnsupportedNestedMacro, NotInMacroRecordingMode, AddressOverlap,
                                       AlignmentError, NotInBitRange, OnlyForwardAddressesAllowed, InvalidArgumentsForDirective)
from necroassembler.macros import Macro


def opcode(name):
    def wrapper(f):
        f.opcode = name
        return f
    return wrapper


class Assembler:

    hex_prefixes = ()
    hex_suffixes = ()
    bin_prefixes = ()
    bin_suffixes = ()
    oct_prefixes = ()
    oct_suffixes = ()
    dec_prefixes = ()
    dec_suffixes = ()

    special_prefixes = ()
    special_suffixes = ()

    case_sensitive = False

    fill_value = 0

    def __init__(self):
        self.instructions = {}
        self.directives = {}
        self.defines = {}
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
        self.log = False

        self.register_directives()
        self.register_defines()
        self._discover_instructions()
        self.register_instructions()

    def register_directives(self):
        self.register_directive('macro', self.macro_start)
        self.register_directive('endmacro', self.macro_end)
        self.register_directive('org', self.directive_org)
        self.register_directive('include', self.directive_include)
        self.register_directive('incbin', self.directive_incbin)
        self.register_directive('define', self.directive_define)
        self.register_directive('db', self.directive_db)
        self.register_directive('byte', self.directive_db)
        self.register_directive('dw', self.directive_dw)
        self.register_directive('word', self.directive_dw)
        self.register_directive('dd', self.directive_dd)
        self.register_directive('dword', self.directive_dd)
        self.register_directive('db_to_ascii', self.directive_db_to_ascii)
        self.register_directive('dw_to_ascii', self.directive_dw_to_ascii)
        self.register_directive('db_to_asciiz', self.directive_db_to_asciiz)
        self.register_directive('dw_to_asciiz', self.directive_dw_to_asciiz)
        self.register_directive('fill', self.directive_fill)
        self.register_directive('log', self.directive_log)
        self.register_directive('align', self.directive_align)

    def register_defines(self):
        pass

    def _discover_instructions(self):
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, 'opcode'):
                self.register_instruction(attr.opcode, attr)

    def register_instructions(self):
        pass

    def macro_start(self, instr):
        if self.macro_recording is not None:
            raise UnsupportedNestedMacro()
        self.macro_recording = Macro(instr.tokens[1:])
        key = instr.tokens[1]
        if not self.case_sensitive:
            key = key.upper()
        self.macros[key] = self.macro_recording

    def macro_end(self, instr):
        if self.macro_recording is None:
            raise NotInMacroRecordingMode()
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
                self.assembled_bytes += blob
                self.org_counter += len(blob)

    def assemble_file(self, filename):
        with open(filename) as f:
            self.assemble(f.read(), filename)

    def save(self, filename):
        with open(filename, 'wb') as handle:
            handle.write(self.assembled_bytes)

    def _resolve_labels(self):
        for address in self.labels_addresses:
            data = self.labels_addresses[address]
            label = data['label']
            relative = data.get('relative', False)

            absolute_address = self.get_label_absolute_address_by_name(label)
            if not relative:
                true_address = absolute_address
            else:
                true_address = self.get_label_relative_address_by_name(
                    label, data['start'])

            if true_address is None:
                raise UnknownLabel(label)

            if 'hook' in data:
                data['hook'](address, true_address)
                continue

            if 'filter' in data:
                true_address = data['filter'](true_address)

            if 'alignment' in data:
                if absolute_address % data['alignment'] != 0:
                    raise AlignmentError(label)

            size = data['size']
            total_bits = size * 8

            if 'bits' in data:
                total_bits = data['bits'][0] - data['bits'][1] + 1

            bits_to_check = data.get('bits_check', total_bits)

            if relative:
                if not in_bit_range_signed(true_address, bits_to_check):
                    raise NotInBitRange(true_address, bits_to_check, label)
            else:
                if true_address < 0 or not in_bit_range(true_address, bits_to_check):
                    raise NotInBitRange(true_address, bits_to_check, label)

            if 'post_filter' in data:
                true_address = data['post_filter'](true_address)

            if 'bits' in data:
                true_address = pack_bits(
                    0, (data['bits'], true_address, relative), check_bits='bits_check' not in data)

            for i in range(0, size):
                value = (true_address >> (8 * i)) & 0xFF
                self.assembled_bytes[address + i] |= value

    def link(self):

        for _pass in self.pre_link_passes:
            _pass()

        self._resolve_labels()

        for _pass in self.post_link_passes:
            _pass()

    def add_label_translation(self, **kwargs):
        index = len(self.assembled_bytes) + kwargs.get('offset', 1)
        self.labels_addresses[index] = kwargs

    def _internal_parse_integer(self, token):
        for prefix in self.hex_prefixes:
            if token.startswith(prefix):
                return int(token[len(prefix):], 16)

        for prefix in self.bin_prefixes:
            if token.startswith(prefix):
                return int(token[len(prefix):], 2)

        for prefix in self.oct_prefixes:
            if token.startswith(prefix):
                return int(token[len(prefix):], 8)

        for prefix in self.dec_prefixes:
            if token.startswith(prefix):
                return int(token[len(prefix):], 10)

        for suffix in self.hex_suffixes:
            if token.endswith(suffix):
                if token[:-len(suffix)].isdigit():
                    return int(token[0:-len(suffix)], 16)

        for suffix in self.bin_suffixes:
            if token.endswith(suffix):
                if token[:-len(suffix)].isdigit():
                    return int(token[0:-len(suffix)], 2)

        for suffix in self.oct_suffixes:
            if token.endswith(suffix):
                if token[:-len(suffix)].isdigit():
                    return int(token[0:-len(suffix)], 8)

        for suffix in self.dec_suffixes:
            if token.endswith(suffix):
                if token[:-len(suffix)].isdigit():
                    return int(token[0:-len(suffix)], 10)

        try:
            return int(token)
        except ValueError:
            return None

    def parse_integer(self, token):
        token, pre_formula, post_formula = self._get_math_formula(token)
        value = self._internal_parse_integer(token)
        if value is None:
            return None
        return self.apply_math_formula(pre_formula, post_formula, value)

    def parse_integer_or_label(self, arg, **kwargs):
        value = self.parse_integer(arg)
        # label ?
        if value is None:
            self.add_label_translation(label=arg, **kwargs)
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
                shifted_value |= (value & 0xFF) << (8 * low_counter)
                low_counter += 1
                has_shifted_value = True

        if has_shifted_value:
            value = shifted_value

        for op in post_formula:
            if op == '+':
                value += 1
            elif op == '-':
                value -= 1
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

    def directive_org(self, instr):
        previous_org = self.current_org
        previous_org_end = self.current_org_end
        previous_org_counter = self.org_counter
        if len(instr.tokens) not in (2, 3):
            raise InvalidArgumentsForDirective()
        self.current_org = self.parse_integer(instr.tokens[1])
        if self.current_org is None:
            raise InvalidArgumentsForDirective()
        if len(instr.tokens) == 3:
            self.current_org_end = self.parse_integer(instr.tokens[2])
            if self.current_org_end is None or self.current_org_end < self.current_org:
                raise InvalidArgumentsForDirective()
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
                blob += bytes([self.fill_value] * (self.current_org -
                                                   (previous_org + previous_org_counter)))
                self.assembled_bytes += blob
            else:
                raise AddressOverlap()

    def directive_define(self, instr):
        if len(instr.tokens) != 3:
            raise InvalidArgumentsForDirective()
        self.defines[instr.tokens[1]] = instr.tokens[2]

    def directive_dw(self, instr):
        for token in instr.tokens[1:]:
            blob = b''
            if token[0] in ('"', '\''):
                blob = token[1:-1].encode('utf16')
            else:
                value = self.parse_integer(token)
                if value is None:
                    self.add_label_translation(label=token, size=2, offset=0)
                blob = pack_le16u(value)
            self.assembled_bytes += blob
            self.org_counter += len(blob)

    def directive_dd(self, instr):
        for token in instr.tokens[1:]:
            blob = b''
            if token[0] in ('"', '\''):
                blob = token[1:-1].encode('utf32')
            else:
                value = self.parse_integer(token)
                if value is None:
                    self.add_label_translation(label=token, size=4, offset=0)
                blob = pack_le32u(value)
            self.assembled_bytes += blob
            self.org_counter += len(blob)

    def directive_dw_to_ascii(self, instr):
        def dw_to_str(address, true_address):
            blob = format(true_address, '05d').encode('ascii')
            for b in blob:
                self.assembled_bytes[address] = b
                address += 1

        for token in instr.tokens[1:]:
            blob = b''
            if token[0] in ('"', '\''):
                blob = str(int(token[1:-1].encode('utf16'))).encode('ascii')
            else:
                value = self.parse_integer(token)
                if value is None:
                    self.add_label_translation(
                        label=token, offset=0, hook=dw_to_str)
                    blob = bytes(5)
                else:
                    blob = str(value).encode('ascii')
            self.assembled_bytes += blob
            self.org_counter += len(blob)

    def directive_dw_to_asciiz(self, instr):
        self.directive_dw_to_ascii(instr)
        self.assembled_bytes += b'\x00'
        self.org_counter += 1

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
            raise InvalidArgumentsForDirective()
        size = self.parse_integer(instr.tokens[1])
        if size is None:
            raise InvalidArgumentsForDirective()
        value = self.fill_value
        if len(instr.tokens) == 3:
            value = self.parse_integer(instr.tokens[2])
            if value is None:
                raise InvalidArgumentsForDirective()
        blob = bytes([value] * size)
        self.assembled_bytes += blob
        self.org_counter += len(blob)

    def directive_align(self, instr):
        if len(instr.tokens) != 2:
            raise InvalidArgumentsForDirective()
        size = self.parse_integer(instr.tokens[1])
        if size is None:
            raise InvalidArgumentsForDirective()

        mod = (self.current_org + self.org_counter) % size
        if mod != 0:
            blob = bytes([self.fill_value]) * (size - mod)
            self.assembled_bytes += blob
            self.org_counter += len(blob)

    def directive_db_to_ascii(self, instr):
        def db_to_str(address, true_address):
            blob = format(true_address, '03d').encode('ascii')
            for b in blob:
                self.assembled_bytes[address] = b
                self.org_counter += 1
                address += 1

        for token in instr.tokens[1:]:
            blob = b''
            if token[0] in ('"', '\''):
                blob = str(int(token[1:-1].encode('ascii'))).encode('ascii')
            else:
                value = self.parse_integer(token)
                if value is None:
                    self.add_label_translation(
                        label=token, offset=0, hook=db_to_str)
                    blob = bytes(3)
                else:
                    blob = str(value).encode('ascii')
            self.assembled_bytes += blob
            self.org_counter += len(blob)

    def directive_db_to_asciiz(self, instr):
        self.directive_db_to_ascii(instr)
        self.assembled_bytes += b'\x00'
        self.org_counter += 1

    def directive_db(self, instr):
        for token in instr.tokens[1:]:
            blob = b''
            if token[0] in ('"', '\''):
                blob = token[1:-1].encode('ascii')
            else:
                value = self.parse_integer(token)
                if value is None:
                    self.add_label_translation(label=token, size=1, offset=0)
                blob = pack_byte(value)
            self.assembled_bytes += blob
            self.org_counter += len(blob)

    def directive_include(self, instr):
        if len(instr.tokens) != 2:
            raise InvalidArgumentsForDirective()
        filename = instr.tokens[1]
        with open(filename) as f:
            self.assemble(f.read(), context=filename)

    def directive_incbin(self, instr):
        if len(instr.tokens) != 2:
            raise InvalidArgumentsForDirective()
        filename = instr.tokens[1]
        with open(filename, 'rb') as f:
            blob = f.read()
            self.assembled_bytes += blob
            self.org_counter += len(blob)

    def _get_math_formula(self, token):
        pre_formula = ''
        post_formula = ''
        for char in token:
            if char in ('<', '>'):
                pre_formula += char
            else:
                break

        for char in token[::-1]:
            if char in ('+', '-'):
                post_formula += char
            else:
                break

        if len(post_formula) > 0:
            return token[len(pre_formula):-len(post_formula)], pre_formula, post_formula

        return token[len(pre_formula):], pre_formula, post_formula

    def register_instruction(self, opcode, logic):
        key = opcode
        if not self.case_sensitive:
            key = key.upper()
        self.instructions[key] = logic

    def register_directive(self, name, logic):
        key = name
        if not self.case_sensitive:
            key = key.upper()
        self.directives[key] = logic

    def register_define(self, name, value):
        self.defines[name] = value
