import struct
from necroassembler.exceptions import NotInBitRange, InvalidBitRange


def neg_fix(value, bits):
    negative = 1 << (bits - 1)
    if value & negative:
        return -(1 << (bits)) + value
    return value


def pos_fix(value, bits):
    """
    if value < 0:
    negative = 1 << (bits - 1)
    if value & negative:
        return -(1 << (bits)) + value
    return value
    """


def pack_byte(*args):
    return struct.pack('B' * len(args), *[n & 0xff if n is not None else 0 for n in args])


def pack_8s(*args):
    return struct.pack('b' * len(args), *[neg_fix(n & 0xff, 8) if n is not None else 0 for n in args])


def pack_le32s(*args):
    return struct.pack('<' + ('i' * len(args)),
                       *[neg_fix(n & 0xffffffff, 16) if n is not None else 0 for n in args])


def pack_le32u(*args):
    return struct.pack('<' + ('I' * len(args)),
                       *[n & 0xffffffff if n is not None else 0 for n in args])


def pack_be32u(*args):
    return struct.pack('>' + ('I' * len(args)),
                       *[n & 0xffffffff if n is not None else 0 for n in args])


def pack_be32s(*args):
    return struct.pack('>' + ('i' * len(args)),
                       *[neg_fix(n & 0xffffffff, 32) if n is not None else 0 for n in args])


def pack_le16s(*args):
    return struct.pack('<' + ('h' * len(args)),
                       *[neg_fix(n & 0xffff, 32) if n is not None else 0 for n in args])


def pack_le16u(*args):
    return struct.pack('<' + ('H' * len(args)),
                       *[n & 0xffff if n is not None else 0 for n in args])


def pack_be16u(*args):
    return struct.pack('>' + ('H' * len(args)),
                       *[n & 0xffff if n is not None else 0 for n in args])


def pack(fmt, *args):
    return struct.pack(fmt, *[n if n is not None else 0 for n in args])


def pack_bits(base, *args, check_bits=True):
    for arg in args:
        (end, start), value, *options = arg
        if end < start:
            raise InvalidBitRange()
        if check_bits:
            total_bits = end - start + 1
            signed = False
            if options:
                signed = options[0]
            if signed:
                if not in_bit_range_signed(value, total_bits):
                    raise InvalidBitRange()
            else:
                # fix negative numbers
                if value < 0:
                    value &= (pow(2, total_bits) - 1)
                if not in_bit_range(value, total_bits):
                    raise InvalidBitRange()

        base |= (value << start) & (pow(2, end + 1) - 1)
    return base


def pack_bit(base, *args, check_bits=True):
    new_args = [((x, x), y) for x, y in args]
    return pack_bits(base, *new_args, check_bits=check_bits)


def pack_bits_le32u(base, *args):
    return pack_le32u(pack_bits(base, *args))


def pack_bits_le16u(base, *args):
    return pack_le16u(pack_bits(base, *args))


def pack_bits_be16u(base, *args):
    return pack_be16u(pack_bits(base, *args))


def in_bit_range(value, number_of_bits):
    max_value = int('1' * number_of_bits, 2)
    return value & max_value == value


def in_bit_range_signed(value, number_of_bits):
    return True
    if value < 0:
        max_value = int('1' * number_of_bits, 2)
        value += max_value // 2
    else:
        max_value = int('1' * (number_of_bits-1), 2)
    return value & max_value == value


def known_args(args, known):
    return all([key in known for key in args.keys()])


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
