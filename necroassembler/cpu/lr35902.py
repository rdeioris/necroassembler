from necroassembler import Assembler, opcode
from necroassembler.utils import pack_byte, pack_le16u, pack_8s
from necroassembler.exceptions import InvalidOpCodeArguments

REGS8 = ('A', 'F', 'B', 'C', 'D', 'E', 'H', 'L')
REGS16 = ('AF', 'BC', 'DE', 'HL', 'HL+', 'HL-', 'SP')
CONDITIONS = ('Z', 'C', 'NZ', 'NC')


def _is_value(token):
    return token.upper() not in REGS8 + REGS16 + CONDITIONS + ('(', ')', '[', ']')


def _is_number(token):
    return token.isdigit()


def _is_ldh(token):
    return token.startswith('$FF00+') and token != '$FF00+C'


VALUE = _is_value
NUMBER = _is_number
LDH = _is_ldh


class AssemblerLR35902(Assembler):

    hex_prefixes = ('$',)

    bin_prefixes = ('%',)

    oct_prefixes = ('@',)

    def register_instructions(self):
        self.register_instruction('NOP', b'\x00')
        self.register_instruction('RRCA', b'\x0F')
        self.register_instruction('BRA', b'\x1F')
        self.register_instruction('HALT', b'\x76')
        self.register_instruction('DI', b'\xF3')
        self.register_instruction('EI', b'\xFB')
        self.register_instruction('RLA', b'\x17')
        self.register_instruction('RLCA', b'\x07')
        self.register_instruction('RRA', b'\x1F')
        self.register_instruction('DAA', b'\x27')
        self.register_instruction('CPL', b'\x2F')
        self.register_instruction('SCF', b'\x37')
        self.register_instruction('CCF', b'\x3f')
        self.register_instruction('RETI', b'\xD9')

    def _data8(self, arg):
        value = self.parse_integer_or_label(
            label=arg, bits_size=8, offset=1, size=1)
        return pack_byte(value)

    def _rel8(self, arg):
        value = self.parse_integer_or_label(label=arg, bits_size=8,
                                            offset=1,
                                            size=1,
                                            relative=self.pc + 2)
        return pack_8s(value)

    def _data16(self, arg):
        value = self.parse_integer_or_label(
            label=arg, bits_size=16, offset=1, size=2)
        return pack_le16u(value)

    def _reg_name(self, reg):
        return reg.lower().replace('+', '_plus').replace('-', '_minus')

    def _build_cb_opcode(self, instr, **kwargs):
        try:

            if instr.match(REGS8):
                reg8, = instr.apply(self._reg_name)
                return pack_byte(0xCB, kwargs[reg8])
            if instr.match('(', 'HL', ')') or instr.match('[', 'HL', ']'):
                return pack_byte(0xCB, kwargs['ind_hl'])
            if instr.match(NUMBER, REGS8):
                value, reg8 = instr.apply(str, self._reg_name)
                return pack_byte(0xCB, kwargs['b' + value + '_' + reg8])
            if instr.match(NUMBER, '(', 'HL', ')') or instr.match(NUMBER, '[', 'HL', ']'):
                value = instr.tokens[1]
                return pack_byte(0xCB, kwargs['b' + value + '_ind_hl'])

        except KeyError:
            raise InvalidOpCodeArguments()

    def _build_opcode(self, instr, **kwargs):
        try:
            if kwargs.get('conditional') and instr.match(CONDITIONS, VALUE):
                relative = kwargs.get('relative')
                if relative:
                    condition, value = instr.apply(self._reg_name, self._rel8)
                    return pack_byte(kwargs[condition + '_r8']) + value
                condition, value = instr.apply(self._reg_name, self._data16)
                return pack_byte(kwargs[condition + '_a16']) + value

            if kwargs.get('conditional') and instr.match(CONDITIONS):
                condition, = instr.apply(self._reg_name)
                return pack_byte(kwargs[condition])

            if instr.match('(', '$FF00+C', ')', 'A') or instr.match('[', '$FF00+C', ']', 'A'):
                return pack_byte(kwargs['ind_c_a'])

            if instr.match('(', LDH, ')', 'A') or instr.match('[', LDH, ']', 'A'):
                value = self._data8(instr.tokens[2][6:])
                return pack_byte(kwargs['ind_a8_a']) + value

            if instr.match('A', '(', LDH, ')') or instr.match('A', '[', LDH, ']'):
                value = self._data8(instr.tokens[3][6:])
                return pack_byte(kwargs['a_ind_a8']) + value

            if instr.match(REGS8, REGS8):
                reg8_d, reg8_s = instr.apply(self._reg_name, self._reg_name)
                return pack_byte(kwargs[reg8_d + '_' + reg8_s])

            if instr.match(REGS16, REGS16):
                reg16_d, reg16_s = instr.apply(self._reg_name, self._reg_name)
                return pack_byte(kwargs[reg16_d + '_' + reg16_s])

            if instr.match(REGS16, VALUE):
                if self._reg_name(instr.tokens[1]) + '_r8' in kwargs:
                    reg16, value = instr.apply(self._reg_name, self._rel8)
                    return pack_byte(kwargs[reg16 + '_r8']) + value
                reg16, value = instr.apply(self._reg_name, self._data16)
                return pack_byte(kwargs[reg16 + '_d16']) + value

            if instr.match('(', REGS16, ')', REGS8) or instr.match('[', REGS16, ']', REGS8):
                reg16, reg8 = instr.apply(
                    None, self._reg_name, None, self._reg_name)
                return pack_byte(kwargs['ind_' + reg16 + '_' + reg8])

            if instr.match(REGS8):
                reg8, = instr.apply(self._reg_name)
                return pack_byte(kwargs[reg8])

            if instr.match(REGS8, VALUE):
                reg8, value = instr.apply(self._reg_name, self._data8)
                return pack_byte(kwargs[reg8 + '_d8']) + value

            if instr.match(REGS16):
                reg16, = instr.apply(self._reg_name)
                return pack_byte(kwargs[reg16])

            if instr.match(REGS8, '(', REGS16, ')') or instr.match(REGS8, '[', REGS16, ']'):
                reg8, reg16 = instr.apply(
                    self._reg_name, None, self._reg_name, None)
                return pack_byte(kwargs[reg8 + '_ind_' + reg16])

            if instr.match(REGS8, '(', REGS8, ')') or instr.match(REGS8, '[', REGS8, ']'):
                reg8, reg8_2 = instr.apply(
                    self._reg_name, None, self._reg_name, None)
                return pack_byte(kwargs[reg8 + '_ind_' + reg8_2])

            if instr.match(REGS8, '(', VALUE, ')') or instr.match(REGS8, '[', VALUE, ']'):
                reg8, value = instr.apply(
                    self._reg_name, None, self._data16, None)
                return pack_byte(kwargs[reg8 + '_ind_a16']) + value

            if instr.match('(', REGS16, ')') or instr.match('[', REGS16, ']'):
                reg16, = instr.apply(
                    None, self._reg_name, None)
                return pack_byte(kwargs['ind_' + reg16])

            if instr.match('(', VALUE, ')', REGS16) or instr.match('[', VALUE, ']', REGS16):
                value, reg16 = instr.apply(
                    None, self._data16, None, self._reg_name)
                return pack_byte(kwargs['ind_a16_' + reg16]) + value

            if instr.match('(', VALUE, ')', REGS8) or instr.match('[', VALUE, ']', REGS8):
                value, reg8 = instr.apply(
                    None, self._data16, None, self._reg_name)
                return pack_byte(kwargs['ind_a16_' + reg8]) + value

            if instr.match('(', REGS16, ')', VALUE) or instr.match('[', REGS16, ']', VALUE):
                reg16, value = instr.apply(
                    None, self._reg_name, None, self._data8)
                return pack_byte(kwargs['ind_' + reg16 + '_d8']) + value

            if instr.match(VALUE):
                if 'r8' in kwargs:
                    value, = instr.apply(self._rel8)
                    return pack_byte(kwargs['r8']) + value
                if 'd8' in kwargs:
                    value, = instr.apply(self._data8)
                    return pack_byte(kwargs['d8']) + value
                if 'd16' in kwargs:
                    value, = instr.apply(self._data16)
                    return pack_byte(kwargs['d16']) + value
                if 'a16' in kwargs:
                    value, = instr.apply(self._data16)
                    return pack_byte(kwargs['a16']) + value

        except KeyError:
            raise InvalidOpCodeArguments()

    @opcode('LDH')
    def _ldh(self, instr):
        if instr.match('(', VALUE, ')', 'A') or instr.match('[', VALUE, ']', 'A'):
            a8, = instr.apply(None, self._data8, None, None)
            return pack_byte(0xE0) + a8
        if instr.match('A', '(', VALUE, ')') or instr.match('A', '[', VALUE, ']'):
            a8, = instr.apply(None, None, self._data8, None)
            return pack_byte(0xF0) + a8

    @opcode('LD')
    def _ld(self, instr):
        if len(instr.tokens) > 2:
            value = None
            if instr.tokens[2].startswith('SP+'):
                value = self._rel8(instr.tokens[2][3:])
            elif instr.tokens[2].startswith('SP-'):
                value = self._rel8(instr.tokens[2][2:])
            if value is not None:
                return pack_byte(0xF8) + value
        return self._build_opcode(instr,
                                  bc_d16=0x01,
                                  ind_bc_a=0x02,
                                  b_d8=0x06,
                                  h_d8=0x26,
                                  ind_a16_sp=0x08,
                                  a_ind_bc=0x0A,
                                  c_d8=0x0E,
                                  c_ind_hl=0x4E,
                                  a_ind_hl_plus=0x2A,
                                  hl_d16=0x21,
                                  de_d16=0x11,
                                  b_a=0x47,
                                  b_b=0x40,
                                  b_c=0x41,
                                  b_d=0x42,
                                  b_e=0x43,
                                  b_h=0x44,
                                  b_l=0x45,
                                  b_ind_hl=0x46,
                                  c_b=0x48,
                                  c_c=0x49,
                                  c_d=0x4A,
                                  c_e=0x4B,
                                  c_h=0x4C,
                                  c_l=0x4D,
                                  d_b=0x50,
                                  d_c=0x51,
                                  d_d=0x52,
                                  d_e=0x53,
                                  d_h=0x54,
                                  d_l=0x55,
                                  d_ind_hl=0x56,
                                  e_b=0x58,
                                  e_c=0x59,
                                  e_d=0x5A,
                                  e_e=0x5B,
                                  e_l=0x5D,
                                  e_h=0x5C,
                                  l_b=0x68,
                                  l_c=0x69,
                                  l_d=0x6a,
                                  l_e=0x6B,
                                  l_h=0x6C,
                                  l_l=0x6d,
                                  l_ind_hl=0x6e,
                                  l_a=0x6f,
                                  h_b=0x60,
                                  h_c=0x61,
                                  h_d=0x62,
                                  h_e=0x63,
                                  h_h=0x64,
                                  h_l=0x65,
                                  h_ind_hl=0x66,
                                  e_ind_hl=0x5E,
                                  e_a=0x5F,
                                  ind_a16_a=0xEA,
                                  a_d8=0x3E,
                                  a_ind_a16=0xFA,
                                  ind_de_a=0x12,
                                  ind_hl_minus_a=0x32,
                                  ind_hl_plus_a=0x22,
                                  d_d8=0x16,
                                  d_a=0x57,
                                  a_d=0x7A,
                                  ind_hl_d8=0x36,
                                  ind_c_a=0xE2,
                                  ind_hl_a=0x77,
                                  ind_a8_a=0xE0,
                                  a_ind_de=0x1A,
                                  a_ind_hl_minus=0x3A,
                                  a_e=0x7B,
                                  l_d8=0x2E,
                                  h_a=0x67,
                                  e_d8=0x1E,
                                  a_ind_a8=0xF0,
                                  a_h=0x7C,
                                  c_a=0x4F,
                                  a_l=0x7D,
                                  a_b=0x78,
                                  a_c=0x79,
                                  a_ind_hl=0x7E,
                                  a_a=0x7F,
                                  ind_hl_b=0x70,
                                  ind_hl_c=0x71,
                                  ind_hl_d=0x72,
                                  ind_hl_e=0x73,
                                  ind_hl_h=0x74,
                                  ind_hl_l=0x75,
                                  a_ind_c=0xF2,
                                  sp_hl=0xF9,
                                  sp_d16=0x31)

    @opcode('INC')
    def _inc(self, instr):
        return self._build_opcode(instr,
                                  ind_hl=0x34,
                                  a=0x3C,
                                  d=0x14,
                                  bc=0x03,
                                  b=0x04,
                                  c=0x0C,
                                  e=0x1c,
                                  hl=0x23,
                                  h=0x24,
                                  l=0x2C,
                                  de=0x13,
                                  sp=0x33)

    @opcode('JP')
    def _jp(self, instr):
        return self._build_opcode(instr,
                                  conditional=True,
                                  c_a16=0xDA,
                                  z_a16=0xCA,
                                  nc_a16=0xD2,
                                  nz_a16=0xC2,
                                  ind_hl=0xE9,
                                  a16=0xC3)

    @opcode('CALL')
    def _call(self, instr):
        return self._build_opcode(instr,
                                  conditional=True,
                                  c_a16=0xDC,
                                  nc_a16=0xD4,
                                  z_a16=0xCC,
                                  nz_a16=0xC4,
                                  a16=0xCD)

    @opcode('XOR')
    def _xor(self, instr):
        return self._build_opcode(instr,
                                  b=0xA8,
                                  c=0xA9,
                                  d=0xAA,
                                  e=0xAb,
                                  h=0xAC,
                                  l=0xAD,
                                  ind_hl=0xAE,
                                  a_d8=0xEE, d8=0xEE,
                                  a=0xAF, a_a=0xAF)

    @opcode('CP')
    def _cp(self, instr):
        return self._build_opcode(instr,
                                  d8=0xFE,
                                  a_b=0xB8, b=0xB8,
                                  a_c=0xB9, c=0xB9,
                                  a_d=0xBA, d=0xBA,
                                  a_e=0xBB, e=0xBB,
                                  a_h=0xBC, h=0xBC,
                                  a_l=0xBD, l=0xBD,
                                  a_ind_hl=0xBE, ind_hl=0xBE,
                                  a_a=0xBF, a=0xBF)

    @opcode('BIT')
    def _bit(self, instr):
        return self._build_cb_opcode(instr,
                                     b0_b=0x40,
                                     b0_c=0x41,
                                     b0_d=0x42,
                                     b0_e=0x43,
                                     b0_h=0x44,
                                     b0_l=0x45,
                                     b0_ind_hl=0x46,
                                     b0_a=0x47,
                                     b1_b=0x48,
                                     b1_c=0x49,
                                     b1_d=0x4A,
                                     b1_e=0x4B,
                                     b1_h=0x4C,
                                     b1_l=0x4D,
                                     b1_ind_hl=0x4E,
                                     b1_a=0x4F,
                                     b2_b=0x50,
                                     b2_c=0x51,
                                     b2_d=0x52,
                                     b2_e=0x53,
                                     b2_h=0x54,
                                     b2_l=0x55,
                                     b2_ind_hl=0x56,
                                     b2_a=0x57,
                                     b3_b=0x58,
                                     b3_c=0x59,
                                     b3_d=0x5A,
                                     b3_e=0x5B,
                                     b3_h=0x5C,
                                     b3_l=0x5D,
                                     b3_ind_hl=0x5E,
                                     b3_a=0x5F,
                                     b4_b=0x60,
                                     b4_c=0x61,
                                     b4_d=0x62,
                                     b4_e=0x63,
                                     b4_h=0x64,
                                     b4_l=0x65,
                                     b4_ind_hl=0x66,
                                     b4_a=0x67,
                                     b5_b=0x68,
                                     b5_c=0x69,
                                     b5_d=0x6A,
                                     b5_e=0x6B,
                                     b5_h=0x6C,
                                     b5_l=0x6D,
                                     b5_ind_hl=0x6E,
                                     b5_a=0x6F,
                                     b6_b=0x70,
                                     b6_c=0x71,
                                     b6_d=0x72,
                                     b6_e=0x73,
                                     b6_h=0x74,
                                     b6_l=0x75,
                                     b6_ind_hl=0x76,
                                     b6_a=0x77,
                                     b7_b=0x78,
                                     b7_c=0x79,
                                     b7_d=0x7A,
                                     b7_e=0x7B,
                                     b7_h=0x7C,
                                     b7_l=0x7D,
                                     b7_ind_hl=0x7E,
                                     b7_a=0x7F)

    @opcode('RES')
    def _res(self, instr):
        return self._build_cb_opcode(instr,
                                     b0_b=0x80,
                                     b0_c=0x81,
                                     b0_d=0x82,
                                     b0_e=0x83,
                                     b0_h=0x84,
                                     b0_l=0x85,
                                     b0_ind_hl=0x86,
                                     b0_a=0x87,
                                     b1_b=0x88,
                                     b1_c=0x89,
                                     b1_d=0x8A,
                                     b1_e=0x8B,
                                     b1_h=0x8C,
                                     b1_l=0x8D,
                                     b1_ind_hl=0x8E,
                                     b1_a=0x8F,
                                     b2_b=0x90,
                                     b2_c=0x91,
                                     b2_d=0x92,
                                     b2_e=0x93,
                                     b2_h=0x94,
                                     b2_l=0x95,
                                     b2_ind_hl=0x96,
                                     b2_a=0x97,
                                     b3_b=0x98,
                                     b3_c=0x99,
                                     b3_d=0x9A,
                                     b3_e=0x9B,
                                     b3_h=0x9C,
                                     b3_l=0x9D,
                                     b3_ind_hl=0x9E,
                                     b3_a=0x9F,
                                     b4_b=0xA0,
                                     b4_c=0xA1,
                                     b4_d=0xA2,
                                     b4_e=0xA3,
                                     b4_h=0xA4,
                                     b4_l=0xA5,
                                     b4_ind_hl=0xA6,
                                     b4_a=0xA7,
                                     b5_b=0xA8,
                                     b5_c=0xA9,
                                     b5_d=0xAA,
                                     b5_e=0xAB,
                                     b5_h=0xAC,
                                     b5_l=0xAD,
                                     b5_ind_hl=0xAE,
                                     b5_a=0xAF,
                                     b6_b=0xB0,
                                     b6_c=0xB1,
                                     b6_d=0xB2,
                                     b6_e=0xB3,
                                     b6_h=0xB4,
                                     b6_l=0xB5,
                                     b6_ind_hl=0xB6,
                                     b6_a=0xB7,
                                     b7_b=0xB8,
                                     b7_c=0xB9,
                                     b7_d=0xBA,
                                     b7_e=0xBB,
                                     b7_h=0xBC,
                                     b7_l=0xBD,
                                     b7_ind_hl=0xBE,
                                     b7_a=0xBF)

    @opcode('SET')
    def _set(self, instr):
        return self._build_cb_opcode(instr,
                                     b0_b=0xC0,
                                     b0_c=0xC1,
                                     b0_d=0xC2,
                                     b0_e=0xC3,
                                     b0_h=0xC4,
                                     b0_l=0xC5,
                                     b0_ind_hl=0xC6,
                                     b0_a=0xC7,
                                     b1_b=0xC8,
                                     b1_c=0xC9,
                                     b1_d=0xCA,
                                     b1_e=0xCB,
                                     b1_h=0xCC,
                                     b1_l=0xCD,
                                     b1_ind_hl=0xCE,
                                     b1_a=0xCF,
                                     b2_b=0xD0,
                                     b2_c=0xD1,
                                     b2_d=0xD2,
                                     b2_e=0xD3,
                                     b2_h=0xD4,
                                     b2_l=0xD5,
                                     b2_ind_hl=0xD6,
                                     b2_a=0xD7,
                                     b3_b=0xD8,
                                     b3_c=0xD9,
                                     b3_d=0xDA,
                                     b3_e=0xDB,
                                     b3_h=0xDC,
                                     b3_l=0xDD,
                                     b3_ind_hl=0xDE,
                                     b3_a=0xDF,
                                     b4_b=0xE0,
                                     b4_c=0xE1,
                                     b4_d=0xE2,
                                     b4_e=0xE3,
                                     b4_h=0xE4,
                                     b4_l=0xE5,
                                     b4_ind_hl=0xE6,
                                     b4_a=0xE7,
                                     b5_b=0xE8,
                                     b5_c=0xE9,
                                     b5_d=0xEA,
                                     b5_e=0xEB,
                                     b5_h=0xEC,
                                     b5_l=0xED,
                                     b5_ind_hl=0xEE,
                                     b5_a=0xEF,
                                     b6_b=0xF0,
                                     b6_c=0xF1,
                                     b6_d=0xF2,
                                     b6_e=0xF3,
                                     b6_h=0xF4,
                                     b6_l=0xF5,
                                     b6_ind_hl=0xF6,
                                     b6_a=0xF7,
                                     b7_b=0xF8,
                                     b7_c=0xF9,
                                     b7_d=0xFA,
                                     b7_e=0xFB,
                                     b7_h=0xFC,
                                     b7_l=0xFD,
                                     b7_ind_hl=0xFE,
                                     b7_a=0xFF)

    @opcode('RLC')
    def _rlc(self, instr):
        return self._build_cb_opcode(instr,
                                     b=0x00,
                                     c=0x01,
                                     d=0x02,
                                     e=0x03,
                                     h=0x04,
                                     l=0x05,
                                     ind_hl=0x06,
                                     a=0x07)

    @opcode('RRC')
    def _rrc(self, instr):
        return self._build_cb_opcode(instr,
                                     b=0x08,
                                     c=0x09,
                                     d=0x0A,
                                     e=0x0B,
                                     h=0x0C,
                                     l=0x0D,
                                     ind_hl=0x0E,
                                     a=0x0F)

    @opcode('RL')
    def _rl(self, instr):
        return self._build_cb_opcode(instr,
                                     b=0x10,
                                     c=0x11,
                                     d=0x12,
                                     e=0x13,
                                     h=0x14,
                                     l=0x15,
                                     ind_hl=0x16,
                                     a=0x17)

    @opcode('RR')
    def _rr(self, instr):
        return self._build_cb_opcode(instr,
                                     b=0x18,
                                     c=0x19,
                                     d=0x1A,
                                     e=0x1B,
                                     h=0x1C,
                                     l=0x1D,
                                     ind_hl=0x1E,
                                     a=0x1F)

    @opcode('SLA')
    def _sla(self, instr):
        return self._build_cb_opcode(instr,
                                     b=0x20,
                                     c=0x21,
                                     d=0x22,
                                     e=0x23,
                                     h=0x24,
                                     l=0x25,
                                     ind_hl=0x26,
                                     a=0x27)

    @opcode('SRA')
    def _sra(self, instr):
        return self._build_cb_opcode(instr,
                                     b=0x28,
                                     c=0x29,
                                     d=0x2A,
                                     e=0x2B,
                                     h=0x2C,
                                     l=0x2D,
                                     ind_hl=0x2E,
                                     a=0x2F)

    @opcode('SRL')
    def _srl(self, instr):
        return self._build_cb_opcode(instr,
                                     b=0x38,
                                     c=0x39,
                                     d=0x3A,
                                     e=0x3B,
                                     h=0x3C,
                                     l=0x3D,
                                     ind_hl=0x3E,
                                     a=0x3F)

    @opcode('SWAP')
    def _swap(self, instr):
        return self._build_cb_opcode(instr,
                                     b=0x30,
                                     c=0x31,
                                     d=0x32,
                                     e=0x33,
                                     h=0x34,
                                     l=0x35,
                                     ind_hl=0x36,
                                     a=0x37)

    @opcode('DEC')
    def _dec(self, instr):
        return self._build_opcode(instr,
                                  ind_hl=0x35,
                                  b=0x05,
                                  a=0x3D,
                                  c=0x0D,
                                  d=0x15,
                                  e=0x1D,
                                  h=0x25,
                                  l=0x2D,
                                  bc=0x0B,
                                  de=0x1B,
                                  hl=0x2B,
                                  sp=0x3B)

    @opcode('RET')
    def _ret(self, instr):
        if len(instr.tokens) == 1:
            return b'\xC9'
        return self._build_opcode(instr,
                                  conditional=True,
                                  c=0xD8,
                                  nc=0xD0,
                                  z=0xC8,
                                  nz=0xC0)

    @opcode('AND')
    def _and(self, instr):
        return self._build_opcode(instr,
                                  b=0xA0,
                                  c=0xA1,
                                  d=0xA2,
                                  e=0xA3,
                                  h=0xA4,
                                  l=0xA5,
                                  ind_hl=0xA6,
                                  a=0xA7,
                                  d8=0xE6)

    @opcode('OR')
    def _or(self, instr):
        return self._build_opcode(instr,
                                  a_b=0xB0, b=0xB0,
                                  a_c=0xB1, c=0xB1,
                                  a_d=0xB2, d=0xB2,
                                  a_e=0xB3, e=0xB3,
                                  a_h=0xB4, h=0xB4,
                                  a_l=0xB5, l=0xB5,
                                  a_ind_hl=0xB6, ind_hl=0xB6,
                                  a_d8=0xF6, d8=0xF6,
                                  a_a=0xB7, a=0xB7)

    @opcode('JR')
    def _jr(self, instr):
        return self._build_opcode(instr,
                                  conditional=True,
                                  relative=True,
                                  z_r8=0x28,
                                  c_r8=0x38,
                                  r8=0x18,
                                  nc_r8=0x30,
                                  nz_r8=0x20)

    @opcode('SUB')
    def _sub(self, instr):
        return self._build_opcode(instr,
                                  b=0x90,
                                  c=0x91,
                                  d=0x92,
                                  e=0x93,
                                  h=0x94,
                                  l=0x95,
                                  ind_hl=0x96,
                                  a=0x97,
                                  a_d8=0xD6, d8=0xD6)

    @opcode('PUSH')
    def _push(self, instr):
        return self._build_opcode(instr,
                                  bc=0xC5,
                                  hl=0xE5,
                                  af=0xF5,
                                  de=0xD5)

    @opcode('POP')
    def _pop(self, instr):
        return self._build_opcode(instr,
                                  bc=0xC1,
                                  hl=0xE1,
                                  af=0xF1,
                                  de=0xD1)

    @opcode('ADD')
    def _add(self, instr):
        return self._build_opcode(instr,
                                  a_b=0x80,
                                  a_c=0x81,
                                  a_d=0x82,
                                  a_e=0x83,
                                  a_h=0x84,
                                  a_l=0x85,
                                  a_a=0x87,
                                  ind_hl=0x86,
                                  hl_bc=0x09,
                                  hl_de=0x19,
                                  hl_hl=0x29,
                                  hl_sp=0x39,
                                  a_d8=0xC6,
                                  sp_r8=0xE8,
                                  a_ind_hl=0x86)

    @opcode('ADC')
    def _adc(self, instr):
        return self._build_opcode(instr,
                                  a_b=0x88,
                                  a_c=0x89,
                                  a_d=0x8A,
                                  a_e=0x8B,
                                  a_h=0x8C,
                                  a_l=0x8D,
                                  a_ind_hl=0x8E,
                                  a_a=0x8F,
                                  a_d8=0xCE,
                                  )

    @opcode('SBC')
    def _sbc(self, instr):
        return self._build_opcode(instr,
                                  a_b=0x98,
                                  a_c=0x99,
                                  a_d=0x9A,
                                  a_e=0x9B,
                                  a_h=0x9C,
                                  a_l=0x9D,
                                  a_ind_hl=0x9E,
                                  a_a=0x9F,
                                  a_d8=0xDE, d8=0xDE
                                  )

    @opcode('STOP')
    def _stop(self, instr):
        if len(instr.tokens) == 1 or instr.match('0'):
            return pack_byte(0x10, 0x00)

    @opcode('RST')
    def _rst(self, instr):
        vectors_table = {'00H': 0xC7, '08H': 0xCF, '10H': 0xD7,
                         '18H': 0xDf, '20H': 0xE7, '28H': 0xEF, '30H': 0xF7, '38H': 0xFF}
        if instr.match(vectors_table.keys()):
            return pack_byte(vectors_table[instr.tokens[1].upper()])


if __name__ == '__main__':
    AssemblerLR35902.main()
