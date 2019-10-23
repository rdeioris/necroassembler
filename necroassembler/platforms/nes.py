from necroassembler import directive
from necroassembler.cpu.mos6502 import AssemblerMOS6502
from necroassembler.exceptions import AssemblerException, InvalidArgumentsForDirective, LabelNotAllowed


class InvalidCartidgeHeaderOffset(AssemblerException):
    message = 'cartridge header can only be set at the start of the rom'


class CartidgeHeaderNotSet(AssemblerException):
    message = 'cartridge header not set'


class AssemblerNES(AssemblerMOS6502):

    cartridge_set = False

    defines = {
        'PPUCTRL': '$2000',
        'PPUMASK': '$2001',
        'PPUSTATUS': '$2002',
        'OAMADDR': '$2003',
        'OAMDATA': '$2004',
        'PPUSCROLL': '$2005',
        'PPUADDR': '$2006',
        'PPUDATA': '$2007',
        'OAMDMA': '$4014'
    }

    @directive('cartridge')
    def _generate_cartridge_header(self, instr):
        if len(self.assembled_bytes) != 0:
            raise InvalidCartidgeHeaderOffset(instr)

        self.append_assembled_bytes('NES'.encode('ascii') +
                                    b'\x1A' +
                                    # PRG_ROMS
                                    b'\x02' +
                                    # CHR ROMS
                                    b'\x00' +
                                    bytes(10))
        self.cartridge_set = True

    def _cartridge_fill(self, instr, address, size):
        if not self.cartridge_set:
            raise CartidgeHeaderNotSet(instr)
        if len(instr.tokens) < 2:
            raise InvalidArgumentsForDirective(instr)
        try:
            blob = self.parse_bytes_or_ascii(instr.tokens[1:])
        except LabelNotAllowed:
            raise InvalidArgumentsForDirective(instr) from None
        if len(blob) > size:
            raise InvalidArgumentsForDirective(instr)
        for index, byte in enumerate(blob):
            self.assembled_bytes[address + index] = byte

    @directive('cartridge_prg_roms')
    def _set_cartridge_title(self, instr):
        self._cartridge_fill(instr, 0x05, 1)

    @directive('cartridge_chr_roms')
    def _set_cartridge_license(self, instr):
        self._cartridge_fill(instr, 0x06, 1)


def main():
    import sys
    asm = AssemblerNES()
    asm.assemble_file(sys.argv[1])
    asm.link()
    asm.save(sys.argv[2])

    # rom debug symbols
    with open(sys.argv[2] + '.0.nl', 'wb') as nl_file:
        for label in asm.labels:
            address = asm.get_label_absolute_address_by_name(label)
            if 0x8000 <= address <= 0xFFFF:
                nl_file.write('${0:04X}#{1}#\x0D\x0A'.format(
                    address, label).encode('ascii'))

    # ram debug symbols
    with open(sys.argv[2] + '.ram.nl', 'wb') as nl_file:
        for label in asm.labels:
            address = asm.get_label_absolute_address_by_name(label)
            if 0x0000 <= address <= 0x7FF:
                nl_file.write('${0:04X}#{1}#\x0D\x0A'.format(
                    address, label).encode('ascii'))


if __name__ == '__main__':
    main()
