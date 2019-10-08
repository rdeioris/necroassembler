from necroassembler.assembler import *
from struct import pack


def pack_bytes(*args):
    return pack('B' * len(args), *args)


def pack_le_32s(*args):
    return pack('<' + ('I' * len(args)), *args)


def pack_be_32s(*args):
    return pack('>' + ('I' * len(args)), *args)


def pack_byte(b):
    return pack('B', b)


def opcode(name):
    def wrapper(f):
        f.opcode = name
        return f
    return wrapper
