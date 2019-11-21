
from necroassembler import Assembler, opcode
from necroassembler.utils import pack, pack_byte, known_args
from necroassembler.exceptions import AssemblerException


class InvalidMode(AssemblerException):
    message = 'invalid 6502 mode'


class AbsoluteAddressNotAllowed(AssemblerException):
    message = 'absolute address not allowed'


class UnsupportedModeForOpcode(AssemblerException):
    message = 'unsupported opcode mode'


def _check_immediate(token):
    return len(token) > 1 and token.startswith('#')


def _check_address(token):
    return token and not token.startswith('#')


IMMEDIATE = _check_immediate
ADDRESS = _check_address
REG_A = 'A'
REG_X = 'X'
REG_Y = 'Y'


def is_zero_page(address):
    return 0 <= address <= 0xff


_AVAILABLE_MODES = frozenset(('immediate', 'accumulator',
                              'absolute', 'absolute_x', 'absolute_y',
                              'zero_page', 'zero_page_x', 'zero_page_y',
                              'indirect', 'indirect_x', 'indirect_y'))


class AssemblerMOS6502(Assembler):

    hex_prefixes = ('$',)

    bin_prefixes = ('%',)

    oct_prefixes = ('@',)

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

    def _manage_branching(self, instr, code):
        arg = instr.tokens[1]
        address = self.parse_integer_or_label(
            label=arg, bits_size=8,
            size=1, offset=1, relative=self.pc + 2)
        return pack('<Bb', code, address)

    def _manage_address(self, absolute, zero_page, arg):

        address = self.parse_integer(arg, 16, signed=False)

        # numeric address ?
        if address is not None:
             # valid zero_page ?
            if zero_page is not None and is_zero_page(address):
                return pack_byte(zero_page, address)
            if absolute is None:
                raise AbsoluteAddressNotAllowed()
            return pack('<BH', absolute, address)

        # label management

        # check for already defined label (zero page optimization)
        address = self.get_label_absolute_address_by_name(arg)
        if address is None:
            if absolute is None:
                raise AbsoluteAddressNotAllowed()
            self.add_label_translation(
                label=arg, size=2, bits_size=16, offset=1)
            return pack('<BH', absolute, 0)

        if zero_page is not None and is_zero_page(address):
            return pack_byte(zero_page, address)

        # normal labeling (postpone to linking phase)
        if absolute is None:
            raise AbsoluteAddressNotAllowed()
        self.add_label_translation(label=arg, size=2, offset=1, bits_size=16)
        return pack('<BH', absolute, 0)

    def _manage_mode(self, instr, **kwargs):

        if not known_args(kwargs, _AVAILABLE_MODES):
            raise InvalidMode()

        try:
            if instr.match(REG_A):
                return pack_byte(kwargs['accumulator'])

            if instr.match(IMMEDIATE):
                return pack_byte(kwargs['immediate'],
                                 self.parse_integer_or_label(label=instr.args[0][1:],
                                                             bits_size=8,
                                                             offset=1,
                                                             size=1))

            if instr.match(ADDRESS):
                return self._manage_address(kwargs.get('absolute'), kwargs.get('zero_page'), instr.args[0])

            if instr.match(ADDRESS, REG_X):
                return self._manage_address(kwargs.get('absolute_x'), kwargs.get('zero_page_x'), instr.args[0])

            if instr.match(ADDRESS, REG_Y):
                return self._manage_address(kwargs.get('absolute_y'), kwargs.get('zero_page_y'), instr.args[0])

            if instr.match('(', ADDRESS, ')'):
                return self._manage_address(kwargs['indirect'], None, instr.args[1])

            if instr.match(['(', ADDRESS], [REG_X, ')']):
                return self._manage_address(None, kwargs['indirect_x'], instr.args[1])

            if instr.match(['(', ADDRESS], [')', REG_Y]):
                return self._manage_address(None, kwargs['indirect_y'], instr.args[1])

        except KeyError:
            raise UnsupportedModeForOpcode()

        raise InvalidMode()

    @opcode('ADC')
    def _adc(self, instr):
        return self._manage_mode(instr,
                                 immediate=0x69,
                                 zero_page=0x65,
                                 zero_page_x=0x75,
                                 absolute=0x6D,
                                 absolute_x=0x7D,
                                 absolute_y=0x79,
                                 indirect_x=0x61,
                                 indirect_y=0x71)

    @opcode('AND')
    def _and(self, instr):
        return self._manage_mode(instr,
                                 immediate=0x29,
                                 zero_page=0x25,
                                 zero_page_x=0x35,
                                 absolute=0x2D,
                                 absolute_x=0x3D,
                                 absolute_y=0x39,
                                 indirect_x=0x21,
                                 indirect_y=0x31)

    @opcode('ASL')
    def _asl(self, instr):
        return self._manage_mode(instr,
                                 accumulator=0x0A,
                                 zero_page=0x06,
                                 zero_page_x=0x16,
                                 absolute=0x0E,
                                 absolute_x=0x1E)

    @opcode('BPL')
    def _bpl(self, instr):
        return self._manage_branching(instr, 0x10)

    @opcode('BMI')
    def _bmi(self, instr):
        return self._manage_branching(instr, 0x30)

    @opcode('BVC')
    def _bvc(self, instr):
        return self._manage_branching(instr, 0x50)

    @opcode('BVS')
    def _bvs(self, instr):
        return self._manage_branching(instr, 0x70)

    @opcode('BCC')
    def _bcc(self, instr):
        return self._manage_branching(instr, 0x90)

    @opcode('BCS')
    def _bcs(self, instr):
        return self._manage_branching(instr, 0xB0)

    @opcode('BNE')
    def _bne(self, instr):
        return self._manage_branching(instr, 0xD0)

    @opcode('BEQ')
    def _beq(self, instr):
        return self._manage_branching(instr, 0xF0)

    @opcode('BIT')
    def _bit(self, instr):
        return self._manage_mode(instr,
                                 zero_page=0x24,
                                 absolute=0x2C)

    @opcode('CMP')
    def _cmp(self, instr):
        return self._manage_mode(instr,
                                 immediate=0xC9,
                                 zero_page=0xC5,
                                 zero_page_x=0xD5,
                                 absolute=0xCD,
                                 absolute_x=0xDD,
                                 absolute_y=0xD9,
                                 indirect_x=0xC1,
                                 indirect_y=0xD1)

    @opcode('CPX')
    def _cpx(self, instr):
        return self._manage_mode(instr,
                                 immediate=0xE0,
                                 zero_page=0xE4,
                                 absolute=0xEC)

    @opcode('CPY')
    def _cpy(self, instr):
        return self._manage_mode(instr,
                                 immediate=0xC0,
                                 zero_page=0xC4,
                                 absolute=0xCC)

    @opcode('DEC')
    def _dec(self, instr):
        return self._manage_mode(instr,
                                 zero_page=0xC6,
                                 zero_page_x=0xD6,
                                 absolute=0xCE,
                                 absolute_x=0xDE)

    @opcode('EOR')
    def _eor(self, instr):
        return self._manage_mode(instr,
                                 immediate=0x49,
                                 zero_page=0x45,
                                 zero_page_x=0x55,
                                 absolute=0x4D,
                                 absolute_x=0x5D,
                                 absolute_y=0x59,
                                 indirect_x=0x41,
                                 indirect_y=0x51)

    @opcode('INC')
    def _inc(self, instr):
        return self._manage_mode(instr,
                                 zero_page=0xE6,
                                 zero_page_x=0xF6,
                                 absolute=0xEE,
                                 absolute_x=0xFE)

    @opcode('JMP')
    def _jmp(self, instr):
        return self._manage_mode(instr,
                                 absolute=0x4C,
                                 indirect=0x6C)

    @opcode('JSR')
    def _jsr(self, instr):
        return self._manage_mode(instr,
                                 absolute=0x20)

    @opcode('LDA')
    def _lda(self, instr):
        return self._manage_mode(instr,
                                 immediate=0xA9,
                                 zero_page=0xA5,
                                 zero_page_x=0xB5,
                                 absolute=0xAD,
                                 absolute_x=0xBD,
                                 absolute_y=0xB9,
                                 indirect_x=0xA1,
                                 indirect_y=0xB1)

    @opcode('LDX')
    def _ldx(self, instr):
        return self._manage_mode(instr,
                                 immediate=0xA2,
                                 zero_page=0xA6,
                                 zero_page_y=0xB6,
                                 absolute=0xAE,
                                 absolute_y=0xBE)

    @opcode('LDY')
    def _ldy(self, instr):
        return self._manage_mode(instr,
                                 immediate=0xA0,
                                 zero_page=0xA4,
                                 zero_page_x=0xB4,
                                 absolute=0xAC,
                                 absolute_x=0xBC)

    @opcode('LSR')
    def _lsr(self, instr):
        return self._manage_mode(instr,
                                 accumulator=0x4A,
                                 zero_page=0x46,
                                 zero_page_x=0x56,
                                 absolute=0x4E,
                                 absolute_x=0x5E)

    @opcode('ORA')
    def _ora(self, instr):
        return self._manage_mode(instr,
                                 immediate=0x09,
                                 zero_page=0x05,
                                 zero_page_x=0x15,
                                 absolute=0x0D,
                                 absolute_x=0x1D,
                                 absolute_y=0x19,
                                 indirect_x=0x01,
                                 indirect_y=0x11)

    @opcode('ROL')
    def _rol(self, instr):
        return self._manage_mode(instr,
                                 accumulator=0x2A,
                                 zero_page=0x26,
                                 zero_page_x=0x36,
                                 absolute=0x2E,
                                 absolute_x=0x3E)

    @opcode('ROR')
    def _ror(self, instr):
        return self._manage_mode(instr,
                                 accumulator=0x6A,
                                 zero_page=0x66,
                                 zero_page_x=0x76,
                                 absolute=0x6E,
                                 absolute_x=0x7E)

    @opcode('SBC')
    def _sbc(self, instr):
        return self._manage_mode(instr,
                                 immediate=0xE9,
                                 zero_page=0xE5,
                                 zero_page_x=0xF5,
                                 absolute=0xED,
                                 absolute_x=0xFD,
                                 absolute_y=0xF9,
                                 indirect_x=0xE1,
                                 indirect_y=0xF1)

    @opcode('STA')
    def _sta(self, instr):
        return self._manage_mode(instr,
                                 zero_page=0x85,
                                 zero_page_x=0x95,
                                 absolute=0x8D,
                                 absolute_x=0x9D,
                                 absolute_y=0x99,
                                 indirect_x=0x81,
                                 indirect_y=0x91)

    @opcode('STX')
    def _stx(self, instr):
        return self._manage_mode(instr,
                                 zero_page=0x86,
                                 zero_page_y=0x96,
                                 absolute=0x8E)

    @opcode('STY')
    def _sty(self, instr):
        return self._manage_mode(instr,
                                 zero_page=0x84,
                                 zero_page_x=0x94,
                                 absolute=0x8C)


if __name__ == '__main__':
    AssemblerMOS6502.main()
