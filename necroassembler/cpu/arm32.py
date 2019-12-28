from necroassembler import Assembler, opcode
from necroassembler.utils import pack_bits, pack_le32u, pack_be32u, rol32
from necroassembler.exceptions import InvalidOpCodeArguments, AssemblerException


RAW_REGS = ('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7',
            'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15')
REGS_ALIASES = ('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7',
                'r8', 'r9', 'r10', 'fp', 'ip', 'sp', 'lr', 'pc')
REGS = RAW_REGS + REGS_ALIASES

CONDITIONS = ('EQ', 'NE', 'CS', 'CC', 'MI', 'PL', 'VS',
              'VC', 'HI', 'LS', 'GE', 'LT', 'GT', 'LE', 'AL')

SHIFTS = ('ASL', 'LSL', 'LSR', 'ASR', 'ROR')


def _immediate(tokens):
    return len(tokens) > 1 and tokens[0] == '#'


def _label(tokens):
    return len(tokens) > 0 and tokens[0] != '#'


def _number(tokens):
    return all([x.isdigit() for x in tokens])


class UnableToEncodeToArmImmediate12(AssemblerException):
    message = 'unable to encode value to arm immediate12'


IMMEDIATE = _immediate
LABEL = _label
NUMBER = _number


def conditions(base):
    for condition in CONDITIONS:
        yield base + condition, {'cond': CONDITIONS.index(condition)}


def set_condition(base):
    yield base + 'S', {'condition_set': True}


def set_byte_transfer(base):
    yield base + 'B', {'byte_transfer': True}


def set_write_back(base):
    yield base + 'T', {'write_back': True}


def _encode_imm12(value):
    for i in range(0, 16):
        rotated_value = rol32(value, i * 2)
        if rotated_value < 256:
            return (i << 8) | rotated_value
    raise UnableToEncodeToArmImmediate12()


class ARM32Opcode:

    def __init__(self, assembler, name, func):
        self.assembler = assembler
        self.name = name
        self.cond = 0xE
        self.signed = False
        self.condition_set = False
        self.byte_transfer = False
        self.write_back = False
        self.func = func

    def _reg(self, arg):
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

    def _offset(self, arg, bits, alignment):
        return self.assembler.parse_integer_or_label(label=arg,
                                                     size=4,
                                                     bits_size=(
                                                         bits[0] - bits[1]) + 1 + (alignment//2),
                                                     bits=bits,
                                                     filter=lambda x: x >> (
                                                         alignment//2),
                                                     alignment=alignment,
                                                     relative=self.assembler.pc + 8)

    def _imm12(self, args):
        value = self.assembler.parse_integer_or_label(label=args[1:],
                                                      size=4,
                                                      bits_size=32,
                                                      bits=(11, 0),
                                                      filter=_encode_imm12)
        return _encode_imm12(value)

    def _bx(self, instr):
        if instr.match(REGS):
            return pack_bits(0x012fff10, ((31, 28), self.cond), ((3, 0), self._reg(instr.args[0])))

    def _b(self, instr):
        if instr.match(LABEL):
            offset = self._offset(instr.args[0], (23, 0), 4)
            return pack_bits(0x0a000000, ((31, 28), self.cond), ((23, 0), offset))

    def _bl(self, instr):
        if instr.match(LABEL):
            offset = self._offset(instr.args[0], (23, 0), 4)
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

    def _shift(self, shiftname):
        n = SHIFTS.index(shiftname.upper()) - 1
        if n < 0:
            n = 0
        return n

    def _shift_rs(self, shiftname, reg):
        return (self._reg([reg]) << 4) | (self._shift(shiftname) << 1) | 1

    def _shift_imm(self, shiftname, n):
        return (int(n) << 3) | (self._shift(shiftname) << 1)

    def _data_proc(self, instr, op, use_rn=False):
        # Rd/Rn, Rm
        if instr.match(REGS, REGS):
            return pack_bits(0,
                             ((31, 28), self.cond),
                             ((20, 20), self.condition_set),
                             ((24, 21), op),
                             ((15, 12) if not use_rn else (
                                 19, 16), self._reg(instr.args[0])),
                             ((3, 0), self._reg(instr.args[1])))

        # Rd, Rm, shift Rs
        if instr.match(REGS, REGS, [SHIFTS, REGS]):
            return pack_bits(0,
                             ((31, 28), self.cond),
                             ((20, 20), self.condition_set),
                             ((24, 21), op),
                             ((15, 12), self._reg(instr.args[0])),
                             ((11, 4), self._shift_rs(
                                 instr.args[2][0], instr.args[2][1])),
                             ((3, 0), self._reg(instr.args[1])))

        # Rd, Rn, Rm, shift Rs
        if instr.match(REGS, REGS, REGS, [SHIFTS, REGS]):
            return pack_bits(0,
                             ((31, 28), self.cond),
                             ((20, 20), self.condition_set),
                             ((24, 21), op),
                             ((19, 16), self._reg(instr.args[1])),
                             ((15, 12), self._reg(instr.args[0])),
                             ((11, 4), self._shift_rs(
                                 instr.args[3][0], instr.args[3][1])),
                             ((3, 0), self._reg(instr.args[2])))

        # Rd, Rm, shift #
        if instr.match(REGS, REGS, [SHIFTS, '#', NUMBER]):
            return pack_bits(0,
                             ((31, 28), self.cond),
                             ((20, 20), self.condition_set),
                             ((24, 21), op),
                             ((15, 12), self._reg(instr.args[0])),
                             ((11, 4), self._shift_imm(
                                 instr.args[2][0], instr.args[2][2])),
                             ((3, 0), self._reg(instr.args[1])))

        # Rd, Rm, RRX
        if instr.match(REGS, REGS, 'RRX'):
            return pack_bits(0,
                             ((31, 28), self.cond),
                             ((20, 20), self.condition_set),
                             ((24, 21), op),
                             ((15, 12), self._reg(instr.args[0])),
                             ((11, 4), self._shift_imm('ROR', '0')),
                             ((3, 0), self._reg(instr.args[1])))

        # Rd, Rn, Rm, shift #
        if instr.match(REGS, REGS, REGS, [SHIFTS, '#', NUMBER]):
            return pack_bits(0,
                             ((31, 28), self.cond),
                             ((20, 20), self.condition_set),
                             ((24, 21), op),
                             ((19, 16), self._reg(instr.args[1])),
                             ((15, 12), self._reg(instr.args[0])),
                             ((11, 4), self._shift_imm(
                                 instr.args[3][0], instr.args[3][2])),
                             ((3, 0), self._reg(instr.args[2])))

        # Rd, Rn, Rm, RRX
        if instr.match(REGS, REGS, REGS, 'RRX'):
            return pack_bits(0,
                             ((31, 28), self.cond),
                             ((20, 20), self.condition_set),
                             ((24, 21), op),
                             ((19, 16), self._reg(instr.args[1])),
                             ((15, 12), self._reg(instr.args[0])),
                             ((11, 4), self._shift_imm('ROR', '0')),
                             ((3, 0), self._reg(instr.args[2])))

        # Rd, Rn, Rm
        if instr.match(REGS, REGS, REGS):
            return pack_bits(0,
                             ((31, 28), self.cond),
                             ((20, 20), self.condition_set),
                             ((24, 21), op),
                             ((19, 16), self._reg(instr.args[1])),
                             ((15, 12), self._reg(instr.args[0])),
                             ((3, 0), self._reg(instr.args[2])))

        # Rd/Rn, #
        if instr.match(REGS, IMMEDIATE):
            return pack_bits(0,
                             ((31, 28), self.cond),
                             ((20, 20), self.condition_set),
                             ((25, 25), 1),
                             ((24, 21), op),
                             ((15, 12) if not use_rn else (
                                 19, 16), self._reg(instr.args[0])),
                             ((11, 0), self._imm12(instr.args[1])))

        # Rd, Rn, #
        if instr.match(REGS, REGS, IMMEDIATE):
            return pack_bits(0,
                             ((31, 28), self.cond),
                             ((20, 20), self.condition_set),
                             ((25, 25), 1),
                             ((24, 21), op),
                             ((19, 16), self._reg(instr.args[1])),
                             ((15, 12), self._reg(instr.args[0])),
                             ((11, 0), self._imm12(instr.args[2])))

    def _and(self, instr):
        return self._data_proc(instr, 0b0000)

    def _eor(self, instr):
        return self._data_proc(instr, 0b0001)

    def _sub(self, instr):
        return self._data_proc(instr, 0b0010)

    def _rsb(self, instr):
        return self._data_proc(instr, 0b0011)

    def _add(self, instr):
        return self._data_proc(instr, 0b0100)

    def _adc(self, instr):
        return self._data_proc(instr, 0b0101)

    def _sbc(self, instr):
        return self._data_proc(instr, 0b0110)

    def _rsc(self, instr):
        return self._data_proc(instr, 0b0111)

    def _tst(self, instr):
        self.condition_set = True
        return self._data_proc(instr, 0b1000, use_rn=True)

    def _teq(self, instr):
        self.condition_set = True
        return self._data_proc(instr, 0b1001, use_rn=True)

    def _cmp(self, instr):
        self.condition_set = True
        return self._data_proc(instr, 0b1010, use_rn=True)

    def _cmn(self, instr):
        self.condition_set = True
        return self._data_proc(instr, 0b1011, use_rn=True)

    def _orr(self, instr):
        return self._data_proc(instr, 0b1100)

    def _mov(self, instr):
        return self._data_proc(instr, 0b1101)

    def _bic(self, instr):
        return self._data_proc(instr, 0b1110)

    def _mvn(self, instr):
        return self._data_proc(instr, 0b1111)

    def _load_store(self, instr, op):
        def build_offset(address):
            if address > 0:
                return (1 << 23) | address
            else:
                return address & 0xfff

        if instr.match(REGS, '[', REGS, IMMEDIATE, ']'):
            offset = self.assembler.parse_integer(instr.args[3][1:], 13, True)
            return pack_bits(0,
                             ((31, 28), self.cond),
                             ((27, 26), 1),
                             ((24, 24), 1),
                             ((23, 23), 1 if offset >= 0 else 0),
                             ((22, 22), self.byte_transfer),
                             ((21, 21), 0),  # no write back
                             ((20, 20), op),
                             ((19, 16), self._reg(instr.args[2])),
                             ((15, 12), self._reg(instr.args[0])),
                             ((11, 0), offset & 0xfff))

        if instr.match(REGS, '[', REGS, IMMEDIATE, ']', '!'):
            offset = self.assembler.parse_integer(instr.args[3][1:], 13, True)
            return pack_bits(0,
                             ((31, 28), self.cond),
                             ((27, 26), 1),
                             ((24, 24), 1),
                             ((23, 23), 1 if offset >= 0 else 0),
                             ((22, 22), self.byte_transfer),
                             ((21, 21), 1), # write back
                             ((20, 20), op),
                             ((19, 16), self._reg(instr.args[2])),
                             ((15, 12), self._reg(instr.args[0])),
                             ((11, 0), offset & 0xfff))

        if instr.match(REGS, '[', REGS, ']'):
            return pack_bits(0,
                             ((31, 28), self.cond),
                             ((27, 26), 1),
                             ((24, 24), 1),
                             ((23, 23), 1),
                             ((22, 22), self.byte_transfer),
                             ((21, 21), 0),  # no write back
                             ((20, 20), op),
                             ((19, 16), self._reg(instr.args[2])),
                             ((15, 12), self._reg(instr.args[0])),
                             ((11, 0), 0))

        if instr.match(REGS, LABEL):

            offset = self.assembler.parse_integer_or_label(label=instr.args[1],
                                                           size=4,
                                                           bits_size=13,
                                                           filter=build_offset,
                                                           alignment=4,
                                                           relative=self.assembler.pc + 8)
            return pack_bits(0,
                             ((31, 28), self.cond),
                             ((27, 26), 1),
                             ((24, 24), 1),
                             ((23, 23), 1 if offset >= 0 else 0),
                             ((22, 22), self.byte_transfer),
                             ((21, 21), 0),  # no write back!
                             ((20, 20), op),
                             ((19, 16), 0xf),
                             ((15, 12), self._reg(instr.args[0])),
                             ((11, 0), offset & 0xfff))

    def _ldr(self, instr):
        return self._load_store(instr, 1)

    def _ldrb(self, instr):
        self.byte_transfer = True
        return self._load_store(instr, 1)

    def _strb(self, instr):
        self.byte_transfer = True
        return self._load_store(instr, 0)

    def _str(self, instr):
        return self._load_store(instr, 0)

    def _mul(self, instr):
        # Rd, Rm, Rs
        if instr.match(REGS, REGS, REGS):
            return pack_bits(0x90,
                             ((31, 28), self.cond),
                             ((20, 20), self.condition_set),
                             ((19, 16), self._reg(instr.args[0])),
                             ((11, 8), self._reg(instr.args[2])),
                             ((3, 0), self._reg(instr.args[1])))


OPCODES = (
    ('BX', (conditions, ), ARM32Opcode._bx),
    ('B', (conditions, ), ARM32Opcode._b),
    ('BL', (conditions, ), ARM32Opcode._bl),
    ('SWI', (conditions, ), ARM32Opcode._swi),
    ('SVC', (conditions, ), ARM32Opcode._swi),
    ('AND', (conditions, set_condition), ARM32Opcode._and),
    ('EOR', (conditions, set_condition), ARM32Opcode._eor),
    ('SUB', (conditions, set_condition), ARM32Opcode._sub),
    ('RSB', (conditions, set_condition), ARM32Opcode._rsb),
    ('ADD', (conditions, set_condition), ARM32Opcode._add),
    ('ADC', (conditions, set_condition), ARM32Opcode._adc),
    ('SBC', (conditions, set_condition), ARM32Opcode._sbc),
    ('RSC', (conditions, set_condition), ARM32Opcode._rsc),
    ('TST', (conditions, ), ARM32Opcode._tst),
    ('TEQ', (conditions, ), ARM32Opcode._teq),
    ('CMP', (conditions, ), ARM32Opcode._cmp),
    ('CMN', (conditions, ), ARM32Opcode._cmn),
    ('ORR', (conditions, set_condition), ARM32Opcode._orr),
    ('MOV', (conditions, set_condition), ARM32Opcode._mov),
    ('BIC', (conditions, set_condition), ARM32Opcode._bic),
    ('MVN', (conditions, set_condition), ARM32Opcode._mvn),
    ('LDR', (conditions, set_byte_transfer, set_write_back), ARM32Opcode._ldr),
    ('STR', (conditions, set_byte_transfer, set_write_back), ARM32Opcode._str),
    ('LDRB', (conditions, set_byte_transfer, set_write_back), ARM32Opcode._ldrb),
    ('STRB', (conditions, set_byte_transfer, set_write_back), ARM32Opcode._strb),
    ('MUL', (conditions, set_condition), ARM32Opcode._mul),
)


class AssemblerARM32(Assembler):

    hex_prefixes = ('0x',)

    bin_prefixes = ('0b', '0y')

    interesting_symbols = ('#',)

    special_symbols = ('[', ']', '{', '}')
    math_brackets = ('(', ')')

    def _apply_recursive_variant(self, base, index, callbacks, values):
        additional = ()
        if index == 0:
            additional = (base,)
        for new_value in tuple(callbacks[index](base[0])) + additional:
            new_value[1].update(base[1])
            values.append(new_value)
            if index + 1 < len(callbacks):
                self._apply_recursive_variant(
                    new_value, index+1, callbacks, values)

    def register_instructions(self):
        for base, variants, func in OPCODES:
            instructions = []
            self._apply_recursive_variant(
                (base, {}), 0, variants, instructions)
            for name, data in instructions:
                arm32_opcode = ARM32Opcode(self, name.upper(), func)
                arm32_opcode.cond = data.get('cond', arm32_opcode.cond)
                arm32_opcode.condition_set = data.get(
                    'condition_set', arm32_opcode.condition_set)
                arm32_opcode.byte_transfer = data.get(
                    'byte_transfer', arm32_opcode.byte_transfer)
                arm32_opcode.write_back = data.get(
                    'write_back', arm32_opcode.write_back)
                self.register_instruction(arm32_opcode.name, arm32_opcode)


if __name__ == '__main__':
    AssemblerARM32.main()
