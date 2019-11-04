from necroassembler import directive
from necroassembler.cpu.mos6502 import AssemblerMOS6502
from necroassembler.exceptions import AssemblerException, InvalidArgumentsForDirective, LabelNotAllowed


class InvalidCartidgeHeaderOffset(AssemblerException):
    message = 'cartridge header can only be set at the start of the rom'


class CartidgeHeaderNotSet(AssemblerException):
    message = 'cartridge header not set'


class OnlyIndexedImagesAreSupported(AssemblerException):
    message = 'only indexed (palette based) images are supported'


class InvalidImageSize(AssemblerException):
    message = 'only 128x128 indexed images are supported'


class InvalidPaletteEntry(AssemblerException):
    message = 'only values between 0 and 3 are allowed for pixel colors'


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

    @directive('chr_pattern_table')
    def _build_chr_pattern_table(self, instr):
        def _convert_cell(image, cell_x, cell_y):
            plane0 = []
            plane1 = []
            for y in range(0, 8):
                byte0 = 0
                byte1 = 0
                for x in range(0, 8):
                    pixel_x = cell_x * 8 + x
                    pixel_y = cell_y * 8 + y
                    pixel_value = image.getpixel((pixel_x, pixel_y))
                    if not 0 <= pixel_value <= 3:
                        raise InvalidPaletteEntry(instr)
                    byte0 |= (pixel_value & 0x1) << (7 - x)
                    byte1 |= (pixel_value >> 1) << (7 - x)
                plane0.append(byte0)
                plane1.append(byte1)
            blob = b''
            for byte in plane0:
                blob += bytes((byte,))
            for byte in plane1:
                blob += bytes((byte,))
            return blob

        if len(instr.tokens) != 2:
            raise InvalidArgumentsForDirective(instr)
        filename = self.stringify(instr.tokens[1])
        from PIL import Image
        image = Image.open(filename)
        if image.mode != 'P':
            raise OnlyIndexedImagesAreSupported(instr)
        width, height = image.size
        if width != 128 or height != 128:
            raise InvalidImageSize(instr)
        for cell_y in range(0, 16):
            for cell_x in range(0, 16):
                blob = _convert_cell(image, cell_x, cell_y)
                self.append_assembled_bytes(blob)


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
