
from necroassembler import Assembler, opcode
from necroassembler.utils import pack, pack_le16u, pack_byte


class InvalidMode(Exception):
    def __init__(self, instr):
        super().__init__('invalid 6502 mode for {0}'.format(instr))


class AbsoluteAddressNotAllowed(Exception):
    def __init__(self, instr):
        super().__init__(
            'absolute address not allowed for {0}'.format(instr))


class UnsupportedModeForOpcode(Exception):
    def __init__(self, instr):
        super().__init__(
            'unsupported upcode mode {0}'.format(instr))


def IMMEDIATE(x): return len(x) > 1 and x.startswith('#')


def ADDRESS(x): return x and not x.startswith('#')


REG_A = 'A'
REG_X = 'X'
REG_Y = 'Y'


class AssemblerMOS6502(Assembler):

    hex_prefixes = ('$',)

    bin_prefixes = ('%',)

    oct_prefixes = ('@',)

    special_prefixes = ('#',)

    def register_instructions(self):

        self.register_instruction('BRK', b'\x00')

        self.register_instruction('CLC', b'\x18')
        self.register_instruction('SEC', b'\x38')
        self.register_instruction('CLI', b'\x58')
        self.register_instruction('SEI', b'\x78')
        self.register_instruction('CLV', b'\xb8')
        self.register_instruction('CLD', b'\xd8')
        self.register_instruction('SED', b'\xf8')

        self.register_instruction('NOP', b'\xEA')

        self.register_instruction('TAX', b'\xAA')
        self.register_instruction('TXA', b'\x8A')
        self.register_instruction('DEX', b'\xCA')
        self.register_instruction('INX', b'\xE8')
        self.register_instruction('TAY', b'\xA8')
        self.register_instruction('TYA', b'\x98')
        self.register_instruction('DEY', b'\x88')
        self.register_instruction('INY', b'\xC8')

        self.register_instruction('RTI', b'\x40')

        self.register_instruction('RTS', b'\x60')

        self.register_instruction('TXS', b'\x9A')
        self.register_instruction('TSX', b'\xBA')
        self.register_instruction('PHA', b'\x48')
        self.register_instruction('PLA', b'\x68')
        self.register_instruction('PHP', b'\x08')
        self.register_instruction('PLP', b'\x28')

    def is_zero_page(self, address):
        return address >= 0 and address <= 0xff

    def manage_branching(self, instr, opcode):
        arg = instr.tokens[1]
        address = self.parse_integer_or_label(
            arg, size=1, relative=True, start=self.current_org + self.org_counter + 2)
        return pack('<Bb', opcode, address)

    def _manage_address(self, abs, zp, arg):

        address = self.parse_integer(arg)

        # numeric address ?
        if address is not None:
             # valid zero_page ?
            if zp is not None and self.is_zero_page(address):
                return pack_byte(zp, address)
            if abs is None:
                raise Exception('absolute address mode not allowed')
            return pack('<BH', abs, address)

        # label management

        # check for already defined label (zero page optimization)
        address = self.get_label_absolute_address_by_name(arg)
        if address is None:
            if abs is None:
                raise Exception('absolute address mode not allowed')
            self.add_label_translation(label=arg, size=2)
            return pack('<BH', abs, 0)

        if zp is not None and self.is_zero_page(address):
            return pack_byte(zp, address)

        # normal labeling (postpone to linking phase)
        if abs is None:
            raise Exception('absolute address mode not allowed')
        self.add_label_translation(label=arg, size=2)
        return pack('<BH', abs, 0)

    def manage_mode(self, instr, **kwargs):
        try:
            if instr.match(REG_A):
                return pack_byte(kwargs['a'])
            if instr.match(IMMEDIATE):
                return pack_byte(kwargs['imm'], self.parse_integer_or_label(instr.tokens[1][1:], size=1))
            if instr.match(ADDRESS):
                return self._manage_address(kwargs.get('abs'), kwargs.get('zp'), instr.tokens[1])
            if instr.match(ADDRESS, REG_X):
                return self._manage_address(kwargs.get('abs_x'), kwargs.get('zp_x'), instr.tokens[1])
            if instr.match(ADDRESS, REG_Y):
                return self._manage_address(kwargs.get('abs_y'), kwargs.get('zp_y'), instr.tokens[1])
            if instr.match('(', ADDRESS, REG_X, ')'):
                return self._manage_address(None, kwargs['ind_x'], instr.tokens[2])
            if instr.match('(', ADDRESS, ')', REG_Y):
                return self._manage_address(None, kwargs['ind_y'], instr.tokens[2])
        except:
            raise UnsupportedModeForOpcode(instr)

        raise InvalidMode(instr)

    @opcode('ADC')
    def _adc(self, instr):
        return self.manage_mode(instr, imm=0x69, zp=0x65, zp_x=0x75, abs=0x6D, abs_x=0x7D, abs_y=0x79, ind_x=0x61, ind_y=0x71)

    @opcode('AND')
    def _and(self, instr):
        return self.manage_mode(instr, imm=0x29, zp=0x25, zp_x=0x35, abs=0x2D, abs_x=0x3D, abs_y=0x39, ind_x=0x21, ind_y=0x31)

    @opcode('ASL')
    def _asl(self, instr):
        return self.manage_mode(instr, a=0x0A, zp=0x06, zp_x=0x16, abs=0x0E, abs_x=0x1E)

    @opcode('BPL')
    def _bpl(self, instr):
        return self.manage_branching(instr, 0x10)

    @opcode('BMI')
    def _bmi(self, instr):
        return self.manage_branching(instr, 0x30)

    @opcode('BVC')
    def _bvc(self, instr):
        return self.manage_branching(instr, 0x50)

    @opcode('BVS')
    def _bvs(self, instr):
        return self.manage_branching(instr, 0x70)

    @opcode('BCC')
    def _bcc(self, instr):
        return self.manage_branching(instr, 0x90)

    @opcode('BCS')
    def _bcs(self, instr):
        return self.manage_branching(instr, 0xB0)

    @opcode('BNE')
    def _bne(self, instr):
        return self.manage_branching(instr, 0xD0)

    @opcode('BEQ')
    def _beq(self, instr):
        return self.manage_branching(instr, 0xF0)

    @opcode('BIT')
    def _bit(self, instr):
        return self.manage_mode(instr, zp=0x24, abs=0x2C)

    @opcode('CMP')
    def _cmp(self, instr):
        return self.manage_mode(instr, imm=0xC9, zp=0xC5, zp_x=0xD5, abs=0xCD, abs_x=0xDD, abs_y=0xD9, ind_x=0xC1, ind_y=0xD1)

    @opcode('CPX')
    def _cpx(self, instr):
        return self.manage_mode(instr, imm=0xE0, zp=0xE4, abs=0xEC)

    @opcode('CPY')
    def _cpy(self, instr):
        return self.manage_mode(instr, imm=0xC0, zp=0xC4, abs=0xCC)

    @opcode('DEC')
    def _dec(self, instr):
        return self.manage_mode(instr, zp=0xC6, zp_x=0xD6, abs=0xCE, abs_x=0xDE)

    @opcode('EOR')
    def _eor(self, instr):
        return self.manage_mode(instr, imm=0x49, zp=0x45, zp_x=0x55, abs=0x4D, abs_x=0x5D, abs_y=0x59, ind_x=0x41, ind_y=0x51)

    @opcode('INC')
    def _inc(self, instr):
        return self.manage_mode(instr, zp=0xE6, zp_x=0xF6, abs=0xEE, abs_x=0xFE)

    @opcode('JMP')
    def _jmp(self, instr):
        return self.manage_mode(instr, abs=0x4C, ind=0x6C)

    @opcode('JSR')
    def _jsr(self, instr):
        return self.manage_mode(instr, abs=0x20)

    @opcode('LDA')
    def _lda(self, instr):
        return self.manage_mode(instr, imm=0xA9, zp=0xA5, zp_x=0xB5, abs=0xAD, abs_x=0xBD, abs_y=0xB9, ind_x=0xA1, ind_y=0xB1)

    @opcode('LDX')
    def _ldx(self, instr):
        return self.manage_mode(instr, imm=0xA2, zp=0xA6, zp_y=0xB6, abs=0xAE, abs_y=0xBE)

    @opcode('LDY')
    def _ldy(self, instr):
        return self.manage_mode(instr, imm=0xA0, zp=0xA4, zp_x=0xB4, abs=0xAC, abs_x=0xBC)

    @opcode('LSR')
    def _lsr(self, instr):
        return self.manage_mode(instr, a=0x4A, zp=0x46, zp_x=0x56, abs=0x4E, abs_x=0x5E)

    @opcode('ORA')
    def _ora(self, instr):
        return self.manage_mode(instr, imm=0x09, zp=0x05, zp_x=0x15, abs=0x0D, abs_x=0x1D, abs_y=0x19, ind_x=0x01, ind_y=0x11)

    @opcode('ROL')
    def _rol(self, instr):
        return self.manage_mode(instr, a=0x2A, zp=0x26, zp_x=0x36, abs=0x2E, abs_x=0x3E)

    @opcode('ROR')
    def _ror(self, instr):
        return self.manage_mode(instr, a=0x6A, zp=0x66, zp_x=0x76, abs=0x6E, abs_x=0x7E)

    @opcode('SBC')
    def _sbc(self, instr):
        return self.manage_mode(instr, imm=0xE9, zp=0xE5, zp_x=0xF5, abs=0xED, abs_x=0xFD, abs_y=0xF9, ind_x=0xE1, ind_y=0xF1)

    @opcode('STA')
    def _sta(self, instr):
        return self.manage_mode(instr, zp=0x85, zp_x=0x95, abs=0x8D, abs_x=0x9D, abs_y=0x99, ind_x=0x81, ind_y=0x91)

    @opcode('STX')
    def _stx(self, instr):
        return self.manage_mode(instr, zp=0x86, zp_y=0x96, abs=0x8E)

    @opcode('STY')
    def _sty(self, instr):
        return self.manage_mode(instr, zp=0x84, zp_x=0x94, abs=0x8C)


def main():
    import sys
    asm = AssemblerMOS6502()
    asm.assemble_file(sys.argv[1])
    asm.link()
    asm.save(sys.argv[2])


if __name__ == '__main__':
    main()
