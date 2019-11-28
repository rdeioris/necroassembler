
from necroassembler.exceptions import InvalidArgumentsForDirective
from necroassembler.utils import pack_bits, pack_byte, pack_be16u, pack_le16u, pack_be32u, pack_le32u
import wave
import audioop


def directive_incwav(instr):
    if len(instr.args) < 1:
        raise InvalidArgumentsForDirective(instr)

    _format = None
    channels = 0
    frequency = 0
    bits = 0

    for arg in instr.args[0][1:]:
        key, *value = arg.split('=', 1)
        if key == 'format':
            _format = value[0]
        elif key == 'channels':
            channels = int(value[0])
        elif key == 'bits':
            bits = int(value[0])
        elif key == 'frequency':
            frequency = int(value[0])

    filename = instr.assembler.stringify_path([instr.args[0][0]]).decode(
        instr.assembler.get_filesystem_encoding())
    wave_read = wave.open(filename, 'rb')
    wave_data = wave_read.readframes(wave_read.getnframes())
    if _format is None:
        blob = wave_data
    elif _format.lower() == 'adpcm':
        blob, _ = audioop.lin2adpcm(wave_data, 2, None)
    instr.assembler.append_assembled_bytes(blob)
