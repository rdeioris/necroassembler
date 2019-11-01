
from necroassembler import Assembler, opcode
from necroassembler.utils import pack_bits_be16u, pack_byte, pack_be16u, pack_be32u
from necroassembler.exceptions import AssemblerException


class InvalidMode(AssemblerException):
    message = 'invalid 68000 mode'


D_REGS = ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7')
A_REGS = ('a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7')


def _is_immediate(token):
    return len(token) > 1 and token.startswith('#')


def _is_displacement(token):
    return token.lower() not in D_REGS + A_REGS + ('(', ')') and not token.startswith('#')


def _is_indexed_reg(token):
    if token.lower().endswith('.w'):
        return token.lower()[0:-2] in D_REGS+A_REGS
    if token.lower().endswith('.l'):
        return token.lower()[0:-2] in D_REGS+A_REGS
    return token in D_REGS+A_REGS


IMMEDIATE = _is_immediate
DISPLACEMENT = _is_displacement
INDEXED_REG = _is_indexed_reg
ABSOLUTE = _is_displacement


def _reg(token):
    return int(token[1:])


def _indexed_reg(token):
    d_or_a = 0 if token.lower().startswith('d') else 1
    if token.lower().endswith('.w'):
        return d_or_a, _reg(token[0:-2]), 0
    if token.lower().endswith('.l'):
        return d_or_a, _reg(token[0:-2]), 1
    return d_or_a, _reg(token), 0


def _s_light(token):
    token = token.lower()
    if token.endswith('.b'):
        return 1, 0
    if token.endswith('.l'):
        return 4, 2
    if token.endswith('.w'):
        return 2, 1
    return 2, 1


def _s_dark(token):
    token = token.lower()
    if token.endswith('.b'):
        return 1, 1
    if token.endswith('.l'):
        return 4, 2
    if token.endswith('.w'):
        return 2, 3
    return 2, 3


def _s_middle(token):
    token = token.lower()
    if token.endswith('.l'):
        return 4, 1
    if token.endswith('.w'):
        return 2, 0
    return 2, 0


class AssemblerMC68000(Assembler):

    hex_prefixes = ('$',)

    bin_prefixes = ('%',)

    special_prefixes = ('#',)

    big_endian = True

    def register_instructions(self):
        self.register_instruction('RTS', b'\x4E\x75')
        self.register_instruction('NOP', b'\x4E\x71')

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

    def _mode(self, instr, start_index, offset, size):
        # Dn
        found, index = instr.unbound_match(D_REGS, start=start_index)
        if found:
            return index, 0, _reg(instr.tokens[start_index]), b''

        # An
        found, index = instr.unbound_match(A_REGS, start=start_index)
        if found:
            return index, 1, _reg(instr.tokens[start_index]), b''

        # (An)+ must be checked before (An) !
        found, index = instr.unbound_match(
            '(', A_REGS, ')', '+', start=start_index)
        if found:
            return index, 3, _reg(instr.tokens[start_index+1]), b''

        # (An)
        found, index = instr.unbound_match('(', A_REGS, ')', start=start_index)
        if found:
            return index, 2, _reg(instr.tokens[start_index+1]), b''

        # -(An)
        found, index = instr.unbound_match(
            '-', '(', A_REGS, ')', start=start_index)
        if found:
            return index, 4, _reg(instr.tokens[start_index+2]), b''

        # (d, An)
        found, index = instr.unbound_match(
            '(', DISPLACEMENT, A_REGS, ')', start=start_index)
        if found:
            value = self.parse_integer_or_label(instr.tokens[start_index+1],
                                                size=2,
                                                bits_size=16,
                                                signed=True,
                                                offset=2+offset)
            return index, 5, _reg(instr.tokens[start_index+2]), pack_be16u(value)

        # (d, An, Xn)
        found, index = instr.unbound_match(
            '(', DISPLACEMENT, A_REGS, INDEXED_REG, ')', start=start_index)
        if found:
            value = self.parse_integer_or_label(instr.tokens[start_index+1],
                                                size=2,
                                                bits_size=8,
                                                bits=(7, 0),
                                                signed=True,
                                                offset=2+offset)
            m, xn, s = _indexed_reg(instr.tokens[start_index+3])
            return index, 6, _reg(instr.tokens[start_index+2]), pack_bits_be16u(0, ((15, 15), m), ((14, 12), xn), ((11, 11), s), ((7, 0), value))

        # (d, PC)
        found, index = instr.unbound_match(
            '(', DISPLACEMENT, 'PC', ')', start=start_index)
        if found:
            value = self.parse_integer_or_label(instr.tokens[start_index+1],
                                                size=2,
                                                bits_size=16,
                                                relative=self.pc+2+offset,
                                                offset=2+offset)
            return index, 7, 2, pack_be16u(value)

        # (d, PC, Xn)
        found, index = instr.unbound_match(
            '(', DISPLACEMENT, 'PC', INDEXED_REG, ')', start=start_index)
        if found:
            value = self.parse_integer_or_label(instr.tokens[start_index+1],
                                                size=2,
                                                bits_size=8,
                                                bits=(7, 0),
                                                relative=self.pc+2+offset,
                                                offset=2+offset)
            m, xn, s = _indexed_reg(instr.tokens[start_index+3])
            return index, 7, 3, pack_bits_be16u(0, ((15, 15), m), ((14, 12), xn), ((11, 11), s), ((7, 0), value))

        # (xxx).w
        found, index = instr.unbound_match(
            '(', ABSOLUTE, ')', '.W', start=start_index)
        if found:
            value = self.parse_integer_or_label(instr.tokens[start_index+1],
                                                size=2,
                                                bits_size=16,
                                                offset=2+offset)
            return index, 7, 0, pack_be16u(value)

        # (xxx).l
        found, index = instr.unbound_match(
            '(', ABSOLUTE, ')', '.L', start=start_index)
        if found:
            value = self.parse_integer_or_label(instr.tokens[start_index+1],
                                                size=4,
                                                bits_size=32,
                                                offset=2+offset)
            return index, 7, 1, pack_be32u(value)

        # #imm
        found, index = instr.unbound_match(IMMEDIATE, start=start_index)
        if found:
            value = self.parse_integer_or_label(instr.tokens[start_index][1:],
                                                size=size,
                                                bits_size=size*8,
                                                offset=2+offset)
            packers = {1: pack_byte, 2: pack_be16u, 4: pack_be32u}
            return index, 7, 4, packers[size](value)

    def _build_opcode(self, base, *args):
        return pack_bits_be16u(base, *args)

    @opcode('move', 'move.w', 'move.b', 'move.l')
    def _move(self, instr):
        op_size, s = _s_dark(instr.tokens[0])
        next_index, src_m, src_xn, src_data = self._mode(instr, 1, 0, op_size)
        _, dst_m, dst_xn, dst_data = self._mode(
            instr, next_index, len(src_data), op_size)
        return self._build_opcode(0b0000000000000000, ((13, 12), s), ((11, 9), dst_xn), ((8, 6), dst_m), ((5, 3), src_m), ((2, 0), src_xn)) + src_data + dst_data


def main():
    import sys
    asm = AssemblerMC68000()
    asm.assemble_file(sys.argv[1])
    asm.link()
    asm.save(sys.argv[2])


if __name__ == '__main__':
    main()
