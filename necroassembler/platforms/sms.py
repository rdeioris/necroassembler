from necroassembler import directive, post_link
from necroassembler.cpu.z80 import AssemblerZ80
from necroassembler.exceptions import AssemblerException, InvalidArgumentsForDirective, LabelNotAllowed


class OnlyIndexedImagesAreSupported(AssemblerException):
    message = 'only indexed (palette based) images are supported'


class InvalidPaletteEntry(AssemblerException):
    message = 'only values between 0 and 15 are allowed for pixel colors'


class InvalidImageSize(AssemblerException):
    message = 'image width and height size must be a multiple of 8'


class AssemblerSegaMasterSystem(AssemblerZ80):

    defines = {
        'RAM': '$C000',
        'JOY1': '$DC',
        'JOY2': '$DD',
        'PSG': '$7F',
        'VDPDATA': '$BE',
        'VDPADDR': '$BF',
        'CMD_VRAM': '$40',
        'CMD_REG': '$80',
        'CMD_CRAM': '$C0',

    }

    @directive('tiles')
    def _build_tiles(self, instr):
        def _convert_cell(image, cell_x, cell_y):
            planes = []
            for y in range(0, 8):
                byte0 = 0
                byte1 = 0
                byte2 = 0
                byte3 = 0
                for x in range(0, 8):
                    pixel_x = cell_x * 8 + x
                    pixel_y = cell_y * 8 + y
                    pixel_value = image.getpixel((pixel_x, pixel_y))
                    if not 0 <= pixel_value <= 15:
                        raise InvalidPaletteEntry(instr)
                    byte0 |= (pixel_value & 0x1) << (7 - x)
                    byte1 |= ((pixel_value >> 1) & 0x1) << (7 - x)
                    byte2 |= ((pixel_value >> 2) & 0x1) << (7 - x)
                    byte3 |= ((pixel_value >> 3) & 0x1) << (7 - x)
                planes.append((byte0, byte1, byte2, byte3))
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


if __name__ == '__main__':
    AssemblerSegaMasterSystem.main()
