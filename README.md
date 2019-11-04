# necroassembler
A Python framework for building assemblers, includes ready-to-use modules for 

* 6502 (nes, commodore64, atari2600)
* 8086 (.com and MZ .exe)
* mips32 (psx, nintendo64)
* LR35902 (gameboy)
* ARM Thumb (gameboy advance)
* 68000 (sega genesis/megadrive, amiga)
* AVR (arduino)
* Z80 (ZX spectrum, Sega Master System, Game Gear)
* PowerPC (gamecube, wii)

## Usage

You can use necroassembler from your python code:

```python
>>> from necroassembler.cpu.mos6502 import AssemblerMOS6502
>>> asm = AssemblerMOS6502()
>>> asm.assemble('LDA #17')  
>>> asm.assemble('STA $1111') 
>>> asm.assembled_bytes
bytearray(b'\xa9\x11\x8d\x11\x11')
>>>
```

```python
>>> from necroassembler.cpu.z80 import AssemblerZ80         
>>> asm = AssemblerZ80()
>>> asm.assemble('NOP\nINC BC')  
>>> asm.assembled_bytes         
bytearray(b'\x00\x03')
>>>
```

or directly from command line using the various included wrappers (remove .exe in unix environments):

```sh
necro_6502.exe hello_world.S hello_world.bin
necro_8086.exe bootblock.S block000.bin
necro_m68k.exe copper.S copper.bin
```

all of the wrappers have the same syntax:

```sh
necro_<platform>.exe <src> <dst>
```

## Installation

just

```sh
pip install necroassembler
```

## Sponsor

The necroassembler development is sponsored by AIV (Accademia Italiana Videogiochi)
