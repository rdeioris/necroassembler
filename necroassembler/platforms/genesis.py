from necroassembler.cpu.mc68000 import AssemblerMC68000


def main():
    import sys
    asm = AssemblerMC68000()
    asm.assemble_file(sys.argv[1])
    asm.link()

    # fix checksums

    # header checksum
    header_checksum = 0
    for i in range(0x200, len(asm.assembled_bytes), 2):
        high = asm.assembled_bytes[i]
        low = asm.assembled_bytes[i+1]
        header_checksum += (high << 8) | low
    asm.assembled_bytes[0x18e] = (header_checksum >> 8) & 0xFF
    asm.assembled_bytes[0x18f] = header_checksum & 0xFF

    asm.save(sys.argv[2])


if __name__ == '__main__':
    main()
