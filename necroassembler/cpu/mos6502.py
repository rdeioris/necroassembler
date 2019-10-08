
from necroassembler import Assembler, opcode
from necroassembler.utils import pack, pack_bytes


class InvalidMode(Exception):
    def __init__(self, tokens):
        super().__init__('invalid 6502 mode for {0}'.format(tokens[0]))


class AssemblerMOS6502(Assembler):

    hex_prefixes = ('$',)

    bin_prefixes = ('%',)

    oct_prefixes = ('@',)

    def register_instructions(self):
        self.register_instruction('BPL', b'\x10')
        self.register_instruction('BMI', b'\x30')
        self.register_instruction('BVC', b'\x50')
        self.register_instruction('BVS', b'\x70')
        self.register_instruction('BCC', b'\x90')
        self.register_instruction('BCS', b'\xB0')
        self.register_instruction('BNE', b'\xD0')
        self.register_instruction('BEQ', b'\xF0')

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

    def manage_address(self, abs, zp, arg):

        address = self.parse_integer(arg)

        # numeric address ?
        if address is not None:
             # valid zero_page ?
            if zp is not None and self.is_zero_page(address):
                return pack_bytes(zp, address)
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
            return pack_bytes(zp, address)

        # normal labeling (postpone to linking phase)
        if abs is None:
            raise Exception('absolute address mode not allowed')
        self.add_label_translation(label=arg, size=2)
        return pack('<BH', abs, 0)

    def manage_single_arg_mode(self, opcodes, arg):
        # immediate ?
        if (arg.startswith('#')):
            value = self.parse_integer(arg[1:])
            # label ?
            if value is None:
                self.add_label_translation(label=arg[1:], size=1)
            return pack_bytes(opcodes['imm'], value)

        # use get for 'zp' to support non-zp opcodes
        return self.manage_address(opcodes['abs'], opcodes.get('zp'), arg)

    def manage_two_args_mode(self, opcodes, arg1, arg2):
        if arg1.startswith('#') or arg2.startswith('#'):
            return None
        # zero_page_x absolute_x
        if arg2.upper() == 'X':
            return self.manage_address(opcodes['abs_x'], opcodes['zp_x'], arg1)
        if arg2.upper() == 'Y':
            return self.manage_address(opcodes['abs_y'], None, arg1)

    def manage_three_args_mode(self, opcodes, *args):
        if any(map(lambda x: x.startswith('#'), args)) or args[0] != '(':
            return None
        # indirect_x
        if args[2].upper() == 'X':
            return self.manage_address(None, opcodes['ind_x'], args[1])
        if args[2] == ')' and args[3].upper() == 'Y':
            return self.manage_address(None, opcodes['ind_y'], args[1])

    def manage_indirect_mode(self, opcodes, *args):
        if args[0] != '(' or args[2] != ')':
            return None
        return self.manage_address(opcodes['ind'], None, args[1])

    def manage_mode(self, tokens, opcodes={}, **kwargs):
        combined_opcodes = opcodes.copy()
        combined_opcodes.update(kwargs)
        try:
            if len(tokens) < 2:
                return None
            if len(tokens) == 2:
                return self.manage_single_arg_mode(combined_opcodes, tokens[1])
            if len(tokens) == 3:
                return self.manage_two_args_mode(combined_opcodes, tokens[1], tokens[2])
            if len(tokens) == 4:
                return self.manage_indirect_mode(combined_opcodes, *tokens[1:])
            if len(tokens) == 5:
                return self.manage_three_args_mode(combined_opcodes, *tokens[1:])
        except KeyError:
            raise InvalidMode(tokens)

    @opcode('ADC')
    def _adc(self, tokens):
        return self.manage_mode(tokens, imm=0x69, zp=0x65, zp_x=0x75, abs=0x6D, abs_x=0x7D, abs_y=0x79, ind_x=0x61, ind_y=0x71)

    @opcode('AND')
    def _and(self, tokens):
        return self.manage_mode(tokens, imm=0x29, zp=0x25, zp_x=0x35, abs=0x2D, abs_x=0x3D, abs_y=0x39, ind_x=0x21, ind_y=0x31)

    @opcode('ASL')
    def _asl(self, tokens):
        if len(tokens) == 2 and tokens[1].upper() == 'A':
            return b'\x0A'
        return self.manage_mode(tokens, zp=0x06, zp_x=0x16, abs=0x0E, abs_x=0x1E)

    @opcode('BIT')
    def _bit(self, tokens):
        return self.manage_mode(tokens, zp=0x24, abs=0x2C)

    @opcode('CMP')
    def _cmp(self, tokens):
        return self.manage_mode(tokens, imm=0xC9, zp=0xC5, zp_x=0xD5, abs=0xCD, abs_x=0xDD, abs_y=0xD9, ind_x=0xC1, ind_y=0xD1)

    @opcode('CPX')
    def _cpx(self, tokens):
        return self.manage_mode(tokens, imm=0xE0, zp=0xE4, abs=0xEC)

    @opcode('CPY')
    def _cpy(self, tokens):
        return self.manage_mode(tokens, imm=0xC0, zp=0xC4, abs=0xCC)

    @opcode('DEC')
    def _dec(self, tokens):
        return self.manage_mode(tokens, zp=0xC6, zp_x=0xD6, abs=0xCE, abs_x=0xDE)

    @opcode('EOR')
    def _eor(self, tokens):
        return self.manage_mode(tokens, imm=0x49, zp=0x45, zp_x=0x55, abs=0x4D, abs_x=0x5D, abs_y=0x59, ind_x=0x41, ind_y=0x51)

    @opcode('INC')
    def _inc(self, tokens):
        return self.manage_mode(tokens, zp=0xE6, zp_x=0xF6, abs=0xEE, abs_x=0xFE)

    @opcode('JMP')
    def _jmp(self, tokens):
        return self.manage_mode(tokens, abs=0x4C, ind=0x6C)

    @opcode('JSR')
    def _jsr(self, tokens):
        return self.manage_mode(tokens, abs=0x20)

    @opcode('LDA')
    def _lda(self, tokens):
        return self.manage_mode(tokens, imm=0xA9, zp=0xA5, zp_x=0xB5, abs=0xAD, abs_x=0xBD, abs_y=0xB9, ind_x=0xA1, ind_y=0xB1)

    @opcode('LDX')
    def _ldx(self, tokens):
        return self.manage_mode(tokens, imm=0xA2, zp=0xA6, zp_y=0xB6, abs=0xAE, abs_y=0xBE)

    @opcode('LDY')
    def _ldy(self, tokens):
        return self.manage_mode(tokens, imm=0xA0, zp=0xA4, zp_x=0xB4, abs=0xAC, abs_x=0xBC)

    @opcode('LSR')
    def _lsr(self, tokens):
        if len(tokens) == 2 and tokens[1].upper() == 'A':
            return b'\x4A'
        return self.manage_mode(tokens, zp=0x46, zp_x=0x56, abs=0x4E, abs_x=0x5E)

    @opcode('ORA')
    def _ora(self, tokens):
        return self.manage_mode(tokens, imm=0x09, zp=0x05, zp_x=0x15, abs=0x0D, abs_x=0x1D, abs_y=0x19, ind_x=0x01, ind_y=0x11)

    @opcode('ROL')
    def _rol(self, tokens):
        if len(tokens) == 2 and tokens[1].upper() == 'A':
            return b'\x2A'
        return self.manage_mode(tokens, zp=0x26, zp_x=0x36, abs=0x2E, abs_x=0x3E)

    @opcode('ROR')
    def _ror(self, tokens):
        if len(tokens) == 2 and tokens[1].upper() == 'A':
            return b'\x6A'
        return self.manage_mode(tokens, zp=0x66, zp_x=0x76, abs=0x6E, abs_x=0x7E)

    @opcode('SBC')
    def _sbc(self, tokens):
        return self.manage_mode(tokens, imm=0xE9, zp=0xE5, zp_x=0xF5, abs=0xED, abs_x=0xFD, abs_y=0xF9, ind_x=0xE1, ind_y=0xF1)

    @opcode('STA')
    def _sta(self, tokens):
        return self.manage_mode(tokens, zp=0x85, zp_x=0x95, abs=0x8D, abs_x=0x9D, abs_y=0x99, ind_x=0x81, ind_y=0x91)

    @opcode('STX')
    def _stx(self, tokens):
        return self.manage_mode(tokens, zp=0x86, zp_y=0x96, abs=0x8E)

    @opcode('STY')
    def _sty(self, tokens):
        return self.manage_mode(tokens, zp=0x84, zp_x=0x94, abs=0x8C)


def main():
    import sys
    asm = AssemblerMOS6502()
    with open(sys.argv[1]) as f:
        asm.assemble(f.read())
    asm.link()
    with open(sys.argv[2], 'wb') as f:
        f.write(asm.assembled_bytes)


if __name__ == '__main__':
    main()
