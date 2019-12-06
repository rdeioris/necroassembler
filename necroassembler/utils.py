import string
import struct
from necroassembler.exceptions import NotInBitRange, InvalidBitRange, NotInSignedBitRange


def neg_fix(value, bits):
    negative = 1 << (bits - 1)
    if value & negative:
        return -(1 << (bits)) + value
    return value


def pack_byte(*args):
    return struct.pack('B' * len(args), *[n & 0xff if n is not None else 0 for n in args])


def pack_8s(*args):
    return struct.pack('b' * len(args), *[neg_fix(n & 0xff, 8) if n is not None else 0 for n in args])


def pack_le32s(*args):
    return struct.pack('<' + ('i' * len(args)),
                       *[neg_fix(n & 0xffffffff, 32) if n is not None else 0 for n in args])


def pack_le32u(*args):
    return struct.pack('<' + ('I' * len(args)),
                       *[n & 0xffffffff if n is not None else 0 for n in args])


def pack_le32f(*args):
    return struct.pack('<' + ('f' * len(args)),
                       *[n if n is not None else 0 for n in args])


def pack_be32f(*args):
    return struct.pack('>' + ('f' * len(args)),
                       *[n if n is not None else 0 for n in args])


def pack_le64f(*args):
    return struct.pack('<' + ('d' * len(args)),
                       *[n if n is not None else 0 for n in args])


def pack_be64f(*args):
    return struct.pack('>' + ('d' * len(args)),
                       *[n if n is not None else 0 for n in args])


def pack_le64u(*args):
    return struct.pack('<' + ('Q' * len(args)),
                       *[n & 0xffffffffffffffff if n is not None else 0 for n in args])


def pack_le64s(*args):
    return struct.pack('<' + ('q' * len(args)),
                       *[neg_fix(n & 0xffffffffffffffff, 64) if n is not None else 0 for n in args])


def pack_be32u(*args):
    return struct.pack('>' + ('I' * len(args)),
                       *[n & 0xffffffff if n is not None else 0 for n in args])


def pack_be32s(*args):
    return struct.pack('>' + ('i' * len(args)),
                       *[neg_fix(n & 0xffffffff, 32) if n is not None else 0 for n in args])


def pack_le16s(*args):
    return struct.pack('<' + ('h' * len(args)),
                       *[neg_fix(n & 0xffff, 16) if n is not None else 0 for n in args])


def pack_le16u(*args):
    return struct.pack('<' + ('H' * len(args)),
                       *[n & 0xffff if n is not None else 0 for n in args])


def pack_be16u(*args):
    return struct.pack('>' + ('H' * len(args)),
                       *[n & 0xffff if n is not None else 0 for n in args])


def pack_be16s(*args):
    return struct.pack('>' + ('h' * len(args)),
                       *[neg_fix(n & 0xffff, 16) if n is not None else 0 for n in args])


def pack(fmt, *args):
    return struct.pack(fmt, *[n if n is not None else 0 for n in args])


def pack_bits(base, *args):
    for arg in args:
        (end, start), value = arg
        if end < start:
            raise InvalidBitRange()

        total_bits = end - start + 1
        # fix negative numbers
        if value < 0:
            max_value = pow(2, total_bits)
            value += max_value
            if value < max_value // 2:
                raise InvalidBitRange()
        if not in_bit_range(value, total_bits):
            raise InvalidBitRange()
        base |= (value << start) & (pow(2, end + 1) - 1)

    return base


def pack_bit(base, *args):
    new_args = [((x, x), y) for x, y in args]
    return pack_bits(base, *new_args)


def pack_bits_le32u(base, *args):
    return pack_le32u(pack_bits(base, *args))


def pack_bits_le16u(base, *args):
    return pack_le16u(pack_bits(base, *args))


def pack_bits_be16u(base, *args):
    return pack_be16u(pack_bits(base, *args))


def in_bit_range(value, number_of_bits):
    max_value = (1 << number_of_bits) - 1
    return (value & max_value) == value


def two_s_complement(value, number_of_bits):
    if not in_bit_range(value, number_of_bits):
        raise NotInSignedBitRange(value, number_of_bits)
    # negative number ?
    if value & (1 << (number_of_bits-1)) != 0:
        value -= 1 << number_of_bits
    return value


def to_two_s_complement(value, number_of_bits):
    min_value = -(1 << number_of_bits-1)
    max_value = (1 << (number_of_bits-1)) - 1

    if value < min_value or value > max_value:
        raise NotInSignedBitRange(value, number_of_bits)

    if value < 0:
        value &= (max_value << 1) + 1

    return value


def known_args(args, known):
    return all([key in known for key in args.keys()])


def is_valid_label(name):
    valid_chars = string.ascii_letters + string.digits + '_' + '.'
    for char in name:
        if char not in valid_chars:
            return False
    return True


def match(iterable, *args):
    skip_size = False
    if args and args[-1] == Ellipsis:
        if len(iterable) < len(args):
            return False
        skip_size = True
    if not skip_size and len(iterable) != len(args):
        return False
    for index, pattern in enumerate(args):
        if pattern in (None, Ellipsis):
            continue

        if isinstance(pattern, str):
            if iterable[index].upper() == pattern.upper():
                continue
        elif callable(pattern):
            if pattern(iterable[index]):
                continue
        elif any([iterable[index].upper() == x.upper() for x in pattern]):
            continue
        return False
    return True
