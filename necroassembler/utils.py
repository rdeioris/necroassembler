import struct


def pack_bytes(*args):
    return struct.pack('B' * len(args), *[n & 0xff if n is not None else 0 for n in args])


def pack_le_32s(*args):
    return struct.pack('<' + ('I' * len(args)), *[n & 0xffffffff if n is not None else 0 for n in args])


def pack_be_32s(*args):
    return struct.pack('>' + ('I' * len(args)), *args)


def pack_byte(b):
    return struct.pack('B', b & 0xFF)


def pack(fmt, *args):
    return struct.pack(fmt, *[n if n is not None else 0 for n in args])
