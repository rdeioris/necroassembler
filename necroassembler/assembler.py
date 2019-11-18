from necroassembler.tokenizer import Tokenizer
from necroassembler.utils import (pack_byte, pack_le32u, pack_le16u,
                                  pack_be32u, pack_be16u, in_bit_range,
                                  in_bit_range, two_s_complement, pack_bits)
from necroassembler.exceptions import (UnknownLabel, UnsupportedNestedMacro, NotInMacroRecordingMode,
                                       AddressOverlap, NegativeSignNotAllowed, NotInRepeatMode,
                                       UnsupportedNestedRepeat,
                                       AlignmentError, NotInBitRange, OnlyForwardAddressesAllowed,
                                       InvalidArgumentsForDirective, LabelNotAllowed, InvalidDefine,
                                       SectionAlreadyDefined, SymbolAlreadyExported)
from necroassembler.macros import Macro
from necroassembler.linker import Dummy
from necroassembler.statements import Statement, Scope
from necroassembler.directives import Repeat


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

    def __init__(self, scope, label, size, bits_size, relative):
        self.scope = scope
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
    args_splitter = ','

    defines = {}

    def __init__(self):
        self.instructions = {}
        self.directives = {}
        self.assembled_bytes = bytearray()
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
        self.scopes_stack = []
        self.math_symbols = {'+': (lambda x, y: x + y, 2, 4),
                             '-': (lambda x, y: x - y, 2, 4),
                             '*': (lambda x, y: x * y, 2, 5),
                             '/': (lambda x, y: x // y, 2, 5),
                             '|': (lambda x, y: x | y, 2, 0),
                             '&': (lambda x, y: x & y, 2, 2),
                             '^': (lambda x, y: x ^ y, 2, 1),
                             '~': (lambda x: ~x, 1, 6),
                             '**': (lambda x, y: x ** y, 2, 7),
                             '>>': (lambda x, y: x >> y, 2, 3),
                             '<<': (lambda x, y: x << y, 2, 3)}

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
        self.register_directive('repeat', Repeat.directive_repeat)
        self.register_directive('endrepeat', Repeat.directive_end_repeat)
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

    def push_scope(self, scope):
        scope.parent = self.get_current_scope()
        self.scopes_stack.append(scope)
        return scope

    def pop_scope(self):
        return self.scopes_stack.pop()

    def get_current_scope(self):
        if not self.scopes_stack:
            return None
        return self.scopes_stack[-1]

    def assemble(self, code, context=None):
        tokenizer = Tokenizer(
            context=context, args_splitter=self.args_splitter)
        tokenizer.parse(code)

        self.push_scope(Scope(self))
        self.line_index = 0

        while self.line_index < len(tokenizer.lines):
            line_number, tokens = tokenizer.lines[self.line_index]
            statement = Statement(self, tokens, line_number, context)
            current_offset = len(self.assembled_bytes)
            statement.assemble()
            if self.log:
                new_offset = len(self.assembled_bytes)
                if new_offset == current_offset:
                    print('not assembled {0}'.format(statement))
                else:
                    print('assembled line {0} -> ({1}) at 0x{2:x}'.format(line_number,
                                                                          ','.join(['0x{0:02x}'.format(x) for x in self.assembled_bytes[current_offset:]]), current_offset))
            self.line_index += 1

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
            scope = data.scope
            is_relative = data.relative != 0

            absolute_address = self.parse_integer(label, 64, False, scope)
            if not is_relative:
                true_address = absolute_address
            else:
                true_address = absolute_address - data.relative

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

            if not in_bit_range(true_address, total_bits):
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

        # TODO move labels resolution to linker
        self._resolve_labels(linker)

        self.assembled_bytes = linker.link(self)

    @property
    def pc(self):
        return self.current_org + self.org_counter

    def add_label_translation(self, label,
                              size, bits_size,
                              offset=0, alignment=1, bits=None, filter=None,
                              relative=0, hook=None):
        index = len(self.assembled_bytes) + offset
        label_data = LabelData(self.get_current_scope(),
                               label, size, bits_size, relative)
        label_data.offset = offset
        label_data.alignment = alignment
        label_data.bits = bits
        label_data.hook = hook
        label_data.filter = filter
        self.labels_addresses[index] = label_data

    def _internal_parse_integer(self, token, base):
        # first check for an ascii char
        if token[0] == '\'' and token[2] == '\'':
            return ord(token[1:2])

        # then check for base override

        for prefix in self.hex_suffixes:
            if token.endswith(prefix):
                token = token[:-len(prefix)]
                base = 16

        for prefix in self.bin_suffixes:
            if token.endswith(prefix):
                token = token[:-len(prefix)]
                base = 2

        for prefix in self.oct_suffixes:
            if token.endswith(prefix):
                token = token[:-len(prefix)]
                base = 8

        for prefix in self.dec_suffixes:
            if token.endswith(prefix):
                token = token[:-len(prefix)]
                base = 10

        for prefix in self.hex_prefixes:
            if token.startswith(prefix):
                token = token[len(prefix):]
                base = 16

        for prefix in self.bin_prefixes:
            if token.startswith(prefix):
                token = token[len(prefix):]
                base = 2

        for prefix in self.oct_prefixes:
            if token.startswith(prefix):
                token = token[len(prefix):]
                base = 8

        for prefix in self.dec_prefixes:
            if token.startswith(prefix):
                token = token[len(prefix):]
                base = 10

        try:
            return int(token, base)
        except ValueError:
            return None

    def apply_postfix(self, values):
        stack = []
        for item in values:
            if item in self.math_symbols:
                op = self.math_symbols[item]
                args = []
                for _ in range(0, op[1]):
                    if not stack:
                        args.append(0)
                    else:
                        args.append(stack.pop())
                stack.append(op[0](*(args[::-1])))
            else:
                stack.append(item)

        return stack.pop()

    def parse_integer(self, args, number_of_bits, signed, labels_scope=None):
        current_base = 10
        cleaned_args = []

        for arg in args:
            if arg in self.hex_prefixes:
                current_base = 16
                continue
            if arg in self.oct_prefixes:
                current_base = 8
                continue
            if arg in self.bin_prefixes:
                current_base = 2
                continue
            if arg in self.dec_prefixes:
                current_base = 10
                continue

            if arg == '<':
                if cleaned_args[-1] == '<':
                    cleaned_args[-1] = '<<'
                else:
                    cleaned_args.append(arg)
                current_base = 10
                continue

            if arg == '>':
                if cleaned_args[-1] == '>':
                    cleaned_args[-1] = '>>'
                else:
                    cleaned_args.append(arg)
                current_base = 10
                continue

            if arg == '*':
                if cleaned_args[-1] == '*':
                    cleaned_args[-1] = '**'
                else:
                    cleaned_args.append(arg)
                current_base = 10
                continue

            if arg in tuple(self.math_symbols.keys()) + ('(', ')'):
                cleaned_args.append(arg)
                current_base = 10
                continue

            cleaned_args.append([current_base, arg])

        values_and_ops = []
        postfix_stack = []

        for arg in cleaned_args:
            if isinstance(arg, list):
                value = self._internal_parse_integer(arg[1], arg[0])
                if value is None:
                    if labels_scope:
                        value = self.get_label_absolute_address_by_name(
                            labels_scope, arg[1])
                    else:
                        return None
                values_and_ops.append(value)
            elif arg == '(':
                postfix_stack.append(arg)
            elif arg == ')':
                # pop and output
                while postfix_stack and postfix_stack[-1] != '(':
                    item = postfix_stack.pop()
                    values_and_ops.append(item)
                # TODO check for invalid state (not empty and not '(' on top)
                postfix_stack.pop()
            else:
                while postfix_stack and postfix_stack[-1] not in ('(', ')') and self.math_symbols[arg][2] <= self.math_symbols[postfix_stack[-1]][2]:
                    values_and_ops.append(postfix_stack.pop())
                postfix_stack.append(arg)

        while postfix_stack:
            values_and_ops.append(postfix_stack.pop())

        value = self.apply_postfix(values_and_ops)

        orig_value = value

        # disable negative sign
        if value < 0:
            value += pow(2, number_of_bits)

        # re-enable it if required
        if signed:
            value = two_s_complement(value, number_of_bits)
            test_value = value
            if value < 0:
                test_value = value + pow(2, number_of_bits)

            if not in_bit_range(test_value, number_of_bits):
                raise NotInBitRange(orig_value, number_of_bits)
        else:
            if not in_bit_range(value, number_of_bits):
                raise NotInBitRange(orig_value, number_of_bits)

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

    def get_label_absolute_address(self, label):
        return label['org'] + label['base']

    def get_label_absolute_address_by_name(self, scope, name):
        while scope:
            if name in scope.labels:
                return self.get_label_absolute_address(scope.labels[name])
            scope = scope.parent
        raise UnknownLabel(name)

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
        if len(instr.args) not in (1, 2):
            raise InvalidArgumentsForDirective(instr)
        new_org_start = self.parse_integer(instr.args[0], 64, False)
        if new_org_start is None:
            raise InvalidArgumentsForDirective(instr)
        new_org_end = 0
        if len(instr.args) == 2:
            new_org_end = self.parse_integer(instr.args[1], 64, False)
            if new_org_end is None:
                raise InvalidArgumentsForDirective(instr)

        self.change_org(new_org_start, new_org_end)

    def directive_define(self, instr):
        # TODO implement matching
        if len(instr.args) != 1 or len(instr.args[0]) != 2:
            raise InvalidArgumentsForDirective(instr)
        self.defines[instr.args[0][0]] = instr.args[0][1]

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
        if len(instr.args) not in (1, 2):
            raise InvalidArgumentsForDirective(instr)
        offset = self.parse_integer(instr.args[0], 64, False)
        if offset is None:
            raise InvalidArgumentsForDirective(instr)
        if offset < len(self.assembled_bytes):
            raise AddressOverlap(instr)
        value = self.fill_value
        if len(instr.args) == 2:
            value = self.parse_integer(instr.args[1], 8, False)
            if value is None:
                raise InvalidArgumentsForDirective(instr)
        blob = bytes([value] * (offset - (self.pc - self.current_org)))
        self.append_assembled_bytes(blob)

    def directive_ram(self, instr):
        if len(instr.args) != 1:
            raise InvalidArgumentsForDirective(instr)
        size = self.parse_integer(instr.args[0], 64, False)
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
        for arg in instr.args:
            blob = self.stringify(arg, 'ascii')
            if blob is None:
                value = self.parse_integer_or_label(
                    label=arg, bits_size=8, size=1)
                blob = pack_byte(value)
            self.append_assembled_bytes(blob)

    def stringify(self, args, encoding):
        whole_string = ''
        for arg in args:
            if arg[0] in ('"', '\''):
                whole_string += arg[1:-1]
            else:
                return None
        return whole_string.encode(encoding)

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
