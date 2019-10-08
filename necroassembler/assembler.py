
import necroassembler
from necroassembler.tokenizer import Tokenizer


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
        self.assembled_bytes = bytearray()
        self.labels = {}
        self.pre_link_passes = []
        self.post_link_passes = []
        self.current_org = 0x00
        self.org_counter = 0
        self.labels_addresses = {}

        self.register_directives()
        self.discover_instructions()
        self.register_instructions()

    def register_directives(self):
        self.register_directive('org', self.directive_org)
        self.register_directive('include', self.directive_include)
        self.register_directive('db', self.directive_db)
        self.register_directive('dw', self.directive_dw)

    def discover_instructions(self):
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, 'opcode'):
                self.register_instruction(attr.opcode, attr)

    def register_instructions(self):
        pass

    def assemble(self, code):
        tokenizer = Tokenizer()
        tokenizer.parse(code)

        for statement in tokenizer.statements:
            print(statement)
            statement.assemble(self)

    def link(self):
        for _pass in self.pre_link_passes:
            _pass()
        for address in self.labels_addresses:
            data = self.labels_addresses[address]
            label = data['label']
            true_address = self.get_label_absolute_address_by_name(label)
            for i in range(0, data['size']):
                self.assembled_bytes[address +
                                     i] = (true_address >> (8 * i)) & 0xff
        for _pass in self.post_link_passes:
            _pass()

    def add_label_translation(self, data={}, **kwargs):
        combined_data = data.copy()
        combined_data.update(kwargs)
        self.labels_addresses[len(
            self.assembled_bytes) + 1] = combined_data

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
        formula = self.get_math_formula(token)
        value = self._internal_parse_integer(token[len(formula):])
        if value is None:
            return None
        return self.apply_math_formula(formula, value)

    def apply_math_formula(self, formula, value):
        for op in formula:
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
        formula = self.get_math_formula(name)
        name = name[len(formula):]
        if not name in self.labels:
            return None
        return self.apply_math_formula(formula, self.get_label_absolute_address(self.labels[name]))

    def get_label_relative_address(self, label, start):
        return self.get_label_absolute_address(label) - start

    def directive_org(self, tokens):
        if len(tokens) != 2:
            raise Exception('invalid org directive')
        self.current_org = self.parse_integer(tokens[1])
        if self.current_org is None:
            raise Exception('invalid .org value')
        self.org_counter = 0

    def directive_dw(self, tokens):
        for token in tokens[1:]:
            blob = b''
            if token[0] in ('"', '\''):
                blob = token[1:-1].encode('utf16')
            else:
                value = self.parse_integer(token)
                if value is None:
                    raise Exception('invalid byte value')
                blob = necroassembler.pack('<H', value)
            self.assembled_bytes += blob
            self.org_counter += len(blob)

    def directive_db(self, tokens):
        for token in tokens[1:]:
            blob = b''
            if token[0] in ('"', '\''):
                blob = token[1:-1].encode('utf8')
            else:
                value = self.parse_integer(token)
                if value is None:
                    raise Exception('invalid byte value')
                blob = necroassembler.pack('B', value)
            self.assembled_bytes += blob
            self.org_counter += len(blob)

    def directive_include(self, tokens):
        if len(tokens) != 2:
            raise Exception('invalid include directive')
        with open(tokens[1]) as f:
            self.assemble(f.read())

    def get_math_formula(self, token):
        formula = ''
        for char in token:
            if char in ('+', '-', '<', '>'):
                formula += char
            else:
                return formula

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
