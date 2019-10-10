from necroassembler.tokenizer import Tokenizer
from necroassembler.utils import pack, pack_byte
from necroassembler.exceptions import UnknownLabel


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

    case_sensitive = False

    def __init__(self):
        self.instructions = {}
        self.directives = {}
        self.defines = {}
        self.assembled_bytes = bytearray()
        self.labels = {}
        self.pre_link_passes = []
        self.post_link_passes = []
        self.current_org = 0x00
        self.org_counter = 0
        self.labels_addresses = {}

        self.register_directives()
        self.register_defines()
        self.discover_instructions()
        self.register_instructions()

    def register_directives(self):
        self.register_directive('org', self.directive_org)
        self.register_directive('include', self.directive_include)
        self.register_directive('define', self.directive_define)
        self.register_directive('db', self.directive_db)
        self.register_directive('byte', self.directive_db)
        self.register_directive('dw', self.directive_dw)
        self.register_directive('word', self.directive_dw)
        self.register_directive('db_to_ascii', self.directive_db_to_ascii)
        self.register_directive('dw_to_ascii', self.directive_dw_to_ascii)
        self.register_directive('db_to_asciiz', self.directive_db_to_asciiz)
        self.register_directive('dw_to_asciiz', self.directive_dw_to_asciiz)

    def register_defines(self):
        pass

    def discover_instructions(self):
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, 'opcode'):
                self.register_instruction(attr.opcode, attr)

    def register_instructions(self):
        pass

    def assemble(self, code, context=None):
        tokenizer = Tokenizer(context=context)
        tokenizer.parse(code)

        for statement in tokenizer.statements:
            statement.assemble(self)

    def assemble_file(self, filename):
        with open(filename) as f:
            self.assemble(f.read(), filename)

    def link(self):
        for _pass in self.pre_link_passes:
            _pass()
        for address in self.labels_addresses:
            data = self.labels_addresses[address]
            label = data['label']
            relative = data.get('relative', False)
            if not relative:
                true_address = self.get_label_absolute_address_by_name(label)
            else:
                true_address = self.get_label_relative_address_by_name(
                    label, data['start'] + data['size'])
            if true_address is None:
                raise UnknownLabel(label, self)
            if 'hook' in data:
                data['hook'](address, true_address)
            else:
                for i in range(0, data['size']):
                    self.assembled_bytes[address +
                                         i] = (true_address >> (8 * i)) & 0xff

        for _pass in self.post_link_passes:
            _pass()

    def add_label_translation(self, data={}, **kwargs):
        combined_data = data.copy()
        combined_data.update(kwargs)
        self.labels_addresses[len(
            self.assembled_bytes) + combined_data.get('offset', 1)] = combined_data

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
        token, pre_formula, post_formula = self.get_math_formula(token)
        value = self._internal_parse_integer(token)
        if value is None:
            return None
        return self.apply_math_formula(pre_formula, post_formula, value)

    def apply_math_formula(self, pre_formula, post_formula, value):
        for op in (pre_formula + post_formula):
            if op == '+':
                value += 1
            elif op == '-':
                value -= 1
            elif op == '>':
                value >>= 8
            elif op == '<':
                value <<= 8
        return value

    def get_label_absolute_address(self, label):
        return label['org'] + label['base']

    def get_label_absolute_address_by_name(self, name):
        name, pre_formula, post_formula = self.get_math_formula(name)
        if not name in self.labels:
            return None
        return self.apply_math_formula(pre_formula, post_formula, self.get_label_absolute_address(self.labels[name]))

    def get_label_relative_address(self, label, start):
        return self.get_label_absolute_address(label) - start

    def get_label_relative_address_by_name(self, name, start):
        name, pre_formula, post_formula = self.get_math_formula(name)
        if not name in self.labels:
            return None
        return self.apply_math_formula(pre_formula, post_formula, self.get_label_relative_address(self.labels[name], start))

    def directive_org(self, instr):
        if len(instr.tokens) != 2:
            raise Exception('invalid org directive')
        self.current_org = self.parse_integer(instr.tokens[1])
        if self.current_org is None:
            raise Exception('invalid .org value')
        self.org_counter = 0

    def directive_define(self, instr):
        if len(instr.tokens) != 3:
            raise Exception('invalid define directive')
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
                blob = pack('<H', value)
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

    def directive_db_to_ascii(self, instr):
        def db_to_str(address, true_address):
            blob = format(true_address, '03d').encode('ascii')
            for b in blob:
                self.assembled_bytes[address] = b
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
            raise Exception('invalid include directive')
        filename = instr.tokens[1]
        with open(filename) as f:
            self.assemble(f.read(), context=filename)

    def get_math_formula(self, token):
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
