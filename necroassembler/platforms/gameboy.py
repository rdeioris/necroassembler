from necroassembler.cpu.lr35902 import AssemblerLR35902


class AssemblerGameboy(AssemblerLR35902):

    cartridge_set = False

    def register_directives(self):
        self.register_directive('cartridge', self.generate_cartridge_header)

    def generate_cartridge_header(self, instr):
        self.change_org(0x100, 0x14f)
        nop_jp_150 = b'\x00\xC3\x50\x01'
        nintendo_logo = bytes((
            0xCE, 0xED, 0x66, 0x66, 0xCC, 0x0D, 0x00, 0x0B,
            0x03, 0x73, 0x00, 0x83, 0x00, 0x0C, 0x00, 0x0D,
            0x00, 0x08, 0x11, 0x1F, 0x88, 0x89, 0x00, 0x0E,
            0xDC, 0xCC, 0x6E, 0xE6, 0xDD, 0xDD, 0xD9, 0x99,
            0xBB, 0xBB, 0x67, 0x63, 0x6E, 0x0E, 0xEC, 0xCC,
            0xDD, 0xDC, 0x99, 0x9F, 0xBB, 0xB9, 0x33, 0x3E))
        self.append_assembled_bytes(nop_jp_150 +
                                    nintendo_logo +
                                    # title
                                    bytes(16) +
                                    # license
                                    bytes(2) +
                                    # sgb + cartridge type
                                    bytes(2) +
                                    # ROM size + RAM size
                                    bytes(2) +
                                    # destination code
                                    bytes(1) +
                                    # old license
                                    b'\x33' +
                                    # version
                                    bytes(1) +
                                    # checksums
                                    bytes(3))
        self.cartridge_set = True

    def fix(self):
        # header checksum
        header_checksum = 0
        for i in range(0x134, 0x14d):
            header_checksum = header_checksum - \
                int(self.assembled_bytes[i]) - 1
        self.assembled_bytes[0x14d] = header_checksum & 0xFF

        # global checksum
        global_checksum = 0
        for byte in self.assembled_bytes:
            global_checksum += int(byte)

        self.assembled_bytes[0x14e] = (global_checksum >> 8) & 0xFF
        self.assembled_bytes[0x14f] = global_checksum & 0xFF


def main():
    import sys
    asm = AssemblerGameboy()
    asm.assemble_file(sys.argv[1])
    asm.link()

    asm.fix()

    asm.save(sys.argv[2])


if __name__ == '__main__':
    main()
