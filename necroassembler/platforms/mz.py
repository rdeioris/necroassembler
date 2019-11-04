import necroassembler.cpu.intel8086 as intel8086
from necroassembler.cpu.intel8086 import AssemblerIntel8086

original__Ap = intel8086._Ap


def _relocatable_Ap(instr, assembler, index, modrm):
    ret = original__Ap(instr, assembler, index, modrm)
    if ret:
        assembler.relocation_table.append(None)
    return ret

intel8086._Ap = _relocatable_Ap

