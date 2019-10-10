from necroassembler import Assembler, opcode
from necroassembler.utils import pack, pack_byte, pack_bytes


class AssemblerGameboy(Assembler):

    hex_prefixes = ('$',)

    bin_prefixes = ('%',)

    oct_prefixes = ('@',)

    regs8 = ('A', 'F', 'B', 'C', 'D', 'E', 'H', 'L')
    regs16 = ('AF', 'BC', 'DE', 'HL', 'HL+', 'HL-', 'SP')

    fill_value = 0xFF

    def register_instructions(self):
        self.register_instruction('NOP', b'\x00')
        self.register_instruction('RRCA', b'\x0F')
        self.register_instruction('BRA', b'\x1F')
        self.register_instruction('STOP', b'\x10')
        self.register_instruction('HALT', b'\x76')
        self.register_instruction('DI', b'\xF3')
        self.register_instruction('EI', b'\xF8')

    def _data8(self, arg):
        value = self.parse_integer(arg)
        # label ?
        if value is None:
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
        if arg.upper() in (self.regs8 + self.regs16):
            key = self.reg_name(arg)
        else:
            if 'data8' in kwargs:
                key = 'data8'
                data = self._data8(arg)
            elif 'data16' in kwargs:
                key = 'data16'
                data = self._data16(arg)

        if key is None:
            return None

        return pack_byte(kwargs[key]) + data

    def build_opcode_two_args(self, instr, **kwargs):
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

        if key is None:
            return None

        return pack_byte(kwargs[key]) + data

    def build_opcode_four_args(self, instr, **kwargs):
        args = instr.tokens[1:]
        key = None
        data = b''
        if args[0] == '(' and args[2] == ')':
            dst = args[1]
            src = args[3]
            # invalid combo
            if src.upper() not in self.regs8 and src.upper() != 'SP':
                return None
            if dst.upper() in self.regs16:
                key = 'ind_' + self.reg_name(dst) + '_' + self.reg_name(src)
            else:
                key = 'ind_a16_' + self.reg_name(src)
                data = self._data16(dst)

        elif args[1] == '(' and args[3] == ')':
            dst = args[0]
            src = args[2]
            # invalid combo
            if dst.upper() not in self.regs8:
                return None
            if src.upper() in self.regs16:
                key = self.reg_name(dst) + '_ind_' + self.reg_name(src)
            else:
                key = self.reg_name(dst) + '_ind_a16'
                data = self._data16(src)

        if key is None:
            return None

        return pack_byte(kwargs[key]) + data

    def build_opcode(self, instr, **kwargs):
        args = instr.tokens[1:]
        if len(args) == 1:
            return self.build_opcode_one_arg(instr, **kwargs)
        if len(args) == 2:
            return self.build_opcode_two_args(instr, **kwargs)
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
                                 a_ind_hl_plus=0x2A)

    @opcode('INC')
    def _inc(self, instr):
        return self.build_opcode(instr,
                                 bc=0x03, b=0x04, c=0x0C)


def main():
    import sys
    asm = AssemblerGameboy()
    asm.assemble_file(sys.argv[1])
    asm.link()
    with open(sys.argv[2], 'wb') as f:
        f.write(asm.assembled_bytes)


if __name__ == '__main__':
    main()
