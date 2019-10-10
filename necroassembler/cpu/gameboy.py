from necroassembler import Assembler, opcode
from necroassembler.utils import pack, pack_byte, pack_bytes


class AssemblerGameboy(Assembler):

    hex_prefixes = ('$',)

    bin_prefixes = ('%',)

    oct_prefixes = ('@',)

    regs8 = ('A', 'F', 'B', 'C', 'D', 'E', 'H', 'L')
    regs16 = ('AF', 'BC', 'DE', 'HL', 'HL+', 'HL-', 'SP')
    conditions = ('Z', 'C', 'NZ', 'NC')

    fill_value = 0xFF

    def register_instructions(self):
        self.register_instruction('NOP', b'\x00')
        self.register_instruction('RRCA', b'\x0F')
        self.register_instruction('BRA', b'\x1F')
        self.register_instruction('STOP', b'\x10')
        self.register_instruction('HALT', b'\x76')
        self.register_instruction('DI', b'\xF3')
        self.register_instruction('EI', b'\xF8')
        self.register_instruction('RLA', b'\x17')

    def _data8(self, arg, relative=False):
        value = self.parse_integer(arg)
        # label ?
        if value is None:
            if relative:
                self.add_label_translation(
                    label=arg, size=1, relative=True, start=self.current_org + self.org_counter + 1)
                return pack('b', value)
            else:
                self.add_label_translation(label=arg, size=1)
        return pack_byte(value)

    def _data16(self, arg):
        value = self.parse_integer(arg)
        # label ?
        if value is None:
            self.add_label_translation(label=arg, size=2)
        return pack('<H', value)

    def reg_name(self, reg, prefix=''):
        return prefix + reg.lower().replace('+', '_plus').replace('-', '_minus')

    def build_opcode_one_arg(self, instr, **kwargs):
        arg = instr.tokens[1]
        key = None
        data = b''
        if arg.upper() in (self.regs8 + self.regs16 + self.conditions):
            key = self.reg_name(arg)
        else:
            if 'relative' in kwargs:
                key = 'r8'
                data = self._data8(arg, True)
            elif 'data8' in kwargs:
                key = 'data8'
                data = self._data8(arg)
            elif 'data16' in kwargs:
                key = 'data16'
                data = self._data16(arg)

        if key is None:
            return None

        return pack_byte(kwargs[key]) + data

    def build_opcode_two_args(self, instr, **kwargs):
        relative = kwargs.get('relative', False)
        dst, src = instr.tokens[1:]
        key = None
        data = b''
        if dst.upper() in self.regs8:
            if src.upper() in self.regs8:
                key = self.reg_name(dst) + '_' + self.reg_name(src)
            # avoid 16bit register in 8bit register
            elif src.upper() not in self.regs16:
                key = self.reg_name(dst) + '_d8'
                data = self._data8(src)

        elif dst.upper() in self.regs16:
            if src.upper() in self.regs16:
                key = self.reg_name(dst) + '_' + self.reg_name(src)
            # avoid 8bit register in 16bit register
            elif src.upper() not in self.regs8:
                key = self.reg_name(dst) + '_d16'
                data = self._data16(src)

        elif dst.upper() in self.conditions:
            if relative:
                key = self.reg_name(dst) + '_r8'
                data = self._data8(src, True)
            else:
                key = self.reg_name(dst) + '_a16'
                data = self._data16(src)

        elif src.upper() in self.regs8:
            if dst.upper() in self.regs8:
                key = self.reg_name(dst) + '_' + self.reg_name(src)
            # avoid 8bit value in 16bit register
            elif dst.upper() not in self.regs16:
                key = 'd8_' + self.reg_name(src)
                data = self._data8(dst)

        if key is None:
            return None

        return pack_byte(kwargs[key]) + data

    def build_cb_opcode(self, instr, **kwargs):
        if len(instr.tokens) == 2:
            reg = instr.tokens[1]
            if reg.upper() not in self.regs8:
                return None
            key = self.reg_name(reg)
            return pack_bytes(0xCB, kwargs[key])
        if len(instr.tokens) == 3:
            bn = instr.tokens[1]
            reg = instr.tokens[2]
            if reg not in self.regs8:
                return None
            key = 'b' + str(bn) + '_' + self.reg_name(reg)
            return pack_bytes(0xCB, kwargs[key])

    def build_opcode_four_args(self, instr, **kwargs):
        args = instr.tokens[1:]
        key = None
        data = b''
        if args[0] in ('(', '[') and args[2] in (')', ']'):
            dst = args[1]
            src = args[3]
            # invalid combo
            if src.upper() not in self.regs8 and src.upper() != 'SP':
                return None
            if dst.upper() in self.regs16:
                key = 'ind_' + self.reg_name(dst) + '_' + self.reg_name(src)
            elif dst.upper() == '$FF00+C':
                key = 'ind_c_' + self.reg_name(src)
            elif dst.upper().startswith('$FF00+'):
                key = 'ind_a8_' + self.reg_name(src)
                data = self._data8(dst[6:])
            else:
                key = 'ind_a16_' + self.reg_name(src)
                data = self._data16(dst)

        elif args[1] in ('(', '[') and args[3] in (')', ']'):
            dst = args[0]
            src = args[2]
            # invalid combo
            if dst.upper() not in self.regs8:
                return None
            if src.upper() in self.regs16:
                key = self.reg_name(dst) + '_ind_' + self.reg_name(src)
            elif src.upper() == '$FF00+C':
                key = self.reg_name(dst) + '_ind_c'
            elif src.upper().startswith('$FF00+'):
                key = self.reg_name(dst) + '_ind_a8'
                data = self._data8(src[6:])
            else:
                key = self.reg_name(dst) + '_ind_a16'
                data = self._data16(src)

        if key is None:
            return None

        return pack_byte(kwargs[key]) + data

    def build_opcode_three_args(self, instr, **kwargs):
        args = instr.tokens[1:]
        key = None
        data = b''
        if args[0] in ('(', '[') and args[2] in (')', ']'):
            arg = args[1]
            if arg.upper() in self.regs16:
                key = 'ind_' + self.reg_name(arg)
            else:
                key = 'ind_a16'
                data = self._data16(arg)

        if key is None:
            return None

        return pack_byte(kwargs[key]) + data

    def build_opcode(self, instr, **kwargs):
        args = instr.tokens[1:]
        if len(args) == 1:
            return self.build_opcode_one_arg(instr, **kwargs)
        if len(args) == 2:
            return self.build_opcode_two_args(instr, **kwargs)
        if len(args) == 3:
            return self.build_opcode_three_args(instr, **kwargs)
        if len(args) == 4:
            return self.build_opcode_four_args(instr, **kwargs)

    @opcode('LD')
    def _ld(self, instr):
        return self.build_opcode(instr,
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
        return self.build_opcode(instr,
                                 ind_hl=0x34, a=0x3C, d=0x14,
                                 bc=0x03, b=0x04, c=0x0C,
                                 hl=0x23,
                                 h=0x24,
                                 de=0x13)

    @opcode('JP')
    def _jp(self, instr):
        return self.build_opcode(instr,
                                 z_a16=0xCA,
                                 nc_a16=0xD2,
                                 nz_a16=0xC2,
                                 data16=0xC3)

    @opcode('CALL')
    def _call(self, instr):
        return self.build_opcode(instr,
                                 z_a16=0xCC,
                                 nz_a16=0xC4,
                                 data16=0xCD)

    @opcode('XOR')
    def _xor(self, instr):
        return self.build_opcode(instr, a=0xAF)

    @opcode('CP')
    def _cp(self, instr):
        return self.build_opcode(instr, data8=0xFE,
                                 ind_hl=0xBE,
                                 a_l=0xBD, l=0xBD)

    @opcode('BIT')
    def _bit(self, instr):
        return self.build_cb_opcode(instr, b0_a=0x47,
                                    b1_a=0x4F,
                                    b2_a=0x57,
                                    b3_a=0x5F,
                                    b7_h=0x7C)

    @opcode('RL')
    def _rl(self, instr):
        return self.build_cb_opcode(instr, c=0x11)

    @opcode('DEC')
    def _dec(self, instr):
        return self.build_opcode(instr, ind_hl=0x35,
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
        return self.build_opcode(instr, nz=0xC0)

    @opcode('AND')
    def _and(self, instr):
        return self.build_opcode(instr, data8=0xE6)

    @opcode('OR')
    def _or(self, instr):
        return self.build_opcode(instr, e=0xB3)

    @opcode('JR')
    def _jr(self, instr):
        return self.build_opcode(instr, relative=True,
                                 z_r8=0x20,
                                 r8=0x18,
                                 nz_r8=0x20)

    @opcode('SUB')
    def _sub(self, instr):
        return self.build_opcode(instr, b=0x90)

    @opcode('PUSH')
    def _push(self, instr):
        return self.build_opcode(instr, bc=0xC5)

    @opcode('POP')
    def _pop(self, instr):
        return self.build_opcode(instr, bc=0xC1)

    @opcode('ADD')
    def _add(self, instr):
        return self.build_opcode(instr, ind_hl=0x86, a_ind_hl=0x86)


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
    for b in asm.assembled_bytes:
        global_checksum += int(b)

    asm.assembled_bytes[0x14e] = (global_checksum >> 8) & 0xFF
    asm.assembled_bytes[0x14f] = global_checksum & 0xFF

    with open(sys.argv[2], 'wb') as f:
        f.write(asm.assembled_bytes)


if __name__ == '__main__':
    main()
