from necroassembler import Assembler, opcode
from necroassembler.utils import pack_le_u16
from necroassembler.exceptions import UnkownRegister, InvalidRegister, InvalideImmediateValue


class AssemblerThumb(Assembler):

    hex_prefixes = ('0x',)

    bin_prefixes = ('0b', '0y')

    special_prefixes = ('#',)

    low_regs = ('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7')
    high_regs = ('r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15')
    high_regs_aliases = ('fp', 'ip', 'sp', 'lr', 'pc')

    def _low_reg(self, instr, reg):
        if reg.lower() in self.low_regs:
            return int(reg[1:])

        if reg.lower() in self.high_regs + self.high_regs_aliases:
            raise InvalidRegister(instr)

        raise UnkownRegister(instr)

    def _offset(self, instr, arg, bits):
        return self.parse_integer_or_label(arg,
                                           bits=bits,
                                           relative=True,
                                           size=2,
                                           offset=0,
                                           right_shift=1,
                                           alignment=2,
                                           start=self.current_org + self.org_counter + 4)

    def _imm(self, instr, arg):
        if not arg.startswith('#'):
            raise InvalideImmediateValue(instr)
        value = self.parse_integer(arg[1:])
        if not value:
            raise InvalideImmediateValue(instr)
        return value

    def _build_opcode(self, left, right):
        return pack_le_u16(left << 8 | right & 0xFF)

    @opcode('LSL')
    def _lsl(self, instr):
        rd, rs, *off5 = instr.tokens[1:]
        if not off5:
            return self._build_opcode(0b01000000, 0b10000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))
        off5 = self._imm(instr, off5[0])
        return self._build_opcode(0b00000000 | (off5 >> 2), (off5 << 6) | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('LSR')
    def _lsr(self, instr):
        rd, rs, *off5 = instr.tokens[1:]
        if not off5:
            return self._build_opcode(0b01000000, 0b11000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))
        off5 = self._imm(instr, off5[0])
        return self._build_opcode(0b00001000 | (off5 >> 2), (off5 << 6) | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('ASR')
    def _asr(self, instr):
        rd, rs, *off5 = instr.tokens[1:]
        if not off5:
            return self._build_opcode(0b01000001, 0b00000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))
        off5 = self._imm(instr, off5[0])
        return self._build_opcode(0b00010000 | (off5 >> 2), (off5 << 6) | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('ADD')
    def _add(self, instr):
        reg_d, reg_s, *op = instr.tokens[1:]
        if not op:
            return self._build_opcode(0b00110000 | self._low_reg(instr, reg_d),  self._imm(instr, reg_s, (7, 0)))
        imm = 0
        op = op[0]
        if op.startswith('#'):
            op = self._imm(instr, op) & 0x07
            imm = 1 << 2
        else:
            op = self._low_reg(instr, op)
        return self._build_opcode(0b00011000 | imm | (op >> 2), (op << 6) | (self._low_reg(instr, reg_s) << 3) | self._low_reg(instr, reg_d))

    @opcode('SUB')
    def _sub(self, instr):
        reg_d, reg_s, *op = instr.tokens[1:]
        if not op:
            return self._build_opcode(0b00111000 | self._low_reg(instr, reg_d),  self._imm(instr, reg_s))
        imm = 0
        op = op[0]
        if op.startswith('#'):
            op = self._imm(instr, op) & 0x07
            imm = 1 << 2
        else:
            op = self._low_reg(instr, op)
        return self._build_opcode(0b00011010 | imm | (op >> 2), (op << 6) | (self._low_reg(instr, reg_s) << 3) | self._low_reg(instr, reg_d))

    @opcode('MOV')
    def _mov(self, instr):
        reg, imm = instr.tokens[1:]
        return self._build_opcode(0b00100000 | self._low_reg(instr, reg),  self._imm(instr, imm))

    @opcode('CMP')
    def _cmp(self, instr):
        reg, imm = instr.tokens[1:]
        return self._build_opcode(0b00101000 | self._low_reg(instr, reg),  self._imm(instr, imm))

    @opcode('AND')
    def _and(self, instr):
        rd, rs = instr.tokens[1:]
        return self._build_opcode(0b01000000, 0b00000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('EOR')
    def _eor(self, instr):
        rd, rs = instr.tokens[1:]
        return self._build_opcode(0b01000000, 0b01000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('B')
    def _b(self, instr):
        offset = self._offset(instr, instr.tokens[1], (10, 0))
        return self._build_opcode(0b11100000 | (offset >> 5), offset)
