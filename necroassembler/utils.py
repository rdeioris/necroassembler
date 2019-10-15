import struct
from necroassembler.exceptions import NotInBitRange


def pack_byte(*args):
    return struct.pack('B' * len(args), *[n & 0xff if n is not None else 0 for n in args])


def pack_le32s(*args):
    return struct.pack('<' + ('i' * len(args)),
                       *[n & 0xffffffff if n is not None else 0 for n in args])


def pack_le32u(*args):
    return struct.pack('<' + ('I' * len(args)),
                       *[n & 0xffffffff if n is not None else 0 for n in args])


def pack_le16s(*args):
    return struct.pack('<' + ('h' * len(args)),
                       *[n & 0xffff if n is not None else 0 for n in args])


def pack_le16u(*args):
    return struct.pack('<' + ('H' * len(args)),
                       *[n & 0xffff if n is not None else 0 for n in args])


def pack(fmt, *args):
    return struct.pack(fmt, *[n if n is not None else 0 for n in args])


def pack_bits(base, *args):
    for arg in args:
        (end, start), value, *signed = arg
        if end < start:
            raise Exception('invalid range')
        total_bits = end - start + 1
        if signed:
            if not in_bit_range_signed(value, total_bits):
                raise Exception('not in bit range')
        else:
            if not in_bit_range(value, total_bits):
                raise Exception('not in bit range')
        base |= (value << start) & (pow(2, end + 1) - 1)
    return base


def pack_bits_le32u(base, *args):
    return pack_le32u(pack_bits(base, *args))


def pack_bits_le16u(base, *args):
    return pack_le16u(pack_bits(base, *args))


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
