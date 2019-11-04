from necroassembler import Assembler, opcode
from necroassembler.utils import pack_bits_le16u, pack_le16u, pack_bit
from necroassembler.exceptions import (
    AssemblerException, InvalidRegister, UnknownRegister, InvalideImmediateValue, NotInBitRange)

LOW_REGS = ('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7')
HIGH_REGS_TRUE = ('r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15')
HIGH_REGS_ALIASES = ('fp', 'ip', 'sp', 'lr', 'pc')
HIGH_REGS = HIGH_REGS_TRUE + HIGH_REGS_ALIASES
PC = ('pc', 'r15')
SP = ('sp', 'r13')


def _immediate(token):
    return len(token) > 1 and token.startswith('#')


def _label(token):
    return token and not token.startswith('#')


def _interrupt(token):
    return token.isdigit()


IMMEDIATE = _immediate
LABEL = _label
INTERRUPT = _interrupt


def low_reg(reg):
    if reg.lower() in HIGH_REGS:
        raise InvalidRegister()
    if not reg.lower() in LOW_REGS:
        raise UnknownRegister()
    return int(reg[1:])


def high_reg(reg):
    if reg.lower() in HIGH_REGS_ALIASES:
        return HIGH_REGS_ALIASES.index(reg.lower()) + 3
    if reg.lower() in LOW_REGS:
        raise InvalidRegister()
    if reg.lower() not in HIGH_REGS:
        raise UnknownRegister()
    return int(reg[1:]) - 8


class InvalidRList(AssemblerException):
    message = 'invalid rlist format'


class AssemblerThumb(Assembler):

    hex_prefixes = ('0x',)

    bin_prefixes = ('0b', '0y')

    def _offset(self, arg, bits, alignment):
        return self.parse_integer_or_label(label=arg,
                                           size=2,
                                           bits_size=(
                                               bits[0] - bits[1]) + 1 + (alignment//2),
                                           bits=bits,
                                           filter=lambda x: x >> (
                                               alignment//2),
                                           alignment=alignment,
                                           relative=self.pc + 4)

    def _imm(self, arg):
        value = self.parse_integer(arg[1:], 8, False)
        if value is None:
            raise InvalideImmediateValue()
        return value

    def _word8(self, arg):
        return self.parse_integer_or_label(label=arg[1:],
                                           size=2,
                                           bits_size=8,
                                           bits=(7, 0),
                                           alignment=4,
                                           filter=lambda x: x >> 2,
                                           # bit 1 of pc must be turned off
                                           relative=(self.pc + 4) & ~(0b10))

    def _conditional_branch(self, instr, cond):
        if instr.match(LABEL):
            offset = self._offset(instr.tokens[1], (7, 0), 2)
            return self._build_opcode(0b1101000000000000, ((11, 8), cond), ((7, 0), offset >> 1))

    def _alu(self, instr, op):
        if instr.match(LOW_REGS, LOW_REGS):
            rd, rs = instr.apply(low_reg, low_reg)
            return self._build_opcode(0b0100000000000000, ((9, 6), op), ((5, 3), rs), ((2, 0), rd))

    def _rlist(self, tokens):

        rlist = 0
        for token in tokens:
            if token in LOW_REGS:
                bit_to_set = low_reg(token)
                rlist = pack_bit(rlist, (bit_to_set, 1))
                continue
            if '-' in token:
                r_start, r_end = token.split('-')
                if not r_start.lower() in LOW_REGS:
                    raise InvalidRList()
                if not r_end.lower() in LOW_REGS:
                    raise InvalidRList()

                first = low_reg(r_start)
                last = low_reg(r_end)
                if first > last:
                    raise InvalidRList()
                for reg in range(first, last+1):
                    rlist = pack_bit(rlist, (reg, 1))
                continue
            raise InvalidRList()

        return rlist

    def _build_opcode(self, value, *args):
        return pack_bits_le16u(value, *args)

    @opcode('LSL')
    def _lsl(self, instr):
        if instr.match(LOW_REGS, LOW_REGS, IMMEDIATE):
            rd, rs, imm = instr.apply(low_reg, low_reg, self._imm)
            return self._build_opcode(0b0000000000000000, ((10, 6), imm), ((5, 3), rs), ((2, 0), rd))
        return self._alu(instr, 0b0010)

    @opcode('LSR')
    def _lsr(self, instr):
        if instr.match(LOW_REGS, LOW_REGS, IMMEDIATE):
            rd, rs, imm = instr.apply(low_reg, low_reg, self._imm)
            return self._build_opcode(0b0000100000000000, ((10, 6), imm), ((5, 3), rs), ((2, 0), rd))
        return self._alu(instr, 0b0011)

    @opcode('ASR')
    def _asr(self, instr):
        if instr.match(LOW_REGS, LOW_REGS, IMMEDIATE):
            rd, rs, imm = instr.apply(low_reg, low_reg, self._imm)
            return self._build_opcode(0b0001000000000000, ((10, 6), imm), ((5, 3), rs), ((2, 0), rd))
        return self._alu(instr, 0b0100)

    @opcode('ADD')
    def _add(self, instr):
        if instr.match(LOW_REGS, LOW_REGS, LOW_REGS):
            rd, rs, rn = instr.apply(low_reg, low_reg, low_reg)
            return self._build_opcode(0b0001100000000000, ((8, 6), rn), ((5, 3), rs), ((2, 0), rd))
        if instr.match(LOW_REGS, LOW_REGS, IMMEDIATE):
            rd, rs, imm = instr.apply(low_reg, low_reg, self._imm)
            return self._build_opcode(0b0001110000000000, ((8, 6), imm), ((5, 3), rs), ((2, 0), rd))
        if instr.match(LOW_REGS, IMMEDIATE):
            rd, imm = instr.apply(low_reg, self._imm)
            return self._build_opcode(0b0011000000000000, ((10, 8), rd), ((7, 0), imm))
        if instr.match(LOW_REGS, HIGH_REGS):
            rd, hs = instr.apply(low_reg, high_reg)
            return self._build_opcode(0b0100010001000000, ((5, 3), hs), ((2, 0), rd))
        if instr.match(HIGH_REGS, LOW_REGS):
            hd, rs = instr.apply(high_reg, low_reg)
            return self._build_opcode(0b0100010010000000, ((5, 3), rs), ((2, 0), hd))
        if instr.match(HIGH_REGS, HIGH_REGS):
            hd, hs = instr.apply(high_reg, high_reg)
            return self._build_opcode(0b0100010011000000, ((5, 3), hs), ((2, 0), hd))
        if instr.match(LOW_REGS, PC, IMMEDIATE):
            rd, imm = instr.apply(low_reg, None, self._imm)
            return self._build_opcode(0b1010000000000000, ((10, 8), rd), ((7, 0), imm))
        if instr.match(LOW_REGS, SP, IMMEDIATE):
            rd, imm = instr.apply(low_reg, None, self._imm)
            return self._build_opcode(0b1010100000000000, ((10, 8), rd), ((7, 0), imm))
        if instr.match(SP, IMMEDIATE):
            imm, = instr.apply(None, self._imm)
            return self._build_opcode(0b1011000000000000, ((7, 0), imm >> 1, True))

    @opcode('SUB')
    def _sub(self, instr):
        if instr.match(LOW_REGS, LOW_REGS, LOW_REGS):
            rd, rs, rn = instr.apply(low_reg, low_reg, low_reg)
            return self._build_opcode(0b0001101000000000, ((8, 6), rn), ((5, 3), rs), ((2, 0), rd))
        if instr.match(LOW_REGS, LOW_REGS, IMMEDIATE):
            rd, rs, imm = instr.apply(low_reg, low_reg, self._imm)
            return self._build_opcode(0b0001111000000000, ((8, 6), imm), ((5, 3), rs), ((2, 0), rd))
        if instr.match(LOW_REGS, IMMEDIATE):
            rd, imm = instr.apply(low_reg, self._imm)
            return self._build_opcode(0b0011100000000000, ((10, 8), rd), ((7, 0), imm))

    @opcode('MOV')
    def _mov(self, instr):
        if instr.match(LOW_REGS, IMMEDIATE):
            rd, imm = instr.apply(low_reg, self._imm)
            return self._build_opcode(0b0010000000000000, ((10, 8), rd), ((7, 0), imm))

        if instr.match(LOW_REGS, HIGH_REGS):
            rd, hs = instr.apply(low_reg, high_reg)
            return self._build_opcode(0b0100011001000000, ((5, 3), hs), ((2, 0), rd))

        if instr.match(HIGH_REGS, LOW_REGS):
            hd, rs = instr.apply(high_reg, low_reg)
            return self._build_opcode(0b0100011010000000, ((5, 3), rs), ((2, 0), hd))

        if instr.match(HIGH_REGS, HIGH_REGS):
            hd, hs = instr.apply(high_reg, high_reg)
            return self._build_opcode(0b0100011011000000, ((5, 3), hs), ((2, 0), hd))

    @opcode('CMP')
    def _cmp(self, instr):
        if instr.match(LOW_REGS, IMMEDIATE):
            rd, imm = instr.apply(low_reg, self._imm)
            return self._build_opcode(0b0010100000000000, ((10, 8), rd), ((7, 0), imm))

        if instr.match(LOW_REGS, HIGH_REGS):
            rd, hs = instr.apply(low_reg, high_reg)
            return self._build_opcode(0b0100010101000000, ((5, 3), hs), ((2, 0), rd))

        if instr.match(HIGH_REGS, LOW_REGS):
            hd, rs = instr.apply(high_reg, low_reg)
            return self._build_opcode(0b0100010110000000, ((5, 3), rs), ((2, 0), hd))

        if instr.match(HIGH_REGS, HIGH_REGS):
            hd, hs = instr.apply(high_reg, high_reg)
            return self._build_opcode(0b0100010111000000, ((5, 3), hs), ((2, 0), hd))

        return self._alu(instr, 0b1010)

    @opcode('AND')
    def _and(self, instr):
        return self._alu(instr, 0b0000)

    @opcode('EOR')
    def _eor(self, instr):
        return self._alu(instr, 0b0001)

    @opcode('ADC')
    def _adc(self, instr):
        return self._alu(instr, 0b0101)

    @opcode('SBC')
    def _sbc(self, instr):
        return self._alu(instr, 0b0110)

    @opcode('ROR')
    def _ror(self, instr):
        return self._alu(instr, 0b0111)

    @opcode('TST')
    def _tst(self, instr):
        return self._alu(instr, 0b1000)

    @opcode('NEG')
    def _neg(self, instr):
        return self._alu(instr, 0b1001)

    @opcode('CMN')
    def _cmn(self, instr):
        return self._alu(instr, 0b1011)

    @opcode('ORR')
    def _orr(self, instr):
        return self._alu(instr, 0b1100)

    @opcode('MUL')
    def _mul(self, instr):
        return self._alu(instr, 0b1101)

    @opcode('BIC')
    def _bic(self, instr):
        return self._alu(instr, 0b1110)

    @opcode('MVN')
    def _mvn(self, instr):
        return self._alu(instr, 0b1111)

    @opcode('BX')
    def _bx(self, instr):
        if instr.match(LOW_REGS):
            rs, = instr.apply(low_reg)
            return self._build_opcode(0b0100011100000000, ((5, 3), rs))
        if instr.match(HIGH_REGS):
            hs, = instr.apply(high_reg)
            return self._build_opcode(0b0100011101000000, ((5, 3), hs))

    @opcode('LDR')
    def _ldr(self, instr):
        if instr.match(LOW_REGS, '[', PC, IMMEDIATE, ']'):
            rd, imm = instr.apply(low_reg, None, None, self._word8, None)
            return self._build_opcode(0b0100100000000000, ((10, 8), rd), ((7, 0), imm >> 2))

        if instr.match(LOW_REGS, '[', LOW_REGS, LOW_REGS, ']'):
            rd, rb, ro = instr.apply(
                low_reg, None, low_reg, low_reg, None)
            return self._build_opcode(0b0101100000000000, ((8, 6), ro), ((5, 3), rb), ((2, 0), rd))

        if instr.match(LOW_REGS, '[', LOW_REGS, IMMEDIATE, ']'):
            rd, rb, imm = instr.apply(
                low_reg, None, low_reg, self._imm, None)
            return self._build_opcode(0b0110100000000000, ((10, 6), imm >> 2), ((5, 3), rb), ((2, 0), rd))

        if instr.match(LOW_REGS, '[', SP, IMMEDIATE, ']'):
            rd, imm = instr.apply(low_reg, None, None, self._word8, None)
            return self._build_opcode(0b1001100000000000, ((10, 8), rd), ((7, 0), imm >> 2))

    @opcode('LDRB')
    def _ldrb(self, instr):
        if instr.match(LOW_REGS, '[', LOW_REGS, LOW_REGS, ']'):
            rd, rb, ro = instr.apply(
                low_reg, None, low_reg, low_reg, None)
            return self._build_opcode(0b0101110000000000, ((8, 6), ro), ((5, 3), rb), ((2, 0), rd))

        if instr.match(LOW_REGS, '[', LOW_REGS, IMMEDIATE, ']'):
            rd, rb, imm = instr.apply(
                low_reg, None, low_reg, self._imm, None)
            return self._build_opcode(0b0111100000000000, ((10, 6), imm >> 2), ((5, 3), rb), ((2, 0), rd))

    @opcode('LDRH')
    def _ldrh(self, instr):
        if instr.match(LOW_REGS, '[', LOW_REGS, LOW_REGS, ']'):
            rd, rb, ro = instr.apply(
                low_reg, None, low_reg, low_reg, None)
            return self._build_opcode(0b010110000000000, ((8, 6), ro), ((5, 3), rb), ((2, 0), rd))

        if instr.match(LOW_REGS, '[', LOW_REGS, IMMEDIATE, ']'):
            rd, rb, imm = instr.apply(
                low_reg, None, low_reg, self._imm, None)
            return self._build_opcode(0b1000100000000000, ((10, 6), imm), ((5, 3), rb), ((2, 0), rd))

    @opcode('LDSB')
    def _ldsb(self, instr):
        if instr.match(LOW_REGS, '[', LOW_REGS, LOW_REGS, ']'):
            rd, rb, ro = instr.apply(
                low_reg, None, low_reg, low_reg, None)
            return self._build_opcode(0b0101011000000000, ((8, 6), ro), ((5, 3), rb), ((2, 0), rd))

    @opcode('LDSH')
    def _ldsh(self, instr):
        if instr.match(LOW_REGS, '[', LOW_REGS, LOW_REGS, ']'):
            rd, rb, ro = instr.apply(
                low_reg, None, low_reg, low_reg, None)
            return self._build_opcode(0b0101111000000000, ((8, 6), ro), ((5, 3), rb), ((2, 0), rd))

    @opcode('STR')
    def _str(self, instr):
        if instr.match(LOW_REGS, '[', LOW_REGS, LOW_REGS, ']'):
            rd, rb, ro = instr.apply(
                low_reg, None, low_reg, low_reg, None)
            return self._build_opcode(0b0101000000000000, ((8, 6), ro), ((5, 3), rb), ((2, 0), rd))

        if instr.match(LOW_REGS, '[', LOW_REGS, IMMEDIATE, ']'):
            rd, rb, imm = instr.apply(
                low_reg, None, low_reg, self._imm, None)
            return self._build_opcode(0b0110100000000000, ((10, 6), imm >> 2), ((5, 3), rb), ((2, 0), rd))

    @opcode('STRB')
    def _strb(self, instr):
        pass

    @opcode('STRH')
    def _strh(self, instr):
        if instr.match(LOW_REGS, '[', LOW_REGS, LOW_REGS, ']'):
            rd, rb, ro = instr.apply(
                low_reg, None, low_reg, low_reg, None)
            return self._build_opcode(0b0101001000000000, ((8, 6), ro), ((5, 3), rb), ((2, 0), rd))

    @opcode('BL')
    def _bl(self, instr):
        if not instr.match(LABEL):
            return None

        offset = instr.tokens[1]

        address = self.parse_integer(offset, 23, signed=True)
        if address:
            address >>= 1
            address0 = address >> 11
            address1 = address & 0x7ff
            return self._build_opcode(0b1111000000000000, ((10, 0), address0)) + self._build_opcode(0b1111100000000000, ((10, 0), address1))

        self.add_label_translation(label=offset,
                                   size=2,
                                   bits_size=23,
                                   bits=(10, 0),
                                   alignment=2,
                                   relative=self.pc + 4,
                                   # get high 11 bits (after >> 1)
                                   filter=lambda x: x >> 12)
        self.add_label_translation(label=offset,
                                   offset=2,
                                   size=2,
                                   bits_size=23,
                                   bits=(10, 0),
                                   alignment=2,
                                   relative=self.pc + 4,
                                   # get low 11 bits (after >> 1)
                                   filter=lambda x: ((x >> 1) & 0x7FF))

        return pack_le16u(0b1111000000000000, 0b1111100000000000)

    @opcode('B')
    def _b(self, instr):
        if instr.match(LABEL):
            offset = self._offset(instr.tokens[1], (10, 0), 2)
            return self._build_opcode(0b1110000000000000, ((10, 0), offset >> 1))

    @opcode('BEQ')
    def _beq(self, instr):
        return self._conditional_branch(instr, 0b0000)

    @opcode('BNE')
    def _bne(self, instr):
        return self._conditional_branch(instr, 0b0001)

    @opcode('BCS')
    def _bcs(self, instr):
        return self._conditional_branch(instr, 0b0010)

    @opcode('BCC')
    def _bcc(self, instr):
        return self._conditional_branch(instr, 0b0011)

    @opcode('BMI')
    def _bmi(self, instr):
        return self._conditional_branch(instr, 0b0100)

    @opcode('BPL')
    def _bpl(self, instr):
        return self._conditional_branch(instr, 0b0101)

    @opcode('BVS')
    def _bvs(self, instr):
        return self._conditional_branch(instr, 0b0110)

    @opcode('BVC')
    def _bvc(self, instr):
        return self._conditional_branch(instr, 0b0111)

    @opcode('BHI')
    def _bhi(self, instr):
        return self._conditional_branch(instr, 0b1000)

    @opcode('BLS')
    def _bls(self, instr):
        return self._conditional_branch(instr, 0b1001)

    @opcode('BGE')
    def _bge(self, instr):
        return self._conditional_branch(instr, 0b1010)

    @opcode('BLT')
    def _blt(self, instr):
        return self._conditional_branch(instr, 0b1011)

    @opcode('BGT')
    def _bgt(self, instr):
        return self._conditional_branch(instr, 0b1100)

    @opcode('BLE')
    def _ble(self, instr):
        return self._conditional_branch(instr, 0b1101)

    @opcode('SWI')
    def _swi(self, instr):
        if instr.match(INTERRUPT):
            return self._build_opcode(0b1101111100000000, ((7, 0), int(instr.tokens[1])))

    @opcode('PUSH')
    def _push(self, instr):
        if len(instr.tokens) < 4:
            return None

        if instr.tokens[1] != '{' or instr.tokens[-1] != '}':
            return None

        lr = 0
        if instr.tokens[-2].lower() == 'lr':
            lr = 1

        rlist = self._rlist(instr.tokens[2:-(1+lr)])
        return self._build_opcode(0b1011010000000000, ((11, 11), lr), ((7, 0), rlist))
