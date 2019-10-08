
from necroassembler.assembler import Assembler, opcode


def opcode(name):
    def wrapper(f):
        f.opcode = name
        return f
    return wrapper
