from necroassembler import Assembler, opcode, pack, pack_bytes


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

    @opcode('MOV')
    def _mov(self, tokens):
        # reg8, imm8
        if tokens[1].upper() in self.regs8:
            return self._imm8(0xB0, *tokens[1:])
        # reg16, imm16
        if tokens[1].upper() in self.regs16:
            return self._imm16(0xB8, *tokens[1:])

    @opcode('INT')
    def _int(self, tokens):
        if tokens[1] == '3':
            return b'\xCC'
        return pack_bytes(0xCD, self.parse_integer(tokens[1]))


def main():
    import sys
    asm = AssemblerIntel8086()
    with open(sys.argv[1]) as f:
        asm.assemble(f.read())
    asm.link()
    with open(sys.argv[2], 'wb') as f:
        f.write(asm.assembled_bytes)


if __name__ == '__main__':
    main()
