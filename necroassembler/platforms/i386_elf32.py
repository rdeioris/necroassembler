from necroassembler.cpu.intel8086 import AssemblerIntel8086
from necroassembler.linker import ELF


def main():
    elf_linker = ELF(32, False, 0x01, machine=0x3)
    AssemblerIntel8086.main(linker=elf_linker)


if __name__ == '__main__':
    main()
