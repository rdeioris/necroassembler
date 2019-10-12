from necroassembler.cpu.thumb import AssemblerThumb


def main():
    import sys
    asm = AssemblerThumb()
    asm.assemble_file(sys.argv[1])
    asm.link()

    # fix checksums

    # header checksum
    header_checksum = 0
    for i in range(0xA0, 0xBD):
        header_checksum = header_checksum - int(asm.assembled_bytes[i])
    asm.assembled_bytes[0xBD] = (header_checksum - 0x19) & 0xFF

    with open(sys.argv[2], 'wb') as stream:
        stream.write(asm.assembled_bytes)


if __name__ == '__main__':
    main()
