from necroassembler.cpu.powerpc import AssemblerPowerPC
from necroassembler.linker import ELF


def main():
    elf_linker = ELF(32, True, 0x01, machine=0x14, alignment=4)
    AssemblerPowerPC.main(linker=elf_linker)


if __name__ == '__main__':
    main()
