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
...
```

all of the wrappers have the same syntax:

```sh
necro_<platform>.exe <src> <dst>
```

## Platforms

In addition to 'core' assemblers, a bunch of ready to use subclasses and related wrappers are available for specific platforms (mainly 80's and 90's game consoles and home computers).

As an example the AssemblerGameboy class exposes utilities for importing images as well as setting the cartridge header for you roms:

```asm
.org $0000 $7fff ; the size of the cartridge must be 32k (second bank at $4000 can be bank-switched)

.goto $100 ; cartridge header must be at $100
.cartridge
.cartridge_title "NECROBOY"

.goto $150 ; start of the program
LD SP, $FFFE ; setup stack


CALL turn_off_lcd ; before accesing vram we need to turn off the lcd

; file tiles
LD HL, start_of_tiles
LD BC, end_of_tiles-start_of_tiles ; label math is so handy...
LD DE, VRAM
fill_tiles:
LD A, (HL+)
LD (DE), A
INC DE
DEC BC
LD A, B
OR C
JR NZ, fill_tiles

; clear tilemap
LD HL, TMAP0
LD BC, 32*32 ; integers and labels have math by default
clear_tilemap:
LD A, 28 ; '28' is the empty tile (see below)
LD (HL+), A
DEC BC
LD A, B
OR C
JR NZ, clear_tilemap

; fill tilemap
LD HL, start_of_tilemap
LD BC, end_of_tilemap-start_of_tilemap
LD DE, TMAP0
fill_tilemap:
LD A, (HL+)
LD (DE), A
INC DE
DEC BC
LD A, B
OR C
JR NZ, fill_tilemap

CALL turn_on_lcd

XOR A
LD (scroll), A
loop:
CALL wait_vblank
LD A, (scroll)
LD (SCX), A ; increment scroll x
LD (SCY), A ; increment scroll y
INC A
LD (scroll), A
JP loop

wait_vblank:
	LD A, (LY)
	CP 144
	JP NZ, wait_vblank
	RET

turn_off_lcd:
	CALL wait_vblank
	XOR A
	LD (LCDC), A
	RET

turn_on_lcd:
	LD A, %10010001 ; enable lcd and background
	LD (LCDC), A
	RET

start_of_tiles:
.tiles "docs/necroassembler_112x16.bmp"
.db 0,0 ; this is the tile 28 (empty)
end_of_tiles:

```

The '.tiles' directive transforms an indexed (palette-based) image (max 4 colors) to a gameboy-compatibile tileset, while the '.cartridge' stuff build and fix the rom for being used in an emulator or a true gameboy hardware

## Installation

just

```sh
pip install necroassembler
```

## Labels and Directives

## Building your own assembler



## Sponsor

The necroassembler development is sponsored by AIV (Accademia Italiana Videogiochi)
