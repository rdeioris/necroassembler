import struct


def pack_bytes(*args):
    return struct.pack('B' * len(args), *[n & 0xff if n is not None else 0 for n in args])


def pack_le_u32s(*args):
    return struct.pack('<' + ('I' * len(args)),
                       *[n & 0xffffffff if n is not None else 0 for n in args])


def pack_be_u32s(*args):
    return struct.pack('>' + ('I' * len(args)), *args)


def pack_byte(byte):
    return struct.pack('B', byte & 0xFF)


def pack_le_u32(value):
    return struct.pack('<I', value & 0xFFFFFFFF)


def pack_be_u32(value):
    return struct.pack('>I', value & 0xFFFFFFFF)


def pack_le_u16(value):
    return struct.pack('<H', value & 0xFFFF)


def pack_be_u16(value):
    return struct.pack('>H', value & 0xFFFF)


def pack(fmt, *args):
    return struct.pack(fmt, *[n if n is not None else 0 for n in args])


def in_bit_range(value, number_of_bits):
    max_value = int('1' * number_of_bits, 2)
    return value & max_value == value


def in_bit_range_signed(value, number_of_bits):
    if value < 0:
        max_value = int('1' * number_of_bits, 2)
        value += max_value // 2
    else:
        max_value = int('1' * (number_of_bits-1), 2)
    return value & max_value == value


def substitute_with_dict(tokens, _dict, start, prefixes=(), suffixes=()):
    for i in range(start, len(tokens)):
        name = tokens[i]
        if name in _dict:
            tokens[i] = _dict[name]
        for prefix in prefixes:
            if name.startswith(prefix):
                new_name = name[len(prefix):]
                if new_name in _dict:
                    tokens[i] = prefix + _dict[new_name]
