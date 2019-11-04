from necroassembler import directive, post_link
from necroassembler.cpu.lr35902 import AssemblerLR35902
from necroassembler.exceptions import AssemblerException, InvalidArgumentsForDirective, LabelNotAllowed


class InvalidCartidgeHeaderOffset(AssemblerException):
    message = 'cartridge header can only be set at rom offset $100'


class CartidgeHeaderNotSet(AssemblerException):
    message = 'cartridge header not set'


class OnlyIndexedImagesAreSupported(AssemblerException):
    message = 'only indexed (palette based) images are supported'


class InvalidPaletteEntry(AssemblerException):
    message = 'only values between 0 and 3 are allowed for pixel colors'


class InvalidImageSize(AssemblerException):
    message = 'image width and height size must be a multiple of 8'


class AssemblerGameboy(AssemblerLR35902):

    cartridge_set = False

    defines = {
        'VRAM': '$8000',
        'LCDC': '$FF40',
        'STAT': '$FF41',
        'SCY': '$FF42',
        'SCX': '$FF43',
        'LY': '$FF44',
        'LYC': '$FF45',
        'WY': '$FF4A',
        'WX': '$FF4B',
        'TMAP0': '$9800',
        'TMAP1': '$9C00',
        'WRAM': '$C000',
        'WRAM0': '$C000',
        'WRAM1': '$D000',
        'HRAM': '$FF80',
    }

    @directive('cartridge')
    def _generate_cartridge_header(self, instr):
        if len(self.assembled_bytes) != 256:
            raise InvalidCartidgeHeaderOffset(instr)

        self.change_org(0x100, self.current_org_end)
        nop_jp_150 = b'\x00\xC3\x50\x01'
        nintendo_logo = bytes((
            0xCE, 0xED, 0x66, 0x66, 0xCC, 0x0D, 0x00, 0x0B,
            0x03, 0x73, 0x00, 0x83, 0x00, 0x0C, 0x00, 0x0D,
            0x00, 0x08, 0x11, 0x1F, 0x88, 0x89, 0x00, 0x0E,
            0xDC, 0xCC, 0x6E, 0xE6, 0xDD, 0xDD, 0xD9, 0x99,
            0xBB, 0xBB, 0x67, 0x63, 0x6E, 0x0E, 0xEC, 0xCC,
            0xDD, 0xDC, 0x99, 0x9F, 0xBB, 0xB9, 0x33, 0x3E))
        self.append_assembled_bytes(nop_jp_150 +
                                    nintendo_logo +
                                    # title
                                    bytes(16) +
                                    # license
                                    bytes(2) +
                                    # sgb + cartridge type
                                    bytes(2) +
                                    # ROM size + RAM size
                                    bytes(2) +
                                    # destination code
                                    b'\x01' +
                                    # old license
                                    b'\x33' +
                                    # version
                                    bytes(1) +
                                    # checksums
                                    bytes(3))
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

    @directive('cartridge_title')
    def _set_cartridge_title(self, instr):
        self._cartridge_fill(instr, 0x134, 16)

    @directive('cartridge_license')
    def _set_cartridge_license(self, instr):
        self._cartridge_fill(instr, 0x144, 2)

    @directive('cartridge_cgb')
    def _set_cartridge_cgb(self, instr):
        self._cartridge_fill(instr, 0x143, 1)

    @directive('cartridge_sgb')
    def _set_cartridge_sgb(self, instr):
        self._cartridge_fill(instr, 0x146, 1)

    @directive('cartridge_type')
    def _set_cartridge_type(self, instr):
        self._cartridge_fill(instr, 0x147, 1)

    @directive('cartridge_destination')
    def _set_cartridge_destination(self, instr):
        self._cartridge_fill(instr, 0x14A, 1)

    @directive('tiles')
    def _build_tiles(self, instr):
        def _convert_cell(image, cell_x, cell_y):
            planes = []
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
                planes.append((byte0, byte1))
            blob = b''
            for plane in planes:
                blob += bytes(plane)
            return blob

        if len(instr.tokens) != 2:
            raise InvalidArgumentsForDirective(instr)
        filename = self.stringify(instr.tokens[1])
        from PIL import Image
        image = Image.open(filename)
        if image.mode != 'P':
            raise OnlyIndexedImagesAreSupported(instr)
        width, height = image.size
        if (width % 8) != 0 or (height % 8) != 0:
            raise InvalidImageSize(instr)
        for cell_y in range(0, height // 8):
            for cell_x in range(0, width // 8):
                blob = _convert_cell(image, cell_x, cell_y)
                self.append_assembled_bytes(blob)

    @post_link
    def _fix(self):
        # header checksum
        header_checksum = 0
        for i in range(0x134, 0x14d):
            header_checksum = header_checksum - \
                int(self.assembled_bytes[i]) - 1
        self.assembled_bytes[0x14d] = header_checksum & 0xFF

        # global checksum
        global_checksum = 0
        for byte in self.assembled_bytes:
            global_checksum += int(byte)

        self.assembled_bytes[0x14e] = (global_checksum >> 8) & 0xFF
        self.assembled_bytes[0x14f] = global_checksum & 0xFF


if __name__ == '__main__':
    AssemblerGameboy.main()
