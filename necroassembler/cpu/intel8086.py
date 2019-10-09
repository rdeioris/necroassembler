from necroassembler import Assembler, opcode
from necroassembler.utils import pack, pack_byte, pack_bytes


class AssemblerIntel8086(Assembler):

    hex_prefixes = ('0x', '0h', '$0')
    hex_suffixes = ('h',)

    dec_prefixes = ('0d',)
    dec_suffixes = ('d',)

    bin_prefixes = ('0b', '0y')
    bin_suffixes = ('b', 'y')

    oct_prefixes = ('0o', '0q')
    oct_suffixes = ('o', 'q')

    regs8 = ('AL', 'CL', 'DL', 'BL', 'AH', 'CH', 'DH', 'BH')
    regs16 = ('AX', 'CX', 'DX', 'BX', 'SP', 'BP', 'SI', 'DI')

    def register_instructions(self):
        self.register_instruction('CLD', b'\xFC')
        self.register_instruction('RET', b'\xC3')

    def _imm8(self, op, reg, arg):
        value = self.parse_integer(arg)
        # label ?
        if value is None:
            self.add_label_translation(label=arg, size=1)
        return pack_bytes(op + self.regs8.index(reg.upper()), value)

    def _imm16(self, op, reg, arg):
        value = self.parse_integer(arg)
        # label ?
        if value is None:
            self.add_label_translation(label=arg, size=2)
        return pack('<BH', op + self.regs16.index(reg.upper()), value)

    def _mem(self, arg):
        value = self.parse_integer(arg)
        # label ?
        if value is None:
            self.add_label_translation(label=arg, size=2)
        return pack('<H', value)

    def _modrm8(self, reg, rm):
        base = 0xC0
        base |= self.regs8.index(reg.upper()) << 5
        base |= self.regs8.index(rm.upper())
        return base

    def _modrm16(self, reg, rm):
        base = 0xC0
        base |= self.regs16.index(reg.upper()) << 5
        base |= self.regs16.index(rm.upper())
        return base

    @opcode('MOV')
    def _mov(self, instr):
        dst, src, *args, = instr.tokens[1:]
        # mem8, AL
        if dst == '[' and args[0] == ']' and args[1].upper() == 'AL':
            return pack_byte(0xA2) + self._mem(src)
        # mem16, AX
        if dst == '[' and args[0] == ']' and args[1].upper() == 'AX':
            return pack_byte(0xA3) + self._mem(src)
        # reg8, reg8
        if dst.upper() in self.regs8 and src.upper() in self.regs8:
            return pack_bytes(0x88, self._modrm8(src, dst))
        # reg16, reg16
        if dst.upper() in self.regs8 and src.upper() in self.regs8:
            return pack_bytes(0x88, self._modrm16(src, dst))
        # reg8, imm8
        if dst.upper() in self.regs8:
            return self._imm8(0xB0, dst, src)
        # reg16, imm16
        if dst.upper() in self.regs16:
            return self._imm16(0xB8, dst, src)

    @opcode('ADD')
    def _add(self, instr):
        dst, src, *_ = instr.tokens[1:]
        # AL, imm8
        if dst.upper() == 'AL':
            return self._imm8(0x04, dst, src)
        # AX, imm16
        if dst.upper() == 'AX':
            return self._imm16(0x05, dst, src)

    @opcode('INT')
    def _int(self, instr):
        arg = instr.tokens[1]
        if arg == '3':
            return b'\xCC'
        return pack_bytes(0xCD, self.parse_integer(arg))

    @opcode('CALL')
    def _call(self, instr):
        arg = instr.tokens[1]
        value = self.parse_integer(arg)
        # label ?
        if value is None:
            self.add_label_translation(
                label=arg, size=2, relative=True, start=self.current_org + self.org_counter + 1)
        return pack('<Bh', 0xE8, value)


def main():
    import sys
    asm = AssemblerIntel8086()
    asm.assemble_file(sys.argv[1])
    asm.link()
    with open(sys.argv[2], 'wb') as f:
        f.write(asm.assembled_bytes)


if __name__ == '__main__':
    main()
