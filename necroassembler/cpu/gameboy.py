from necroassembler import Assembler, opcode
from necroassembler.utils import pack_byte, pack_le16u, pack_8s
from necroassembler.exceptions import InvalidOpCodeArguments

REGS8 = ('A', 'F', 'B', 'C', 'D', 'E', 'H', 'L')
REGS16 = ('AF', 'BC', 'DE', 'HL', 'HL+', 'HL-', 'SP')
CONDITIONS = ('Z', 'C', 'NZ', 'NC')


def _is_value(token):
    return token.upper() not in REGS8 + REGS16 + CONDITIONS + ('(', ')')


def _is_number(token):
    return token.isdigit()


def _is_ldh(token):
    return token.startswith('$FF00+') and token != '$FF00+C'


VALUE = _is_value
NUMBER = _is_number
LDH = _is_ldh


class AssemblerGameboy(Assembler):

    hex_prefixes = ('$',)

    bin_prefixes = ('%',)

    oct_prefixes = ('@',)

    fill_value = 0xFF

    def register_instructions(self):
        self.register_instruction('NOP', b'\x00')
        self.register_instruction('RRCA', b'\x0F')
        self.register_instruction('BRA', b'\x1F')
        self.register_instruction('HALT', b'\x76')
        self.register_instruction('DI', b'\xF3')
        self.register_instruction('EI', b'\xF8')
        self.register_instruction('RLA', b'\x17')

    def _data8(self, arg):
        value = self.parse_integer_or_label(arg, size=1)
        return pack_byte(value)

    def _rel8(self, arg):
        value = self.parse_integer_or_label(arg,
                                            size=1,
                                            relative=True,
                                            start=self.current_org + self.org_counter + 2)
        return pack_8s(value)

    def _data16(self, arg):
        value = self.parse_integer_or_label(arg, size=2)
        return pack_le16u(value)

    def _reg_name(self, reg, prefix=''):
        return prefix + reg.lower().replace('+', '_plus').replace('-', '_minus')

    def _build_cb_opcode(self, instr, **kwargs):
        try:

            if instr.match(REGS8):
                reg8, = instr.apply(self._reg_name)
                return pack_byte(0xCB, kwargs[reg8])
            if instr.match('(', 'HL', ')'):
                return pack_byte(0xCB, kwargs['ind_hl'])
            if instr.match(NUMBER, REGS8):
                value, reg8 = instr.apply(str, self._reg_name)
                return pack_byte(0xCB, kwargs['b' + value + '_' + reg8])
            if instr.match(NUMBER, '(', 'HL', ')'):
                return pack_byte(0xCB, kwargs['b' + value + 'ind_hl'])

        except KeyError:
            raise InvalidOpCodeArguments()

    def _build_opcode(self, instr, **kwargs):
        try:
            if instr.match('(', '$FF00+C', ')', 'A'):
                return pack_byte(kwargs['ind_c_a'])

            if instr.match('(', LDH, ')', 'A'):
                value = self._data8(instr.tokens[2][6:])
                return pack_byte(kwargs['ind_a8_a']) + value

            if instr.match('A', '(', LDH, ')'):
                value = self._data8(instr.tokens[3][6:])
                return pack_byte(kwargs['a_ind_a8']) + value

            if instr.match(REGS8, REGS8):
                reg8_d, reg8_s = instr.apply(self._reg_name, self._reg_name)
                return pack_byte(kwargs[reg8_d + '_' + reg8_s])

            if instr.match(REGS16, VALUE):
                reg16, value = instr.apply(self._reg_name, self._data16)
                return pack_byte(kwargs[reg16 + '_d16']) + value

            if instr.match('(', REGS16, ')', REGS8):
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

            if instr.match(REGS8, '(', REGS16, ')'):
                reg8, reg16 = instr.apply(
                    self._reg_name, None, self._reg_name, None)
                return pack_byte(kwargs[reg8 + '_ind_' + reg16])

            if instr.match('(', REGS16, ')'):
                reg16, = instr.apply(
                    None, self._reg_name, None)
                return pack_byte(kwargs['ind_' + reg16])

            if instr.match('(', VALUE, ')', REGS16):
                value, reg16 = instr.apply(
                    None, self._data16, None, self._reg_name)
                return pack_byte(kwargs['ind_a16_' + reg16]) + value

            if instr.match('(', VALUE, ')', REGS8):
                value, reg8 = instr.apply(
                    None, self._data16, None, self._reg_name)
                return pack_byte(kwargs['ind_a16_' + reg8]) + value

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

            if instr.match(CONDITIONS, VALUE):
                relative = kwargs.get('relative')
                if relative:
                    condition, value = instr.apply(self._reg_name, self._rel8)
                    return pack_byte(kwargs[condition + '_r8']) + value
                condition, value = instr.apply(self._reg_name, self._data16)
                return pack_byte(kwargs[condition + '_a16']) + value

        except KeyError:
            raise InvalidOpCodeArguments()

    @opcode('LD')
    def _ld(self, instr):
        return self._build_opcode(instr,
                                  bc_d16=0x01,
                                  ind_bc_a=0x02,
                                  b_d8=0x06,
                                  ind_a16_sp=0x08,
                                  a_ind_bc=0x0A,
                                  c_d8=0x0E,
                                  a_ind_hl_plus=0x2A,
                                  hl_d16=0x21,
                                  de_d16=0x11,
                                  ind_a16_a=0xEA,
                                  a_d8=0x3E,
                                  a_ind_a16=0xFA,
                                  ind_hl_minus_a=0x32,
                                  ind_hl_plus_a=0x22,
                                  d_d8=0x16,
                                  d_a=0x57,
                                  a_d=0x7A,
                                  ind_c_a=0xE2,
                                  ind_hl_a=0x77,
                                  ind_a8_a=0xE0,
                                  a_ind_de=0x1A,
                                  a_e=0x78,
                                  l_d8=0x2E,
                                  h_a=0x67,
                                  e_d8=0x1E,
                                  a_ind_a8=0xF0,
                                  a_h=0x7C,
                                  c_a=0x4F,
                                  a_l=0x7D,
                                  a_b=0x78,
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
                                  hl=0x23,
                                  h=0x24,
                                  de=0x13)

    @opcode('JP')
    def _jp(self, instr):
        return self._build_opcode(instr,
                                  z_a16=0xCA,
                                  nc_a16=0xD2,
                                  nz_a16=0xC2,
                                  a16=0xC3)

    @opcode('CALL')
    def _call(self, instr):
        return self._build_opcode(instr,
                                  z_a16=0xCC,
                                  nz_a16=0xC4,
                                  a16=0xCD)

    @opcode('XOR')
    def _xor(self, instr):
        return self._build_opcode(instr, a=0xAF)

    @opcode('CP')
    def _cp(self, instr):
        return self._build_opcode(instr,
                                  d8=0xFE,
                                  ind_hl=0xBE,
                                  a_l=0xBD, l=0xBD)

    @opcode('BIT')
    def _bit(self, instr):
        return self._build_cb_opcode(instr,
                                     b0_a=0x47,
                                     b1_a=0x4F,
                                     b2_a=0x57,
                                     b3_a=0x5F,
                                     b7_h=0x7C)

    @opcode('RL')
    def _rl(self, instr):
        return self._build_cb_opcode(instr, c=0x11)

    @opcode('DEC')
    def _dec(self, instr):
        return self._build_opcode(instr,
                                  ind_hl=0x35,
                                  b=0x05,
                                  a=0x3D,
                                  c=0x0D,
                                  d=0x15,
                                  e=0x1D,
                                  de=0x1B)

    @opcode('RET')
    def _ret(self, instr):
        if len(instr.tokens) == 1:
            return b'\xC9'
        return self._build_opcode(instr, nz=0xC0)

    @opcode('AND')
    def _and(self, instr):
        return self._build_opcode(instr, d8=0xE6)

    @opcode('OR')
    def _or(self, instr):
        return self._build_opcode(instr, e=0xB3)

    @opcode('JR')
    def _jr(self, instr):
        return self._build_opcode(instr, relative=True,
                                  z_r8=0x20,
                                  r8=0x18,
                                  nz_r8=0x20)

    @opcode('SUB')
    def _sub(self, instr):
        return self._build_opcode(instr, b=0x90)

    @opcode('PUSH')
    def _push(self, instr):
        return self._build_opcode(instr, bc=0xC5)

    @opcode('POP')
    def _pop(self, instr):
        return self._build_opcode(instr, bc=0xC1)

    @opcode('ADD')
    def _add(self, instr):
        return self._build_opcode(instr, ind_hl=0x86, a_ind_hl=0x86)

    @opcode('STOP')
    def _stop(self, instr):
        if len(instr.tokens) == 1 or (len(instr.tokens) == 2 and instr.tokens[1] == '0'):
            return pack_byte(0x10, 0x00)


def main():
    import sys
    asm = AssemblerGameboy()
    asm.assemble_file(sys.argv[1])
    asm.link()

    # fix checksums

    # header checksum
    header_checksum = 0
    for i in range(0x134, 0x14d):
        header_checksum = header_checksum - int(asm.assembled_bytes[i]) - 1
    asm.assembled_bytes[0x14d] = header_checksum & 0xFF

    # global checksum
    global_checksum = 0
    for byte in asm.assembled_bytes:
        global_checksum += int(byte)

    asm.assembled_bytes[0x14e] = (global_checksum >> 8) & 0xFF
    asm.assembled_bytes[0x14f] = global_checksum & 0xFF

    asm.save(sys.argv[2])


if __name__ == '__main__':
    main()
