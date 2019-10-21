from necroassembler import Assembler, opcode
from necroassembler.utils import pack_bits, pack_le32u, pack_be32u
from necroassembler.exceptions import LabelNotAllowed, NotInBitRange

REGS_BASE = ('$0', '$1', '$2', '$3', '$4', '$5',
             '$6', '$7', '$8', '$9', '$10', '$11',
             '$12', '$13', '$14', '$15', '$16', '$17',
             '$18', '$19', '$20', '$21', '$22', '$23',
             '$24', '$25', '$26', '$27', '$28', '$29',
             '$30', '$31')

REGS_ALIAS = ('$zero', '$at', '$v0', '$v1', '$a0', '$a1',
              '$a2', '$a3', '$t0', '$t1', '$t2', '$t3',
              '$t4', '$t5', '$t6', '$t7', '$s0', '$s1',
              '$s2', '$s3', '$s4', '$s5', '$s6', '$s7',
              '$t8', '$t9', '$k0', '$k1', '$gp', '$sp',
              '$fp', '$ra')

REGS = REGS_BASE + REGS_ALIAS


def _is_immediate(token):
    return token and not token.startswith('$')


IMMEDIATE = _is_immediate


def _reg(reg):
    if reg.lower() in REGS_BASE:
        return int(reg[1:])
    index = REGS_ALIAS.index(reg.lower())
    return int(REGS_BASE[index][1:])


class AssemblerMIPS32(Assembler):

    hex_prefixes = ('0x',)
    bin_prefixes = ('0b',)

    big_endian = True

    def _immediate(self, token):
        return self.parse_integer_or_label(token, 16, signed=True, offset=0, bits=(15, 0), size=4)

    def _offset(self, token):
        value = self.parse_integer(token, 16, signed=True)
        if value is None:
            raise LabelNotAllowed()
        return value

    def _abs_label(self, token):
        return self.parse_integer_or_label(token, 32, signed=False,
                                           offset=0,
                                           bits=(25, 0),
                                           bits_check=32,
                                           post_filter=lambda x: (
                                               x & 0x0fffffff) >> 2,
                                           size=4) >> 2

    def _rel_label(self, token):
        return self.parse_integer_or_label(token, 16, signed=True,
                                           relative=True,
                                           offset=0,
                                           bits=(15, 0),
                                           bits_check=18,
                                           post_filter=lambda x: x >> 2,
                                           start=self.current_org + self.org_counter + 4,
                                           size=4) >> 2

    def _immediate32(self, high):
        def _high(token):
            return self.parse_integer_or_label(token, 32, signed=False,
                                               offset=0,
                                               bits=(15, 0),
                                               size=4,
                                               bits_check=32,
                                               post_filter=lambda x: x >> 16) >> 16

        def _low(token):
            return self.parse_integer_or_label(token, 32, signed=False,
                                               offset=0,
                                               bits=(15, 0),
                                               size=4,
                                               bits_check=32,
                                               post_filter=lambda x: x & 0xFFFF) & 0xFFFF
        if high:
            return _high
        return _low

    def _aaaaa(self, token):
        return self.parse_integer_or_label(token, 5, signed=False, offset=0, bits=(10, 6), size=4)

    def _build_opcode(self, base, *args):
        value = pack_bits(base, *args)
        if self.big_endian:
            return pack_be32u(value)
        return pack_le32u(value)

    def _arith_log(self, instr, func):
        if instr.match(REGS, REGS, REGS):
            rd, rs, rt = instr.apply(_reg, _reg, _reg)
            return self._build_opcode(0, ((25, 21), rs), ((20, 16), rt), ((15, 11), rd), ((5, 0), func))

    def _div_mult(self, instr, func):
        if instr.match(REGS, REGS):
            rs, rt = instr.apply(_reg, _reg)
        return self._build_opcode(0, ((25, 21), rs), ((20, 16), rt), ((5, 0), func))

    def _arith_log_i(self, instr, op, signed):
        if instr.match(REGS, REGS, IMMEDIATE):
            rt, rs, imm = instr.apply(_reg, _reg, self._immediate)
            return self._build_opcode(0, ((31, 26), op), ((25, 21), rs), ((20, 16), rt), ((15, 0), imm, signed))

    def _shift(self, instr, func):
        if instr.match(REGS, REGS, IMMEDIATE):
            rd, rt, shift = instr.apply(_reg, _reg, self._aaaaa)
            return self._build_opcode(0, ((20, 16), rt), ((15, 11), rd), ((10, 6), shift), ((5, 0), func))

    def _shift_v(self, instr, func):
        if instr.match(REGS, REGS, REGS):
            rd, rt, rs = instr.apply(_reg, _reg, _reg)
            return self._build_opcode(0, ((25, 21), rs), ((20, 16), rt), ((15, 11), rd), ((5, 0), func))

    def _load_i(self, instr, op, high):
        if instr.match(REGS, IMMEDIATE):
            rt, imm32 = instr.apply(_reg, self._immediate32(high))
            return self._build_opcode(0, ((31, 26), op), ((20, 16), rt), ((15, 0), imm32))

    def _branch(self, instr, op):
        if instr.match(REGS, REGS, IMMEDIATE):
            rs, rt, label = instr.apply(_reg, _reg, self._rel_label)
            return self._build_opcode(0, ((31, 26), op),  ((25, 21), rs), ((20, 16), rt), ((15, 0), label))

    def _branch_z(self, instr, op):
        if instr.match(REGS, IMMEDIATE):
            rs, label = instr.apply(_reg, self._rel_label)
            return self._build_opcode(0, ((31, 26), op),  ((25, 21), rs), ((15, 0), label))

    def _jump(self, instr, op):
        if instr.match(IMMEDIATE):
            label, = instr.apply(self._abs_label)
            return self._build_opcode(0, ((31, 26), op), ((25, 0), label))

    def _jump_r(self, instr, func):
        if instr.match(REGS):
            rs, = instr.apply(_reg)
            return self._build_opcode(0, ((25, 21), rs), ((5, 0), func))

    def _load_store(self, instr, op):
        if instr.match(REGS, IMMEDIATE, '(', REGS, ')'):
            rt, imm, rs = instr.apply(_reg, self._offset, None, _reg, None)
            return self._build_opcode(0, ((31, 26), op), ((25, 21), rs), ((20, 16), rt), ((15, 0), imm, True))

    def _move_from(self, instr, func):
        if instr.match(REGS):
            rd, = instr.apply(_reg)
            return self._build_opcode(0, ((15, 11), rd), ((5, 0), func))

    def _move_to(self, instr, func):
        if instr.match(REGS):
            rs, = instr.apply(_reg)
            return self._build_opcode(0, ((25, 21), rs), ((5, 0), func))

    def _no_args(self, instr, func):
        if len(instr.tokens) == 1:
            return self._build_opcode(0, (((5, 0)), func))

    @opcode('add')
    def _add(self, instr):
        return self._arith_log(instr, 0b100000)

    @opcode('addu')
    def _addu(self, instr):
        return self._arith_log(instr, 0b100001)

    @opcode('addi')
    def _addi(self, instr):
        return self._arith_log_i(instr, 0b001000, True)

    @opcode('addiu')
    def _addiu(self, instr):
        return self._arith_log_i(instr, 0b001001, False)

    @opcode('and')
    def _and(self, instr):
        return self._arith_log(instr, 0b100100)

    @opcode('andi')
    def _andi(self, instr):
        return self._arith_log_i(instr, 0b001100, True)

    @opcode('div')
    def _div(self, instr):
        return self._div_mult(0b011010, instr)

    @opcode('divu')
    def _divu(self, instr):
        return self._div_mult(0b011011, instr)

    @opcode('mult')
    def _mult(self, instr):
        return self._div_mult(0b011000, instr)

    @opcode('multu')
    def _multu(self, instr):
        return self._div_mult(0b011001, instr)

    @opcode('nor')
    def _nor(self, instr):
        return self._arith_log(0b100111, instr)

    @opcode('or')
    def _or(self, instr):
        return self._arith_log(0b100101, instr)

    @opcode('ori')
    def _ori(self, instr):
        return self._arith_log_i(instr, 0b001101, True)

    @opcode('sll')
    def _sll(self, instr):
        return self._shift(instr, 0b000000)

    @opcode('sllv')
    def _sllv(self, instr):
        return self._shift_v(instr, 0b000100)

    @opcode('sra')
    def _sra(self, instr):
        return self._shift(instr, 0b000011)

    @opcode('srav')
    def _srav(self, instr):
        return self._shift_v(instr, 0b000111)

    @opcode('srl')
    def _srl(self, instr):
        return self._shift(instr, 0b000010)

    @opcode('srlv')
    def _srlv(self, instr):
        return self._shift_v(instr, 0b000110)

    @opcode('sub')
    def _sub(self, instr):
        return self._arith_log(0b100010, instr)

    @opcode('subu')
    def _subu(self, instr):
        return self._arith_log(0b100011, instr)

    @opcode('xor')
    def _xor(self, instr):
        return self._arith_log(0b100110, instr)

    @opcode('xori')
    def _xori(self, instr):
        return self._arith_log_i(instr, 0b001110, True)

    @opcode('lui')
    def _lui(self, instr):
        return self._load_i(instr, 0b001111, True)

    @opcode('lhi')
    def _lhi(self, instr):
        return self._load_i(instr, 0b011001, True)

    @opcode('llo')
    def _llo(self, instr):
        return self._load_i(instr, 0b011000, False)

    @opcode('slt')
    def _slt(self, instr):
        return self._arith_log(instr, 0b101010)

    @opcode('sltu')
    def _sltu(self, instr):
        return self._arith_log(instr, 0b101001)

    @opcode('slti')
    def _slti(self, instr):
        return self._arith_log_i(instr, 0b001010, True)

    @opcode('sltiu')
    def _sltiu(self, instr):
        return self._arith_log_i(instr, 0b001001, False)

    @opcode('beq')
    def _beq(self, instr):
        return self._branch(instr, 0b000100)

    @opcode('bgtz')
    def _bgtz(self, instr):
        return self._branch_z(instr, 0b000111)

    @opcode('blez')
    def _blez(self, instr):
        return self._branch_z(instr, 0b000110)

    @opcode('bne')
    def _bne(self, instr):
        return self._branch(instr, 0b000101)

    @opcode('j')
    def _j(self, instr):
        return self._jump(instr, 0b000010)

    @opcode('jal')
    def _jal(self, instr):
        return self._jump(instr, 0b000011)

    @opcode('jalr')
    def _jalr(self, instr):
        return self._jump_r(instr, 0b001001)

    @opcode('jr')
    def _jr(self, instr):
        return self._jump_r(instr, 0b001000)

    @opcode('lb')
    def _lb(self, instr):
        return self._load_store(instr, 0b100000)

    @opcode('lbu')
    def _lbu(self, instr):
        return self._load_store(instr, 0b100100)

    @opcode('lh')
    def _lh(self, instr):
        return self._load_store(instr, 0b100001)

    @opcode('lhu')
    def _lhu(self, instr):
        return self._load_store(instr, 0b100101)

    @opcode('lw')
    def _lw(self, instr):
        return self._load_store(instr, 0b100011)

    @opcode('sb')
    def _sb(self, instr):
        return self._load_store(instr, 0b101000)

    @opcode('sh')
    def _sh(self, instr):
        return self._load_store(instr, 0b101001)

    @opcode('sw')
    def _sw(self, instr):
        return self._load_store(instr, 0b101011)

    @opcode('mfhi')
    def _mfhi(self, instr):
        return self._move_from(instr, 0b010000)

    @opcode('mflo')
    def _mflo(self, instr):
        return self._move_from(instr, 0b010010)

    @opcode('mthi')
    def _mthi(self, instr):
        return self._move_to(instr, 0b010001)

    @opcode('mtlo')
    def _mtlo(self, instr):
        return self._move_to(instr, 0b010011)

    @opcode('trap')
    def _trap(self, instr):
        return self._jump(instr, 0b011010)

    @opcode('break')
    def _break(self, instr):
        return self._no_args(instr, 0b001101)

    @opcode('syscall')
    def _syscall(self, instr):
        return self._no_args(instr, 0b001100)


def main():
    import sys
    asm = AssemblerMIPS32()
    asm.assemble_file(sys.argv[1])
    asm.link()
    asm.save(sys.argv[2])


if __name__ == '__main__':
    main()
