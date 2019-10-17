
from necroassembler import Assembler, opcode
from necroassembler.utils import pack_bits_be16u, pack_byte, pack_be16u, pack_be32u


D_REGS = ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7')
A_REGS = ('a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7')


def _is_immediate(token):
    return len(token) > 1 and token.startswith('#')


def _is_address(token):
    return token.lower() not in D_REGS + A_REGS + ('(', ')') and not token.startswith('#')


IMMEDIATE = _is_immediate
ADDRESS = _is_address


def _reg(token):
    return int(token[1:])


def _suffix(token):
    if token.lower().endswith('.b'):
        return 1, 0, None, 1
    if token.lower().endswith('.l'):
        return 4, 2, 1, 2
    if token.lower().endswith('.w'):
        return 2, 1, 0, 3
    return 2, 1, 0, 3


class AssemblerMC68000(Assembler):

    hex_prefixes = ('$',)

    bin_prefixes = ('%',)

    special_prefixes = ('#',)

    big_endian = True

    def _value8(self, token):
        value = self.parse_integer_or_label(token[1:], size=2, offset=2)
        return pack_be16u(value & 0xff)

    def _value16(self, token):
        value = self.parse_integer_or_label(token[1:], size=2, offset=2)
        return pack_be16u(value)

    def _value32(self, token):
        value = self.parse_integer_or_label(token[1:], size=4, offset=2)
        return pack_be32u(value)

    def _raw(self, token):
        return self.parse_integer_or_label(token[1:], size=1, offset=2)

    def _addr(self, token):
        value = self.parse_integer_or_label(token, size=4, offset=2)
        return pack_be32u(value)

    def _value(self, size):
        if size == 1:
            return self._value8
        if size == 2:
            return self._value16
        if size == 4:
            return self._value32

    def _build_opcode(self, base, *args):
        return pack_bits_be16u(base, *args)

    @opcode('move', 'move.w', 'move.b', 'move.l')
    def _move(self, instr):
        size, _, _, op_size = _suffix(instr.tokens[0])
        if instr.match(IMMEDIATE, D_REGS):
            value, reg = instr.apply(self._value(size), _reg)
            return self._build_opcode(0b0000000000111100, ((13, 12), op_size), ((11, 9), reg)) + value

    @opcode('moveq')
    def _moveq(self, instr):
        if instr.match(IMMEDIATE, D_REGS):
            value, reg = instr.apply(self._raw, _reg)
            return self._build_opcode(0b0111000000000000, ((11, 9), reg), ((7, 0), value))

    @opcode('jmp')
    def _jmp(self, instr):
        if instr.match(ADDRESS):
            address, = instr.apply(self._addr)
            return self._build_opcode(0b0100111011111001) + address


def main():
    import sys
    asm = AssemblerMC68000()
    asm.assemble_file(sys.argv[1])
    asm.link()
    asm.save(sys.argv[2])


if __name__ == '__main__':
    main()
