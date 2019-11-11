from necroassembler.cpu.x86 import AssemblerX86
from necroassembler.linker import ELF


def main():
    elf_linker = ELF(64, False, 0x01, machine=0x3E)
    AssemblerX86.main(linker=elf_linker)


if __name__ == '__main__':
    main()
