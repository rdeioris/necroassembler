
from necroassembler.exceptions import InvalidArgumentsForDirective
from necroassembler.utils import pack_bits, pack_byte, pack_be16u, pack_le16u, pack_be32u, pack_le32u


def directive_incimg(instr):
    if len(instr.args) < 1:
        raise InvalidArgumentsForDirective(instr)

    mode = None
    palette = 0
    colors = 256
    bits = 0
    bits_r = 0
    bits_g = 0
    bits_b = 0
    bits_base = 0

    for arg in instr.args[0][1:]:
        key, *value = arg.split('=', 1)
        if key == 'mode':
            mode = value[0]
        elif key == 'palette':
            palette = int(value[0])
        elif key == 'bits':
            bits = int(value[0])
        elif key == 'bits_base':
            bits_base = int(value[0])
        elif key == 'bits_r':
            bits_r = tuple(map(int, value[0].split('_', 1)))
        elif key == 'bits_g':
            bits_g = tuple(map(int, value[0].split('_', 1)))
        elif key == 'bits_b':
            bits_b = tuple(map(int, value[0].split('_', 1)))

    pack_map = {
        8: pack_byte,
        16: pack_be16u if instr.assembler.big_endian else pack_le16u,
        32: pack_be32u if instr.assembler.big_endian else pack_le32u
    }

    filename = instr.assembler.stringify_path([instr.args[0][0]])

    from PIL import Image
    image = Image.open(filename)
    if mode is None:
        mode = image.mode
    if palette > 0:
        mode = 'P'
        colors = palette
        palette = Image.ADAPTIVE
    if image.mode != mode:
        image = image.convert(mode, palette=palette, colors=colors)

    if palette == 0:
        blob = b''
        for r, g, b in image.getdata():
            if bits > 0:
                r = int(((1 << (bits_r[0] - bits_r[1] + 1)) - 1) * (r/255))
                g = int(((1 << (bits_g[0] - bits_g[1] + 1)) - 1) * (g/255))
                b = int(((1 << (bits_b[0] - bits_b[1] + 1)) - 1) * (b/255))
                blob += pack_map[bits](pack_bits(bits_base, (bits_r, r),
                                                 (bits_g, g), (bits_b, b)))
            else:
                blob += bytes((r, g, b))
        instr.assembler.append_assembled_bytes(blob)
