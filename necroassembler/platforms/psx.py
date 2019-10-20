from necroassembler.cpu.mips32 import AssemblerMIPS32
from necroassembler.utils import pack_le32u


class AssemberPSX(AssemblerMIPS32):

    big_endian = False


def main():
    import sys
    asm = AssemberPSX()
    asm.assemble_file(sys.argv[1])
    asm.link()

    padding = len(asm.assembled_bytes) % 2048
    if padding != 0:
        asm.assembled_bytes += bytes(2048 - padding)

    with open(sys.argv[2], 'wb') as output:
        output.write('PS-X EXE'.encode('ascii'))
        output.seek(0x10)
        output.write(b'\x00\x00\x01\x80')  # pc 0x80010000
        output.write(b'\xFF\xFF\xFF\xFF')  # gp
        output.write(b'\x00\x00\x01\x80')  # text 0x80010000
        output.write(pack_le32u(len(asm.assembled_bytes)))
        output.write(b'\xF0\xFF\x1F\x80')  # stack ptr
        output.seek(0x4C)
        output.write(
            'Sony Computer Entertainment Inc. for Europe area'.encode('ascii'))
        output.seek(0x800)
        output.write(asm.assembled_bytes)


if __name__ == '__main__':
    main()
