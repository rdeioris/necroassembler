from necroassembler import Assembler, opcode
from necroassembler.utils import pack_bytes
from necroassembler.exceptions import UnkownRegister, InvalidRegister, InvalideImmediateValue


class AssemblerThumb(Assembler):

    hex_prefixes = ('0x',)

    bin_prefixes = ('0b', '0y')

    low_regs = ('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7')
    high_regs = ('r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15')
    high_regs_aliases = ('fp', 'ip', 'sp', 'lr', 'pc')

    def _low_reg(self, instr, reg):
        if reg.lower() in self.low_regs:
            return int(reg[1:])

        if reg.lower() in self.high_regs + self.high_regs_aliases:
            raise InvalidRegister(instr)

        raise UnkownRegister(instr)

    def _offset(self, instr, arg, bits):
        return self.parse_integer_or_label(arg, bits=bits,
                                           relative=True,
                                           start=self.current_org + self.org_counter + 4)

    def _imm(self, instr, arg, bits):
        if not arg.startswith('#'):
            raise InvalideImmediateValue(instr)
        return self._offset(instr, arg[1:], bits)

    @opcode('MOV')
    def _mov(self, instr):
        reg, imm = instr.tokens[1:]
        return pack_bytes(0b00100 | self._low_reg(instr, reg), self._imm(instr, imm, 8))

    @opcode('ADD')
    def _add(self, instr):
        reg_d, reg_s, op = instr.tokens[1:]
        imm = 0
        if op.startswith('#'):
            op = self._imm(instr, op, 3) & 0x07
            imm = 1 << 2
        else:
            op = self._low_reg(instr, op)
        return pack_bytes(0b0001100 | imm | op >> 2, op << 6 | self._low_reg(instr, reg_s) << 3 | self._low_reg(instr, reg_d))

    @opcode('B')
    def _b(self, instr):
        offset = self._offset(instr, instr.tokens[1], 11)
        return pack_bytes(0b11100 | offset, offset)
