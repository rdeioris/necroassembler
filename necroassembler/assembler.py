from necroassembler.tokenizer import Tokenizer
from necroassembler.utils import (pack_byte, pack_le32u, pack_le16u,
                                  pack_be32u, pack_be16u,
                                  in_bit_range, two_s_complement, pack_bits, to_two_s_complement)
from necroassembler.exceptions import (UnknownLabel, UnsupportedNestedMacro, NotInMacroRecordingMode,
                                       AddressOverlap, NegativeSignNotAllowed, NotInRepeatMode,
                                       UnsupportedNestedRepeat,
                                       AlignmentError, NotInBitRange, NotInSignedBitRange, OnlyForwardAddressesAllowed,
                                       InvalidArgumentsForDirective, LabelNotAllowed, InvalidDefine,
                                       SectionAlreadyDefined, SymbolAlreadyExported, OnlyPositiveValuesAllowed)

from necroassembler.scope import Scope
from necroassembler.macros import Macro
from necroassembler.linker import Linker
from necroassembler.statements import Instruction
from necroassembler.directives import Repeat, Data
import necroassembler.image
import necroassembler.audio
import sys
from collections import OrderedDict


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

    math_symbols = {'+': (lambda x, y: x + y, 2, 4),
                    '++': (lambda x: x + 1, 1, 4),
                    '-': (lambda x, y: x - y, 2, 4),
                    '--': (lambda x: x - 1, 1, 4),
                    '*': (lambda x, y: x * y, 2, 5),
                    '/': (lambda x, y: x // y, 2, 5),
                    '|': (lambda x, y: x | y, 2, 0),
                    '&': (lambda x, y: x & y, 2, 2),
                    '^': (lambda x, y: x ^ y, 2, 1),
                    '~': (lambda x: ~x, 1, 6),
                    '**': (lambda x, y: x ** y, 2, 7),
                    '>>': (lambda x, y: x >> y, 2, 3),
                    '<<': (lambda x, y: x << y, 2, 3)}

    math_brackets = ('(', ')')

    interesting_symbols = ()
    special_symbols = ()

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
        self.log = False
        self.sections = OrderedDict()
        self.current_section = None
        self.exports = []
        self.scopes_stack = []
        self.entry_point = None

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
        self.math_symbols = self.math_symbols.copy()
        self.interesting_symbols = tuple(self.interesting_symbols)
        self.special_symbols = tuple(self.special_symbols)

        self._register_internal_directives()
        self._discover()

        self.register_defines()
        self.register_directives()
        self.register_instructions()

    def _register_internal_directives(self):
        self.register_directive('macro', Macro.directive_macro)
        self.register_directive('endmacro', Macro.directive_endmacro)
        self.register_directive('org', self.directive_org)
        self.register_directive('include', self.directive_include)
        self.register_directive('incbin', self.directive_incbin)
        self.register_directive('inccsv', self.directive_inccsv)
        self.register_directive('inccsv_le16', self.directive_inccsv_le16)
        self.register_directive('incjson', self.directive_incjson)
        self.register_directive('define', self.directive_define)
        self.register_directive('db', Data.directive_db)
        self.register_directive('byte', Data.directive_db)
        self.register_directive('dw', Data.directive_dw)
        self.register_directive('word', Data.directive_dw)
        self.register_directive('dd', Data.directive_dd)
        self.register_directive('dl', Data.directive_dd)
        self.register_directive('dword', Data.directive_dd)
        self.register_directive('df', Data.directive_df)
        self.register_directive('db_to_ascii', self.directive_db_to_ascii)
        self.register_directive('dw_to_ascii', self.directive_dw_to_ascii)
        self.register_directive('db_to_asciiz', self.directive_db_to_asciiz)
        self.register_directive('dw_to_asciiz', self.directive_dw_to_asciiz)
        self.register_directive('fill', self.directive_fill)
        self.register_directive('ram', self.directive_ram)
        self.register_directive('log', self.directive_log)
        self.register_directive('align', Data.directive_align)
        self.register_directive('repeat', Repeat.directive_repeat)
        self.register_directive('endrepeat', Repeat.directive_endrepeat)
        self.register_directive('goto', self.directive_goto)
        self.register_directive('upto', self.directive_upto)
        self.register_directive('section', self.directive_section)
        self.register_directive('export', self.directive_export)
        self.register_directive('entry_point', self.directive_entry_point)
        self.register_directive(
            'incimg', necroassembler.image.directive_incimg)
        self.register_directive(
            'incwav', necroassembler.audio.directive_incwav)

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

    def get_root_scope(self):
        if not self.scopes_stack:
            return None
        return self.scopes_stack[0]

    def assemble(self, code, context=None):

        tokenizer = Tokenizer(
            context=context,
            interesting_symbols=tuple(
                set(''.join(self.math_symbols.keys()))) + self.math_brackets + self.interesting_symbols,
            special_symbols=self.special_symbols,
            args_splitter=self.args_splitter)
        tokenizer.parse(code)

        self.push_scope(Scope(self))
        self.statement_index = 0

        while self.statement_index < len(tokenizer.statements):
            line_number, tokens = tokenizer.statements[self.statement_index]
            instruction = Instruction(self, tokens, line_number, context)
            current_offset = len(self.assembled_bytes)
            current_pc = self.pc
            instruction.assemble()
            if self.log:
                new_offset = len(self.assembled_bytes)
                if new_offset == current_offset:
                    print('not assembled {0}'.format(instruction))
                else:
                    print('assembled to ({0}) offset/address 0x{1:x}/0x{2:x} {3}'.format(
                        ','.join(['0x{0:02x}'.format(x) for x in self.assembled_bytes[current_offset:]]), current_offset, current_pc, instruction))
            self.statement_index += 1

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

    def link(self, linker=None):
        if not linker:
            linker = Linker()
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

    def parse_integer(self, args, number_of_bits, signed, only_positive=False, labels_scope=None):
        current_base = 10
        cleaned_args = []

        for arg in args:
            if arg in self.hex_prefixes+self.hex_suffixes:
                current_base = 16
                continue
            if arg in self.oct_prefixes+self.oct_suffixes:
                current_base = 8
                continue
            if arg in self.bin_prefixes+self.bin_suffixes:
                current_base = 2
                continue
            if arg in self.dec_prefixes+self.dec_suffixes:
                current_base = 10
                continue

            if arg == '<':
                if cleaned_args and cleaned_args[-1] == '<':
                    cleaned_args[-1] = '<<'
                else:
                    cleaned_args.append(arg)
                current_base = 10
                continue

            if arg == '>':
                if cleaned_args and cleaned_args[-1] == '>':
                    cleaned_args[-1] = '>>'
                else:
                    cleaned_args.append(arg)
                current_base = 10
                continue

            if arg == '*':
                if cleaned_args and cleaned_args[-1] == '*':
                    cleaned_args[-1] = '**'
                else:
                    cleaned_args.append(arg)
                current_base = 10
                continue

            if arg == '+':
                if cleaned_args and cleaned_args[-1] == '+':
                    cleaned_args[-1] = '++'
                else:
                    cleaned_args.append(arg)
                current_base = 10
                continue

            if arg == '-':
                if cleaned_args and cleaned_args[-1] == '-':
                    cleaned_args[-1] = '--'
                else:
                    cleaned_args.append(arg)
                current_base = 10
                continue

            if arg in tuple(self.math_symbols.keys()) + self.math_brackets:
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
                            arg[1], labels_scope)
                    else:
                        return None
                values_and_ops.append(value)
            elif self.math_brackets and arg == self.math_brackets[0]:
                postfix_stack.append(arg)
            elif self.math_brackets and arg == self.math_brackets[1]:
                # pop and output
                while postfix_stack and postfix_stack[-1] != self.math_brackets[0]:
                    item = postfix_stack.pop()
                    values_and_ops.append(item)
                # TODO check for invalid state (not empty and not '(' on top)
                postfix_stack.pop()
            else:
                while postfix_stack and (self.math_brackets and postfix_stack[-1] not in self.math_brackets) and self.math_symbols[arg][2] <= self.math_symbols[postfix_stack[-1]][2]:
                    values_and_ops.append(postfix_stack.pop())
                postfix_stack.append(arg)

        while postfix_stack:
            values_and_ops.append(postfix_stack.pop())

        value = self.apply_postfix(values_and_ops)

        orig_value = value

        # disable negative sign for unsigned numbers
        if not signed:
            if value < 0:
                if only_positive:
                    raise OnlyPositiveValuesAllowed(orig_value)
                else:
                    # this will rise exception in case of overflow
                    value = to_two_s_complement(value, number_of_bits)

            if not in_bit_range(value, number_of_bits):
                raise NotInBitRange(orig_value, number_of_bits)

        else:
            min_value = -(1 << number_of_bits-1)
            max_value = (1 << (number_of_bits-1)) - 1

            if value < min_value:
                raise NotInSignedBitRange(value, number_of_bits)

            if value > max_value:
                two_s_complement_value = to_two_s_complement(
                    value, number_of_bits+1)
                value = two_s_complement(
                    two_s_complement_value, number_of_bits)

        return value

    def parse_unsigned_integer(self, arg):
        return self.parse_integer([arg], 64, False)

    def parse_signed_integer(self, arg):
        return self.parse_integer([arg], 64, True)

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

    def get_label_absolute_address_by_name(self, name, scope=None):
        if not scope:
            scope = self.get_current_scope()
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

    def get_filesystem_encoding(self):
        return sys.getfilesystemencoding()

    def directive_org(self, instr):
        if len(instr.directive_args) not in (1, 2):
            raise InvalidArgumentsForDirective(instr)
        new_org_start = self.parse_unsigned_integer(instr.directive_args[0])
        if new_org_start is None:
            raise InvalidArgumentsForDirective(instr)
        new_org_end = 0
        if len(instr.directive_args) == 2:
            new_org_end = self.parse_unsigned_integer(instr.directive_args[1])
            if new_org_end is None:
                raise InvalidArgumentsForDirective(instr)

        self.change_org(new_org_start, new_org_end)

    def directive_define(self, instr):
        if len(instr.directive_args) != 2:
            raise InvalidArgumentsForDirective(instr)
        scope = self.get_current_scope()
        scope.defines[instr.directive_args[0]] = instr.directive_args[1]

    def get_define(self, key):
        scope = self.get_current_scope()
        while scope:
            if key in scope.defines:
                return scope.defines[key]
            scope = scope.parent
        return None

    def append_assembled_bytes(self, blob):
        self.assembled_bytes += blob
        self.org_counter += len(blob)

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

    def stringify(self, args, encoding):
        whole_string = ''
        for arg in args:
            if arg[0] in ('"', '\''):
                whole_string += arg[1:-1]
            else:
                return None
        return whole_string.encode(encoding)

    def stringify_path(self, args):
        return self.stringify(args, self.get_filesystem_encoding())

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
        if len(instr.args[0]) not in (2, 3):
            raise InvalidArgumentsForDirective(instr)

        name = self.stringify([instr.args[0][0]], 'ascii')
        if name in self.sections:
            raise SectionAlreadyDefined(instr)
        permissions = instr.args[0][1]
        if not all([True if letter in 'RWXE' else False for letter in permissions]):
            raise InvalidArgumentsForDirective(instr)
        if len(instr.args[0]) == 3:
            new_org_start = self.parse_integer([instr.args[0][2]], 64, False)
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
        if len(instr.args) != 1:
            raise InvalidArgumentsForDirective(instr)
        name = instr.args[0][0]
        if name in self.exports:
            raise SymbolAlreadyExported(instr)
        self.exports.append(name)

    def directive_entry_point(self, instr):
        if len(instr.args) != 1:
            raise InvalidArgumentsForDirective(instr)
        self.entry_point = instr.args[0]

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
    def main(cls, linker=None):
        import sys
        import os
        try:
            *sources, destination = sys.argv[1:]
        except ValueError:
            print('usage: {0} <sources> <destination>'.format(
                os.path.basename(sys.argv[0])))
            return
        asm = cls()
        for source in sources:
            asm.assemble_file(source)
        asm.link(linker=linker)
        asm.save(destination)
