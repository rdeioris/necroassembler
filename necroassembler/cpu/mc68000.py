
from necroassembler import Assembler, opcode
from necroassembler.utils import pack_bits_be16u, pack_be16u, pack_be32u
from necroassembler.exceptions import AssemblerException


class InvalidMode(AssemblerException):
    message = 'invalid 68000 mode'


D_REGS = ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7')
A_REGS = ('a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7')

CONDITIONS = ('T', 'F', 'HI', 'LS', 'CC', 'CS', 'NE', 'EQ',
              'VC', 'VS', 'PL', 'MI', 'GE', 'LT', 'GT', 'LE')


def _is_immediate(token):
    return len(token) > 1 and token.startswith('#')


def _is_displacement(token):
    return token.lower() not in D_REGS + A_REGS + ('(', ')') and not token.startswith('#')


def _is_absolute_with_w(token):
    return _is_displacement(token) and token.lower().endswith('.w')


def _is_absolute_with_l(token):
    return _is_displacement(token) and token.lower().endswith('.l')


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
ABSOLUTE_W = _is_absolute_with_w
ABSOLUTE_L = _is_absolute_with_l

MODES = ('Dn', 'An', '(An)', '(An)+', '-(An)', '(d16,An)', '(d8,An,Xn)',
         '(xxx).W', '(xxx).L', '#<data>', '(d16,PC)', '(d8,PC,Xn)')


def _reg(token):
    return int(token[1:])


def _cond(token):
    if token[0:2].upper() == 'RA':
        return 1
    return CONDITIONS.index(token[0:2].upper())


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

    big_endian = True

    def register_instructions(self):
        self.register_instruction('RTS', b'\x4E\x75')
        self.register_instruction('NOP', b'\x4E\x71')

    def _mode(self, instr, start_index, offset, size, blacklist=()):
        # first check the blacklist
        for black_item in blacklist:
            if black_item not in MODES:
                raise InvalidMode(instr)

        # Dn
        found, index = instr.unbound_match(D_REGS, start=start_index)
        if found and 'Dn' not in blacklist:
            return index, 0, _reg(instr.tokens[start_index]), b''

        # An
        found, index = instr.unbound_match(A_REGS, start=start_index)
        if found and 'An' not in blacklist:
            return index, 1, _reg(instr.tokens[start_index]), b''

        # (An)+ must be checked before (An) !
        found, index = instr.unbound_match(
            '(', A_REGS, ')', '+', start=start_index)
        if found and '(An)+' not in blacklist:
            return index, 3, _reg(instr.tokens[start_index+1]), b''

        # (An)
        found, index = instr.unbound_match('(', A_REGS, ')', start=start_index)
        if found and '(An)' not in blacklist:
            return index, 2, _reg(instr.tokens[start_index+1]), b''

        # -(An)
        found, index = instr.unbound_match(
            '-', '(', A_REGS, ')', start=start_index)
        if found and '-(An)' not in blacklist:
            return index, 4, _reg(instr.tokens[start_index+2]), b''

        # (d16, An)
        found, index = instr.unbound_match(
            '(', DISPLACEMENT, A_REGS, ')', start=start_index)
        if found and '(d16,An)' not in blacklist:
            value = self.parse_integer_or_label(instr.tokens[start_index+1],
                                                size=2,
                                                bits_size=16,
                                                signed=True,
                                                offset=2+offset)
            return index, 5, _reg(instr.tokens[start_index+2]), pack_be16u(value)

        # (d8, An, Xn)
        found, index = instr.unbound_match(
            '(', DISPLACEMENT, A_REGS, INDEXED_REG, ')', start=start_index)
        if found and '(d8,An,Xn)' not in blacklist:
            value = self.parse_integer_or_label(instr.tokens[start_index+1],
                                                size=2,
                                                bits_size=8,
                                                bits=(7, 0),
                                                signed=True,
                                                offset=2+offset)
            m, xn, s = _indexed_reg(instr.tokens[start_index+3])
            return index, 6, _reg(instr.tokens[start_index+2]), pack_bits_be16u(0, ((15, 15), m), ((14, 12), xn), ((11, 11), s), ((7, 0), value))

        # (d16, PC)
        found, index = instr.unbound_match(
            '(', DISPLACEMENT, 'PC', ')', start=start_index)
        if found and '(d16,PC)' not in blacklist:
            value = self.parse_integer_or_label(instr.tokens[start_index+1],
                                                size=2,
                                                bits_size=16,
                                                relative=self.pc+2+offset,
                                                offset=2+offset)
            return index, 7, 2, pack_be16u(value)

        # (d8, PC, Xn)
        found, index = instr.unbound_match(
            '(', DISPLACEMENT, 'PC', INDEXED_REG, ')', start=start_index)
        if found and '(d8,PC,Xn)' not in blacklist:
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
        if found and '(xxx).W' not in blacklist:
            value = self.parse_integer_or_label(instr.tokens[start_index+1],
                                                size=2,
                                                bits_size=16,
                                                offset=2+offset)
            return index, 7, 0, pack_be16u(value)

        # (xxx).l
        found, index = instr.unbound_match(
            '(', ABSOLUTE, ')', '.L', start=start_index)
        if found and '(xxx).L' not in blacklist:
            value = self.parse_integer_or_label(instr.tokens[start_index+1],
                                                size=4,
                                                bits_size=32,
                                                offset=2+offset)
            return index, 7, 1, pack_be32u(value)

        # #imm
        found, index = instr.unbound_match(IMMEDIATE, start=start_index)
        if found and '#<data>' not in blacklist:
            packed = self._packer(instr.tokens[start_index][1:], size, offset)
            return index, 7, 4, packed

        # (xxx).w ALIAS addr.w
        found, index = instr.unbound_match(ABSOLUTE_W, start=start_index)
        if found and '(xxx).W' not in blacklist:
            value = self.parse_integer_or_label(instr.tokens[start_index][:-2],
                                                size=2,
                                                bits_size=16,
                                                offset=2+offset)
            return index, 7, 0, pack_be16u(value)

        # (xxx).l ALIAS addr.l
        found, index = instr.unbound_match(ABSOLUTE_L, start=start_index)
        if found and '(xxx).L' not in blacklist:
            value = self.parse_integer_or_label(instr.tokens[start_index][:-2],
                                                size=4,
                                                bits_size=32,
                                                offset=2+offset)
            return index, 7, 1, pack_be32u(value)

        # (xxx).l ALIAS [2] addr (better to use 32bit when not specified)
        found, index = instr.unbound_match(ABSOLUTE, start=start_index)
        if found and '(xxx).L' not in blacklist:
            value = self.parse_integer_or_label(instr.tokens[start_index],
                                                size=4,
                                                bits_size=32,
                                                offset=2+offset)
            return index, 7, 1, pack_be32u(value)

        raise InvalidMode(instr)

    def _build_opcode(self, base, *args):
        return pack_bits_be16u(base, *args)

    def _packer(self, token, op_size, offset):
        value = self.parse_integer_or_label(
            token, size=op_size + (op_size % 2), bits_size=op_size*8, offset=2+offset)
        packers = {1: pack_be16u, 2: pack_be16u, 4: pack_be32u}
        return packers[op_size](value)

    @opcode('move', 'move.w', 'move.b', 'move.l')
    def _move(self, instr):
        op_size, s = _s_dark(instr.tokens[0])
        next_index, src_m, src_xn, src_data = self._mode(instr, 1, 0, op_size)
        # convert to MOVEA
        if op_size in (2, 4) and instr.match(A_REGS, start=next_index):
            return self._build_opcode(0b0000000001000000, ((13, 12), s), ((11, 9), _reg(instr.tokens[next_index])), ((5, 3), src_m), ((2, 0), src_xn)) + src_data
        _, dst_m, dst_xn, dst_data = self._mode(
            instr, next_index, len(src_data), op_size, blacklist=('An', '#<data>', '(d16,PC)', '(d8,PC,Xn)'))
        return self._build_opcode(0b0000000000000000, ((13, 12), s), ((11, 9), dst_xn), ((8, 6), dst_m), ((5, 3), src_m), ((2, 0), src_xn)) + src_data + dst_data

    @opcode('movea', 'movea.w', 'movea.l')
    def _movea(self, instr):
        op_size, s = _s_dark(instr.tokens[0])
        next_index, src_m, src_xn, src_data = self._mode(instr, 1, 0, op_size)
        if instr.match(A_REGS, start=next_index):
            return self._build_opcode(0b0000000001000000, ((13, 12), s), ((11, 9), _reg(instr.tokens[next_index])), ((5, 3), src_m), ((2, 0), src_xn)) + src_data

    @opcode('ori', 'ori.w', 'ori.b', 'ori.l')
    def _ori(self, instr):
        if instr.match(IMMEDIATE, 'CCR'):
            packed = self._packer(instr.tokens[1][1:], 1, 0)
            return self._build_opcode(0b0000000000111100) + packed
        if instr.match(IMMEDIATE, 'SR'):
            packed = self._packer(instr.tokens[1][1:], 2, 0)
            return self._build_opcode(0b0000000001111100) + packed
        found, index = instr.unbound_match(IMMEDIATE)
        if found:
            op_size, s = _s_light(instr.tokens[0])
            packed = self._packer(instr.tokens[1][1:], op_size, 0)
            _, dst_m, dst_xn, dst_data = self._mode(
                instr, index, op_size + (op_size % 2), op_size, blacklist=('An', '#<data>', '(d16,PC)', '(d8,PC,Xn)'))
            return self._build_opcode(0b0000000000000000, ((7, 6), s), ((5, 3), dst_m), ((2, 0), dst_xn)) + packed + dst_data

    @opcode('andi', 'andi.w', 'andi.b', 'andi.l')
    def _andi(self, instr):
        if instr.match(IMMEDIATE, 'CCR'):
            packed = self._packer(instr.tokens[1][1:], 1, 0)
            return self._build_opcode(0b0000001000111100) + packed
        if instr.match(IMMEDIATE, 'SR'):
            packed = self._packer(instr.tokens[1][1:], 2, 0)
            return self._build_opcode(0b0000001001111100) + packed
        found, index = instr.unbound_match(IMMEDIATE)
        if found:
            op_size, s = _s_light(instr.tokens[0])
            packed = self._packer(instr.tokens[1][1:], op_size, 0)
            _, dst_m, dst_xn, dst_data = self._mode(
                instr, index, op_size + (op_size % 2), op_size, blacklist=('An', '#<data>', '(d16,PC)', '(d8,PC,Xn)'))
            return self._build_opcode(0b0000001000000000, ((7, 6), s), ((5, 3), dst_m), ((2, 0), dst_xn)) + packed + dst_data

    @opcode('subi', 'subi.w', 'subi.b', 'subi.l')
    def _subi(self, instr):
        found, index = instr.unbound_match(IMMEDIATE)
        if found:
            op_size, s = _s_light(instr.tokens[0])
            packed = self._packer(instr.tokens[1][1:], op_size, 0)
            _, dst_m, dst_xn, dst_data = self._mode(
                instr, index, op_size + (op_size % 2), op_size, blacklist=('An', '#<data>', '(d16,PC)', '(d8,PC,Xn)'))
            return self._build_opcode(0b0000010000000000, ((7, 6), s), ((5, 3), dst_m), ((2, 0), dst_xn)) + packed + dst_data

    @opcode('addi', 'addi.w', 'addi.b', 'addi.l')
    def _addi(self, instr):
        found, index = instr.unbound_match(IMMEDIATE)
        if found:
            op_size, s = _s_light(instr.tokens[0])
            packed = self._packer(instr.tokens[1][1:], op_size, 0)
            _, dst_m, dst_xn, dst_data = self._mode(
                instr, index, op_size + (op_size % 2), op_size, blacklist=('An', '#<data>', '(d16,PC)', '(d8,PC,Xn)'))
            return self._build_opcode(0b0000011000000000, ((7, 6), s), ((5, 3), dst_m), ((2, 0), dst_xn)) + packed + dst_data

    @opcode('eori', 'eori.w', 'eori.b', 'eori.l')
    def _eori(self, instr):
        if instr.match(IMMEDIATE, 'CCR'):
            packed = self._packer(instr.tokens[1][1:], 1, 0)
            return self._build_opcode(0b0000101000111100) + packed
        if instr.match(IMMEDIATE, 'SR'):
            packed = self._packer(instr.tokens[1][1:], 2, 0)
            return self._build_opcode(0b0000101001111100) + packed
        found, index = instr.unbound_match(IMMEDIATE)
        if found:
            op_size, s = _s_light(instr.tokens[0])
            packed = self._packer(instr.tokens[1][1:], op_size, 0)
            _, dst_m, dst_xn, dst_data = self._mode(
                instr, index, op_size + (op_size % 2), op_size, blacklist=('An', '#<data>', '(d16,PC)', '(d8,PC,Xn)'))
            return self._build_opcode(0b0000101000000000, ((7, 6), s), ((5, 3), dst_m), ((2, 0), dst_xn)) + packed + dst_data

    @opcode('cmpi', 'cmpi.w', 'cmpi.b', 'cmpi.l')
    def _cmpi(self, instr):
        found, index = instr.unbound_match(IMMEDIATE)
        if found:
            op_size, s = _s_light(instr.tokens[0])
            packed = self._packer(instr.tokens[1][1:], op_size, 0)
            _, dst_m, dst_xn, dst_data = self._mode(
                instr, index, op_size + (op_size % 2), op_size, blacklist=('An', '#<data>', '(d16,PC)', '(d8,PC,Xn)'))
            return self._build_opcode(0b0000110000000000, ((7, 6), s), ((5, 3), dst_m), ((2, 0), dst_xn)) + packed + dst_data

    @opcode('jmp')
    def _jmp(self, instr):
        _, src_m, src_xn, src_data = self._mode(
            instr, 1, 0, 0, blacklist=('Dn', 'An', '(An)+', '-(An)', '#<data>'))
        return self._build_opcode(0b0100111011000000, ((5, 3), src_m), ((2, 0), src_xn)) + src_data

    @opcode('lea', 'lea.l')
    def _lea(self, instr):
        next_index, src_m, src_xn, src_data = self._mode(
            instr, 1, 0, 4, blacklist=('Dn', 'An', '(An)+', '-(An)', '#<data>'))
        if instr.match(A_REGS, start=next_index):
            return self._build_opcode(0b0100000111000000, ((11, 9), _reg(instr.tokens[next_index])), ((5, 3), src_m), ((2, 0), src_xn)) + src_data

    @opcode('bhi', 'bls', 'bcc', 'bcs', 'bne', 'beq', 'bvc', 'bvs', 'bpl', 'bmi', 'bge', 'blt', 'bgt', 'ble',
            'bhi.b', 'bls.b', 'bcc.b', 'bcs.b', 'bne.b', 'beq.b', 'bvc.b', 'bvs.b', 'bpl.b', 'bmi.b', 'bge.b', 'blt.b', 'bgt.b', 'ble.b',
            'bhi.w', 'bls.w', 'bcc.w', 'bcs.w', 'bne.w', 'beq.w', 'bvc.w', 'bvs.w', 'bpl.w', 'bmi.w', 'bge.w', 'blt.w', 'bgt.w', 'ble.w'
            )
    def _bcc(self, instr):
        if instr.match(DISPLACEMENT):
            condition = _cond(instr.tokens[0][1:])
            op_size, _ = _s_dark(instr.tokens[0])
            if op_size == 1:
                value = self.parse_integer_or_label(instr.tokens[1],
                                                    size=2,
                                                    bits_size=8,
                                                    bits=(7, 0),
                                                    alignment=2,  # here is safe to check for alignment
                                                    relative=self.pc+2)
                return self._build_opcode(0b0110000000000000, ((11, 8), condition), ((7, 0), value))
            elif op_size == 2:
                value = self.parse_integer_or_label(instr.tokens[1],
                                                    size=2,
                                                    bits_size=16,
                                                    alignment=2,  # here is safe to check for alignment
                                                    offset=2,
                                                    relative=self.pc+2)
                return self._build_opcode(0b0110000000000000, ((11, 8), condition)) + pack_be16u(value)

    @opcode('dbt', 'dbf', 'dbra', 'dbhi', 'dbls', 'dbcc', 'dbcs', 'dbne', 'dbeq', 'dbvc', 'dbvs', 'dbpl', 'dbmi', 'dbge', 'dblt', 'dbgt', 'dble',
            'dbt.w', 'dbf.w', 'dbra.w', 'dbhi.w', 'dbls.w', 'dbcc.w', 'dbcs.w', 'dbne.w', 'dbeq.w', 'dbvc.w', 'dbvs.w', 'dbpl.w', 'dbmi.w', 'dbge.w', 'dblt.w', 'dbgt.w', 'dble.w'
            )
    def _dbcc(self, instr):
        if instr.match(D_REGS, DISPLACEMENT):
            condition = _cond(instr.tokens[0][2:])
            d_reg = _reg(instr.tokens[1])
            value = self.parse_integer_or_label(instr.tokens[2],
                                                size=2,
                                                bits_size=16,
                                                alignment=2,  # here is safe to check for alignment
                                                offset=2,
                                                relative=self.pc+2)
            return self._build_opcode(0b0101000011001000, ((11, 8), condition), ((2, 0), d_reg)) + pack_be16u(value)

    @opcode('jsr')
    def _jsr(self, instr):
        _, src_m, src_xn, src_data = self._mode(
            instr, 1, 0, 0, blacklist=('Dn', 'An', '(An)+', '-(An)', '#<data>'))
        return self._build_opcode(0b0100111010000000, ((5, 3), src_m), ((2, 0), src_xn)) + src_data


def main():
    import sys
    asm = AssemblerMC68000()
    asm.assemble_file(sys.argv[1])
    asm.link()
    asm.save(sys.argv[2])


if __name__ == '__main__':
    main()
