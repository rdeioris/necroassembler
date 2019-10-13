from necroassembler import Assembler, opcode
from necroassembler.utils import pack_le_u16, in_bit_range_signed
from necroassembler.exceptions import UnkownRegister, InvalidRegister, InvalideImmediateValue, NotInBitRange


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

    def _high_reg(self, instr, reg):
        if reg.lower() in self.high_regs:
            return int(reg[1:]) - 8

        if reg.lower() in self.high_regs_aliases:
            return self.high_regs_aliases.index(reg.lower()) + 3

        if reg.lower() in self.low_regs:
            raise InvalidRegister(instr)

        raise UnkownRegister(instr)

    def _offset(self, instr, arg, bits, alignment):
        return self.parse_integer_or_label(arg,
                                           bits=bits,
                                           relative=True,
                                           size=2,
                                           offset=0,
                                           right_shift=alignment//2,
                                           alignment=alignment,
                                           start=self.current_org + self.org_counter + 4)

    def _imm(self, instr, arg, shift=0):
        if not arg.startswith('#'):
            raise InvalideImmediateValue(instr)
        value = self.parse_integer(arg[1:])
        if value is None:
            raise InvalideImmediateValue(instr)
        return value >> shift

    def _word8(self, instr, arg, shift=0):
        if not arg.startswith('#'):
            raise InvalideImmediateValue(instr)
        value = self.parse_integer(arg[1:])
        if value is None:
            pc = self.current_org + self.org_counter + 4
            self.add_label_translation(label=arg[1:],
                                       bits=(7, 0),
                                       relative=True,
                                       only_forward=True,
                                       size=2,
                                       offset=0,
                                       alignment=4,
                                       right_shift=2,
                                       # bit 1 of pc must be turned off
                                       start=pc & ~(0b10))
            value = 0
        return value >> shift

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
            if reg_s.lower() in self.high_regs + self.high_regs_aliases and reg_d.lower() in self.high_regs + self.high_regs_aliases:
                return self._build_opcode(0b01000100, 0b11000000 | self._high_reg(instr, reg_s) << 3 | self._high_reg(instr, reg_d))
            if reg_s.lower() in self.high_regs + self.high_regs_aliases:
                return self._build_opcode(0b01000100, 0b01000000 | self._high_reg(instr, reg_s) << 3 | self._low_reg(instr, reg_d))
            if reg_d.lower() in self.high_regs + self.high_regs_aliases:
                return self._build_opcode(0b01000100, 0b10000000 | self._low_reg(instr, reg_s) << 3 | self._high_reg(instr, reg_d))
            return self._build_opcode(0b00110000 | self._low_reg(instr, reg_d),  self._imm(instr, reg_s))
        imm = 0
        op = op[0]
        if op.startswith('#'):
            if reg_s.lower() in ('r15', 'pc'):
                return self._build_opcode(0b10100000 | self._low_reg(instr, reg_d), self._word8(instr, op, 2))
            if reg_s.lower() in ('r13', 'sp'):
                return self._build_opcode(0b10101000 | self._low_reg(instr, reg_d), self._imm(instr, op, 2))

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
        reg_d, reg_s = reg, imm
        if reg_s.lower() in self.high_regs + self.high_regs_aliases and reg_d.lower() in self.high_regs + self.high_regs_aliases:
            return self._build_opcode(0b01000110, 0b11000000 | self._high_reg(instr, reg_s) << 3 | self._high_reg(instr, reg_d))
        if reg_s.lower() in self.high_regs + self.high_regs_aliases:
            return self._build_opcode(0b01000110, 0b01000000 | self._high_reg(instr, reg_s) << 3 | self._low_reg(instr, reg_d))
        if reg_d.lower() in self.high_regs + self.high_regs_aliases:
            return self._build_opcode(0b01000110, 0b10000000 | self._low_reg(instr, reg_s) << 3 | self._high_reg(instr, reg_d))
        return self._build_opcode(0b00100000 | self._low_reg(instr, reg),  self._imm(instr, imm))

    @opcode('CMP')
    def _cmp(self, instr):
        reg, imm = instr.tokens[1:]
        reg_d, reg_s = reg, imm
        if reg_s.lower() in self.high_regs + self.high_regs_aliases and reg_d.lower() in self.high_regs + self.high_regs_aliases:
            return self._build_opcode(0b01000101, 0b11000000 | self._high_reg(instr, reg_s) << 3 | self._high_reg(instr, reg_d))
        if reg_s.lower() in self.high_regs + self.high_regs_aliases:
            return self._build_opcode(0b01000101, 0b01000000 | self._high_reg(instr, reg_s) << 3 | self._low_reg(instr, reg_d))
        if reg_d.lower() in self.high_regs + self.high_regs_aliases:
            return self._build_opcode(0b01000101, 0b10000000 | self._low_reg(instr, reg_s) << 3 | self._high_reg(instr, reg_d))

        if imm not in self.low_regs:
            return self._build_opcode(0b00101000 | self._low_reg(instr, reg),  self._imm(instr, imm))
        return self._build_opcode(0b01000000, 0b00000000 | (self._low_reg(instr, imm) << 3) | self._low_reg(instr, reg))

    @opcode('AND')
    def _and(self, instr):
        rd, rs = instr.tokens[1:]
        return self._build_opcode(0b01000000, 0b00000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('EOR')
    def _eor(self, instr):
        rd, rs = instr.tokens[1:]
        return self._build_opcode(0b01000000, 0b01000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('ADC')
    def _adc(self, instr):
        rd, rs = instr.tokens[1:]
        return self._build_opcode(0b01000001, 0b01000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('SBC')
    def _sbc(self, instr):
        rd, rs = instr.tokens[1:]
        return self._build_opcode(0b01000001, 0b10000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('ROT')
    def _rot(self, instr):
        rd, rs = instr.tokens[1:]
        return self._build_opcode(0b01000001, 0b11000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('TST')
    def _tst(self, instr):
        rd, rs = instr.tokens[1:]
        return self._build_opcode(0b01000010, 0b00000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('NEG')
    def _neg(self, instr):
        rd, rs = instr.tokens[1:]
        return self._build_opcode(0b01000010, 0b01000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('CMN')
    def _cmn(self, instr):
        rd, rs = instr.tokens[1:]
        return self._build_opcode(0b01000010, 0b11000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('ORR')
    def _orr(self, instr):
        rd, rs = instr.tokens[1:]
        return self._build_opcode(0b01000011, 0b00000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('MUL')
    def _mul(self, instr):
        rd, rs = instr.tokens[1:]
        return self._build_opcode(0b01000011, 0b01000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('BIC')
    def _bic(self, instr):
        rd, rs = instr.tokens[1:]
        return self._build_opcode(0b01000011, 0b10000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('MVN')
    def _mvn(self, instr):
        rd, rs = instr.tokens[1:]
        return self._build_opcode(0b01000011, 0b11000000 | (self._low_reg(instr, rs) << 3) | self._low_reg(instr, rd))

    @opcode('BX')
    def _bx(self, instr):
        reg = instr.tokens[1]
        if reg in self.low_regs:
            return self._build_opcode(0b01000111, 0b00000000 | self._low_reg(instr, reg) << 3)
        if reg in self.high_regs + self.high_regs_aliases:
            return self._build_opcode(0b01000111, 0b01000000 | self._high_reg(instr, reg) << 3)

    @opcode('LDR')
    def _ldr(self, instr):
        rd, open_bracket, pc, imm, close_bracket = instr.tokens[1:]

        if open_bracket != '[' or close_bracket != ']':
            return None

        if pc.lower() in ('r15', 'pc'):
            return self._build_opcode(0b01001000 | self._low_reg(instr, rd), self._word8(instr, imm, 2))

        if pc.lower() in ('r13', 'sp'):
            return self._build_opcode(0b10011000 | self._low_reg(instr, rd), self._imm(instr, imm, 2))

        rb, ro = pc, imm

        if rb.lower() in self.low_regs and ro.lower() in self.low_regs:
            return self._build_opcode(0b01011000 | (self._low_reg(instr, ro) >> 7),
                                      self._low_reg(instr, ro) << 6 | self._low_reg(instr, rb) << 3 | self._low_reg(instr, rd))

        if rb.lower() in self.low_regs:
            return self._build_opcode(0b01110000 | self._imm(instr, ro, 2) >> 3, self._imm(
                instr, ro, 2) << 6 | self._low_reg(instr, rb) << 3 | self._low_reg(instr, rd))

        return None

    @opcode('STR')
    def _str(self, instr):
        rd, open_bracket, rb, ro, close_bracket = instr.tokens[1:]

        if open_bracket != '[' or close_bracket != ']':
            return None

        if rb.lower() in ('r13', 'sp'):
            return self._build_opcode(0b10010000 | self._low_reg(instr, rd), self._imm(instr, ro, 2))

        if ro.lower() in self.low_regs:
            return self._build_opcode(0b01010000 | (self._low_reg(instr, ro) >> 7),
                                      self._low_reg(instr, ro) << 6 | self._low_reg(instr, rb) << 3 | self._low_reg(instr, rd))

        if ro.lower() in self.high_regs + self.high_regs_aliases:
            raise InvalidRegister(instr)

        return self._build_opcode(0b01100000 | self._imm(instr, ro, 2) >> 5, self._imm(instr, ro, 2) << 6 | self._low_reg(instr, rb) << 3 | self._low_reg(instr, rd))

    @opcode('STRB')
    def _strb(self, instr):
        rd, open_bracket, rb, ro, close_bracket = instr.tokens[1:]

        if open_bracket != '[' or close_bracket != ']':
            return None

        if ro.lower() in self.low_regs:
            return self._build_opcode(0b01010100 | (self._low_reg(instr, ro) >> 7),
                                      self._low_reg(instr, ro) << 6 | self._low_reg(instr, rb) << 3 | self._low_reg(instr, rd))

        if ro.lower() in self.high_regs + self.high_regs_aliases:
            raise InvalidRegister(instr)

        return self._build_opcode(0b01110000 | self._imm(instr, ro, 2) >> 3, self._imm(instr, ro, 2) << 6 | self._low_reg(instr, rb) << 3 | self._low_reg(instr, rd))

    @opcode('LDRB')
    def _ldrb(self, instr):
        rd, open_bracket, rb, ro, close_bracket = instr.tokens[1:]

        if open_bracket != '[' or close_bracket != ']':
            return None

        if ro.lower() in self.low_regs:
            return self._build_opcode(0b01011100 | (self._low_reg(instr, ro) >> 7),
                                      self._low_reg(instr, ro) << 6 | self._low_reg(instr, rb) << 3 | self._low_reg(instr, rd))
        if ro.lower() in self.high_regs + self.high_regs_aliases:
            raise InvalidRegister(instr)

        return self._build_opcode(0b01111000 | self._imm(instr, ro, 2) >> 3, self._imm(instr, ro, 2) << 6 | self._low_reg(instr, rb) << 3 | self._low_reg(instr, rd))

    @opcode('STRH')
    def _strh(self, instr):
        rd, open_bracket, rb, ro, close_bracket = instr.tokens[1:]

        if open_bracket != '[' or close_bracket != ']':
            return None

        if ro.lower() in self.low_regs:
            return self._build_opcode(0b01010010 | (self._low_reg(instr, ro) >> 7),
                                      self._low_reg(instr, ro) << 6 | self._low_reg(instr, rb) << 3 | self._low_reg(instr, rd))

        if ro.lower() in self.high_regs + self.high_regs_aliases:
            raise InvalidRegister(instr)

        return self._build_opcode(0b10000000 | self._imm(instr, ro, 2) >> 3, self._imm(instr, ro, 2) << 6 | self._low_reg(instr, rb) << 3 | self._low_reg(instr, rd))

    @opcode('LDRH')
    def _ldrh(self, instr):
        rd, open_bracket, rb, ro, close_bracket = instr.tokens[1:]

        if open_bracket != '[' or close_bracket != ']':
            return None

        if ro.lower() in self.low_regs:
            return self._build_opcode(0b01011010 | (self._low_reg(instr, ro) >> 7),
                                      self._low_reg(instr, ro) << 6 | self._low_reg(instr, rb) << 3 | self._low_reg(instr, rd))

        if ro.lower() in self.high_regs + self.high_regs_aliases:
            raise InvalidRegister(instr)

        return self._build_opcode(0b10001000 | self._imm(instr, ro, 2) >> 3, self._imm(instr, ro, 2) << 6 | self._low_reg(instr, rb) << 3 | self._low_reg(instr, rd))

    @opcode('LDSB')
    def _ldsb(self, instr):
        rd, open_bracket, rb, ro, close_bracket = instr.tokens[1:]

        if open_bracket != '[' or close_bracket != ']':
            return None

        return self._build_opcode(0b01010110 | (self._low_reg(instr, ro) >> 7),
                                  self._low_reg(instr, ro) << 6 | self._low_reg(instr, rb) << 3 | self._low_reg(instr, rd))

    @opcode('LDSH')
    def _ldsh(self, instr):
        rd, open_bracket, rb, ro, close_bracket = instr.tokens[1:]

        if open_bracket != '[' or close_bracket != ']':
            return None

        return self._build_opcode(0b01011110 | (self._low_reg(instr, ro) >> 7),
                                  self._low_reg(instr, ro) << 6 | self._low_reg(instr, rb) << 3 | self._low_reg(instr, rd))

    @opcode('BL')
    def _bl(self, instr):
        offset = instr.tokens[1]
        address = self.parse_integer(offset)
        if address:
            if not in_bit_range_signed(address, 23):
                raise NotInBitRange('', address, 23, instr)
            address >>= 1
            address0 = address >> 11
            address1 = address & 0x7ff
            return self._build_opcode(0b11110000 | (address0 >> 8), address0) + self._build_opcode(0b11111000 | (address1 >> 8), address1)
        self.add_label_translation(label=offset, bits=(10, 0),
                                   relative=True,
                                   size=2,
                                   offset=0,
                                   alignment=2,
                                   right_shift=12,  # 11 + 1
                                   skip_bit_check=True,
                                   combined_bit_check=23,
                                   start=self.current_org + self.org_counter + 4)
        self.add_label_translation(label=offset, bits=(10, 0),
                                   relative=True,
                                   size=2,
                                   offset=2,
                                   alignment=2,
                                   right_shift=1,
                                   filter=lambda x: x & 0x7FF,  # get first 11 bits
                                   skip_bit_check=True,
                                   combined_bit_check=23,
                                   start=self.current_org + self.org_counter + 4)
        return self._build_opcode(0b11110000, 0) + self._build_opcode(0b11111000, 0)

    @opcode('B')
    def _b(self, instr):
        offset = self._offset(instr, instr.tokens[1], (10, 0), 2)
        return self._build_opcode(0b11100000 | (offset >> 5), offset)

    @opcode('BNE')
    def _bne(self, instr):
        offset = self._offset(instr, instr.tokens[1], (7, 0), 2)
        return self._build_opcode(0b11010001, offset)
