import struct


def pack_bytes(*args):
    return struct.pack('B' * len(args), *[n & 0xff if n is not None else 0 for n in args])


def pack_le_32s(*args):
    return struct.pack('<' + ('I' * len(args)),
                       *[n & 0xffffffff if n is not None else 0 for n in args])


def pack_be_32s(*args):
    return struct.pack('>' + ('I' * len(args)), *args)


def pack_byte(byte):
    return struct.pack('B', byte & 0xFF)


def pack(fmt, *args):
    return struct.pack(fmt, *[n if n is not None else 0 for n in args])


def substitute_with_dict(tokens, _dict, start=0):
    for i in range(start, len(tokens)):
        name = tokens[i]
        if name in _dict:
            tokens[i] = _dict[name]
