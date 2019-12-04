from necroassembler import Assembler, opcode
from necroassembler.utils import pack_bits, pack_le32u, pack_be32u
from necroassembler.exceptions import InvalidOpCodeArguments


RAW_REGS = ('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7',
            'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15')
REGS_ALIASES = ('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7',
                'r8', 'r9', 'r10', 'fp', 'ip', 'sp', 'lr', 'pc')
REGS = RAW_REGS + REGS_ALIASES

CONDITIONS = ('EQ', 'NE', 'CS', 'CC', 'MI', 'PL', 'VS',
              'VC', 'HI', 'LS', 'GE', 'LT', 'GT', 'LE', 'AL')


def _immediate(tokens):
    return len(tokens) > 1 and tokens[0] == '#'


def _label(tokens):
    return len(tokens) > 0 and tokens[0] != '#'


def _interrupt(tokens):
    return all([x.isdigit() for x in tokens])


IMMEDIATE = _immediate
LABEL = _label
INTERRUPT = _interrupt


def conditions(base):
    for condition in CONDITIONS:
        yield base + condition, {'cond': CONDITIONS.index(condition)}


def set_condition(base):
    yield base + 'S', {'condition_set': True}


class ARM32Opcode:

    def __init__(self, name, func):
        self.name = name
        self.cond = 0xE
        self.signed = False
        self.condition_set = False
        self.func = func

    def reg(self, arg):
        name = arg[0].lower()
        if name in RAW_REGS:
            return RAW_REGS.index(name)
        if name in REGS_ALIASES:
            return REGS_ALIASES.index(name)

    def __call__(self, instr):
        blob = self.func(self, instr)
        if blob:
            if instr.assembler.big_endian:
                return pack_be32u(blob)
            else:
                return pack_le32u(blob)

    def _offset(self, assembler, arg, bits, alignment):
        return assembler.parse_integer_or_label(label=arg,
                                                size=4,
                                                bits_size=(
                                                    bits[0] - bits[1]) + 1 + (alignment//2),
                                                bits=bits,
                                                filter=lambda x: x >> (
                                                    alignment//2),
                                                alignment=alignment,
                                                relative=assembler.pc + 8)

    def _bx(self, instr):
        if instr.match(REGS):
            return pack_bits(0x012fff10, ((31, 28), self.cond), ((3, 0), self.reg(instr.args[0])))

    def _b(self, instr):
        if instr.match(LABEL):
            offset = self._offset(instr.assembler, instr.args[0], (23, 0), 4)
            return pack_bits(0x0a000000, ((31, 28), self.cond), ((23, 0), offset))

    def _bl(self, instr):
        if instr.match(LABEL):
            offset = self._offset(instr.assembler, instr.args[0], (23, 0), 4)
            return pack_bits(0x0b000000, ((31, 28), self.cond), ((23, 0), offset))

    def _swi(self, instr):
        comment = 0
        if instr.args:
            arg = instr.args[0]
            if arg[0] == '#':
                arg = arg[1:]
            comment = instr.assembler.parse_integer_or_label(label=arg,
                                                             size=4,
                                                             bits_size=24,
                                                             bits=(23, 0))
        return pack_bits(0x0f000000, ((31, 28), self.cond), ((23, 0), comment))

    def _mov(self, instr):
        op = 0b1101
        if instr.match(REGS, REGS):
            return pack_bits(0, ((31, 28), self.cond), ((24, 21), op), ((15, 12), self.reg(instr.args[0])), ((3, 0), self.reg(instr.args[1])))


OPCODES = (
    ('BX', (conditions, ), ARM32Opcode._bx),
    ('B', (conditions, ), ARM32Opcode._b),
    ('BL', (conditions, ), ARM32Opcode._bl),
    ('SWI', (conditions, ), ARM32Opcode._swi),
    ('SVC', (conditions, ), ARM32Opcode._swi),
    ('MOV', (set_condition, conditions), ARM32Opcode._mov),
)


class AssemblerARM32(Assembler):

    hex_prefixes = ('0x',)

    bin_prefixes = ('0b', '0y')

    interesting_symbols = ('#',)

    special_symbols = ('[', ']', '{', '}')
    math_brackets = ('(', ')')

    def _apply_recursive_variant(self, base, index, callbacks, values):
        for new_value in callbacks[index](base):
            values.append(new_value)
            if index + 1 < len(callbacks):
                self._apply_recursive_variant(
                    new_value, index+1, callbacks, values)

    def register_instructions(self):
        for base, variants, func in OPCODES:
            instructions = [(base, {})]
            self._apply_recursive_variant(
                base, 0, variants, instructions)
            for name, data in instructions:
                arm32_opcode = ARM32Opcode(name.upper(), func)
                arm32_opcode.cond = data.get('cond', arm32_opcode.cond)
                self.register_instruction(arm32_opcode.name, arm32_opcode)


if __name__ == '__main__':
    AssemblerARM32.main()
