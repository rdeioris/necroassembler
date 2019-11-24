import unittest
from necroassembler.cpu.mos6502 import AssemblerMOS6502, InvalidMode, UnsupportedModeForOpcode
from necroassembler.exceptions import (
    InvalidOpCodeArguments, NotInBitRange, NotInSignedBitRange, OnlyForwardAddressesAllowed, OnlyPositiveValuesAllowed)


class TestMOS6502(unittest.TestCase):

    def setUp(self):
        self.asm = AssemblerMOS6502()

    def test_lda_immediate(self):
        self.asm.assemble('LDA #$17\nlda #17\nLdA #%11111111')
        self.assertEqual(self.asm.assembled_bytes, b'\xA9\x17\xA9\x11\xA9\xFF')

    def test_nop(self):
        self.asm.assemble('NOP')
        self.assertEqual(self.asm.assembled_bytes, b'\xEA')

    def test_two_nops(self):
        self.asm.assemble(' NOP \n NOP')
        self.assertEqual(self.asm.assembled_bytes, b'\xEA\xEA')

    def test_lda_zp(self):
        self.asm.assemble('LDA $17')
        self.assertEqual(self.asm.assembled_bytes, b'\xA5\x17')

    def test_lda_immediate_label(self):
        self.asm.assemble(
            '.org $1000\n.db 1,2,3,4,5\ntest: .db 6,7,8\nLDA #test & $ff')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, bytes(
            (1, 2, 3, 4, 5, 6, 7, 8, 0xA9, 0x05)))

    def test_lda_immediate_label_plus_one(self):
        self.asm.assemble(
            '.org $1000\n.db 1,2,3,4,5\ntest: .db 6,7,8\nLDA #[[test++] &$FF]')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, bytes(
            (1, 2, 3, 4, 5, 6, 7, 8, 0xA9, 0x06)))

    def test_lda_immediate_label_plus_three(self):
        self.asm.assemble(
            '.org $1000\n.db 1,2,3,4,5\ntest: .db 6,7,8\nLDA #[[test+3] & $ff]')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, bytes(
            (1, 2, 3, 4, 5, 6, 7, 8, 0xA9, 0x08)))

    def test_lda_immediate_label_plus_dash(self):
        self.asm.assemble(
            '.org $1000\n.db 1,2,3,4,5\ntest: .db 6,7,8\nLDA #[test+1-1+1-1] & $ff')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, bytes(
            (1, 2, 3, 4, 5, 6, 7, 8, 0xA9, 0x05)))

    def test_lda_immediate_label_shift(self):
        self.asm.assemble(
            '.org $1000\n.db 1,2,3,4,5\ntest: .db 6,7,8\nLDA #test>>8')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, bytes(
            (1, 2, 3, 4, 5, 6, 7, 8, 0xA9, 0x10)))

    def test_lda_ind_x(self):
        self.asm.assemble('LDA ($17,  X)')
        self.assertEqual(self.asm.assembled_bytes, b'\xA1\x17')

    def test_flags(self):
        self.asm.assemble('CLC\nSEC\nCLI\nSEI\nCLV\nCLD\nSED')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x18\x38\x58\x78\xB8\xD8\xF8')

    def test_regs(self):
        self.asm.assemble('TAX\nTXA\nDEX\nINX\nTAY\nTYA\nDEY\nINY')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xAA\x8A\xCA\xE8\xA8\x98\x88\xC8')

    def test_stack(self):
        self.asm.assemble('TXS\nTSX\nPHA\nPLA\nPHP\nPLP')
        self.assertEqual(self.asm.assembled_bytes, b'\x9A\xBA\x48\x68\x08\x28')

    def test_jsr(self):
        self.asm.assemble('.org $100 \nloop: JSR loop')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\x20\x00\x01')

    def test_jmp(self):
        self.asm.assemble('loop: JMP loop')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\x4C\x00\x00')

    def test_jmp_indirect(self):
        self.asm.assemble('loop: .dw foo\nJMP (loop)\nfoo: JMP foo')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x05\x00\x6C\x00\x00\x4C\x05\x00')

    def test_invalid_bit(self):
        self.assertRaises(UnsupportedModeForOpcode,
                          self.asm.assemble, 'BIT #$17')

    def test_beq(self):
        self.asm.assemble('loop:NOP\nBEQ loop')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\xEA\xF0\xFD')

    def test_beq_numeric(self):
        self.asm.assemble('BEQ -3')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\xF0\xFD')

    def test_jmp_backward(self):
        self.assertRaises(OnlyPositiveValuesAllowed,
                          self.asm.assemble, 'JMP -3')

    def test_branch(self):
        self.asm.assemble(
            'loop: BPL loop\nBMI loop\nBVC loop\nBVS loop\nBCC loop\nBCS loop\nBNE loop\nBEQ loop')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x10\xFE\x30\xFC\x50\xFA\x70\xF8\x90\xF6\xB0\xF4\xD0\xF2\xF0\xF0')

    def test_adc(self):
        self.asm.assemble('ADC #$44')
        self.asm.assemble('ADC $44')
        self.asm.assemble('ADC $44, X')
        self.asm.assemble('ADC $4400')
        self.asm.assemble('ADC $4400,X')
        self.asm.assemble('ADC $4400,Y')
        self.asm.assemble('ADC ($44, X)')
        self.asm.assemble('ADC ($44), Y')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x69\x44\x65\x44\x75\x44\x6D\x00\x44\x7D\x00\x44\x79\x00\x44\x61\x44\x71\x44')

    def test_and(self):
        self.asm.assemble('AND #$44')
        self.asm.assemble('AND $44')
        self.asm.assemble('AND $44, X')
        self.asm.assemble('AND $4400')
        self.asm.assemble('AND $4400,X')
        self.asm.assemble('AND $4400,Y')
        self.asm.assemble('AND ($44, X)')
        self.asm.assemble('AND ($44), Y')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x29\x44\x25\x44\x35\x44\x2D\x00\x44\x3D\x00\x44\x39\x00\x44\x21\x44\x31\x44')

    def test_asl(self):
        self.asm.assemble('ASL A')
        self.asm.assemble('ASL $44')
        self.asm.assemble('ASL $44, X')
        self.asm.assemble('ASL $4400')
        self.asm.assemble('ASL $4400,X')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x0A\x06\x44\x16\x44\x0E\x00\x44\x1E\x00\x44')

    def test_bit(self):
        self.asm.assemble('BIT $44')
        self.asm.assemble('BIT $4400')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x24\x44\x2C\x00\x44')

    def test_brk(self):
        self.asm.assemble('BRK')
        self.assertEqual(self.asm.assembled_bytes, b'\x00')

    def test_brk_bad(self):
        self.assertRaises(InvalidOpCodeArguments,
                          self.asm.assemble, 'BRK oops')

    def test_cmp(self):
        self.asm.assemble('CMP #$44')
        self.asm.assemble('CMP $44')
        self.asm.assemble('CMP $44, X')
        self.asm.assemble('CMP $4400')
        self.asm.assemble('CMP $4400,X')
        self.asm.assemble('CMP $4400,Y')
        self.asm.assemble('CMP ($44, X)')
        self.asm.assemble('CMP ($44), Y')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xC9\x44\xC5\x44\xD5\x44\xCD\x00\x44\xDD\x00\x44\xD9\x00\x44\xC1\x44\xD1\x44')

    def test_cpx(self):
        self.asm.assemble('CPX #$44')
        self.asm.assemble('CPX $44')
        self.asm.assemble('CPX $4400')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xE0\x44\xE4\x44\xEC\x00\x44')

    def test_cpy(self):
        self.asm.assemble('CPY #$44')
        self.asm.assemble('CPY $44')
        self.asm.assemble('CPY $4400')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xC0\x44\xC4\x44\xCC\x00\x44')

    def test_dec(self):
        self.asm.assemble('DEC $44')
        self.asm.assemble('DEC $44, X')
        self.asm.assemble('DEC $4400')
        self.asm.assemble('DEC $4400,X')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xC6\x44\xD6\x44\xCE\x00\x44\xDE\x00\x44')

    def test_eor(self):
        self.asm.assemble('EOR #$44')
        self.asm.assemble('EOR $44')
        self.asm.assemble('EOR $44, X')
        self.asm.assemble('EOR $4400')
        self.asm.assemble('EOR $4400,X')
        self.asm.assemble('EOR $4400,Y')
        self.asm.assemble('EOR ($44, X)')
        self.asm.assemble('EOR ($44), Y')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x49\x44\x45\x44\x55\x44\x4D\x00\x44\x5D\x00\x44\x59\x00\x44\x41\x44\x51\x44')

    def test_inc(self):
        self.asm.assemble('INC $44')
        self.asm.assemble('INC $44, X')
        self.asm.assemble('INC $4400')
        self.asm.assemble('INC $4400,X')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xE6\x44\xF6\x44\xEE\x00\x44\xFE\x00\x44')

    def test_lda(self):
        self.asm.assemble('LDA #$44')
        self.asm.assemble('LDA $44')
        self.asm.assemble('LDA $44, X')
        self.asm.assemble('LDA $4400')
        self.asm.assemble('LDA $4400,X')
        self.asm.assemble('LDA $4400,Y')
        self.asm.assemble('LDA ($44, X)')
        self.asm.assemble('LDA ($44), Y')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xA9\x44\xA5\x44\xB5\x44\xAD\x00\x44\xBD\x00\x44\xB9\x00\x44\xA1\x44\xB1\x44')

    def test_ldx(self):
        self.asm.assemble('LDX #$44')
        self.asm.assemble('LDX $44')
        self.asm.assemble('LDX $44, Y')
        self.asm.assemble('LDX $4400')
        self.asm.assemble('LDX $4400,Y')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xA2\x44\xA6\x44\xB6\x44\xAE\x00\x44\xBE\x00\x44')

    def test_ldy(self):
        self.asm.assemble('LDY #$44')
        self.asm.assemble('LDY $44')
        self.asm.assemble('LDY $44, X')
        self.asm.assemble('LDY $4400')
        self.asm.assemble('LDY $4400,X')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xA0\x44\xA4\x44\xB4\x44\xAC\x00\x44\xBC\x00\x44')

    def test_lsr(self):
        self.asm.assemble('LSR A')
        self.asm.assemble('LSR $44')
        self.asm.assemble('LSR $44, X')
        self.asm.assemble('LSR $4400')
        self.asm.assemble('LSR $4400,X')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x4A\x46\x44\x56\x44\x4E\x00\x44\x5E\x00\x44')

    def test_ora(self):
        self.asm.assemble('ORA #$44')
        self.asm.assemble('ORA $44')
        self.asm.assemble('ORA $44, X')
        self.asm.assemble('ORA $4400')
        self.asm.assemble('ORA $4400,X')
        self.asm.assemble('ORA $4400,Y')
        self.asm.assemble('ORA ($44, X)')
        self.asm.assemble('ORA ($44), Y')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x09\x44\x05\x44\x15\x44\x0D\x00\x44\x1D\x00\x44\x19\x00\x44\x01\x44\x11\x44')

    def test_rol(self):
        self.asm.assemble('ROL A')
        self.asm.assemble('ROL $44')
        self.asm.assemble('ROL $44, X')
        self.asm.assemble('ROL $4400')
        self.asm.assemble('ROL $4400,X')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x2A\x26\x44\x36\x44\x2E\x00\x44\x3E\x00\x44')

    def test_ror(self):
        self.asm.assemble('ROR A')
        self.asm.assemble('ROR $44')
        self.asm.assemble('ROR $44, X')
        self.asm.assemble('ROR $4400')
        self.asm.assemble('ROR $4400,X')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x6A\x66\x44\x76\x44\x6E\x00\x44\x7E\x00\x44')

    def test_rti(self):
        self.asm.assemble('rti')
        self.assertEqual(self.asm.assembled_bytes, b'\x40')

    def test_rts(self):
        self.asm.assemble('RTS')
        self.assertEqual(self.asm.assembled_bytes, b'\x60')

    def test_sbc(self):
        self.asm.assemble('SBC #$44')
        self.asm.assemble('SBC $44')
        self.asm.assemble('SBC $44, X')
        self.asm.assemble('SBC $4400')
        self.asm.assemble('SBC $4400,X')
        self.asm.assemble('SBC $4400,Y')
        self.asm.assemble('SBC ($44, X)')
        self.asm.assemble('SBC ($44), Y')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xE9\x44\xE5\x44\xF5\x44\xED\x00\x44\xFD\x00\x44\xF9\x00\x44\xE1\x44\xF1\x44')

    def test_sta(self):
        self.asm.assemble('STA $44')
        self.asm.assemble('STA $44, X')
        self.asm.assemble('STA $4400')
        self.asm.assemble('STA $4400,X')
        self.asm.assemble('STA $4400,Y')
        self.asm.assemble('STA ($44, X)')
        self.asm.assemble('STA ($44), Y')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x85\x44\x95\x44\x8D\x00\x44\x9D\x00\x44\x99\x00\x44\x81\x44\x91\x44')

    def test_stx(self):
        self.asm.assemble('STX $44')
        self.asm.assemble('STX $44, Y')
        self.asm.assemble('STX $4400')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x86\x44\x96\x44\x8E\x00\x44')

    def test_sty(self):
        self.asm.assemble('STY $44')
        self.asm.assemble('STY $44, X')
        self.asm.assemble('STY $4400')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x84\x44\x94\x44\x8C\x00\x44')

    def test_lda_negative(self):
        self.asm.assemble('LDA #-1')
        self.assertEqual(self.asm.assembled_bytes, b'\xA9\xFF')

    def test_lda_negative_raw(self):
        self.asm.assemble('LDA #$ff')
        self.assertEqual(self.asm.assembled_bytes, b'\xA9\xFF')

    def test_lda_wrong(self):
        self.assertRaises(NotInBitRange, self.asm.assemble, 'LDA #$1ff')

    def test_lda_wrong_binary(self):
        self.assertRaises(NotInBitRange, self.asm.assemble, 'LDA #%111111110')

    def test_lda_wrong_big(self):
        self.assertRaises(NotInBitRange, self.asm.assemble, 'LDA #1234')

    def test_lda_wrong_negative(self):
        self.assertRaises(NotInSignedBitRange, self.asm.assemble, 'LDA #-129')

    def test_lda_wrong_positive(self):
        self.assertRaises(NotInBitRange, self.asm.assemble, 'LDA #256')

    def test_lda_last_negative(self):
        self.asm.assemble('LDA #-128')
        self.assertEqual(self.asm.assembled_bytes, b'\xA9\x80')
