from necroassembler.cpu.arm32 import AssemblerARM32
from necroassembler.linker import ELF


def main():
    elf_linker = ELF(32, False, 0x02, machine=0x28, alignment=4)
    AssemblerARM32.main(linker=elf_linker)


if __name__ == '__main__':
    main()
