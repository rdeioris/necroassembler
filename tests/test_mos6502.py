import unittest
from necroassembler.cpu.mos6502 import AssemblerMOS6502, InvalidMode, UnsupportedModeForOpcode


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
            '.org $1000\n.db 1,2,3,4,5\ntest: .db 6,7,8\nLDA #<test')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, bytes(
            (1, 2, 3, 4, 5, 6, 7, 8, 0xA9, 0x05)))

    def test_lda_immediate_label_plus_one(self):
        self.asm.assemble(
            '.org $1000\n.db 1,2,3,4,5\ntest: .db 6,7,8\nLDA #<test+')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, bytes(
            (1, 2, 3, 4, 5, 6, 7, 8, 0xA9, 0x06)))

    def test_lda_immediate_label_plus_three(self):
        self.asm.assemble(
            '.org $1000\n.db 1,2,3,4,5\ntest: .db 6,7,8\nLDA #>test+++')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, bytes(
            (1, 2, 3, 4, 5, 6, 7, 8, 0xA9, 0x13)))

    def test_lda_immediate_label_plus_dash(self):
        self.asm.assemble(
            '.org $1000\n.db 1,2,3,4,5\ntest: .db 6,7,8\nLDA #<test+-+-')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, bytes(
            (1, 2, 3, 4, 5, 6, 7, 8, 0xA9, 0x05)))

    def test_lda_immediate_label_shift(self):
        self.asm.assemble(
            '.org $1000\n.db 1,2,3,4,5\ntest: .db 6,7,8\nLDA #>test')
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

    def test_jmp(self):
        self.asm.assemble('loop: JMP loop')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\x4C\x00\x00')

    def test_invalid_bit(self):
        self.assertRaises(UnsupportedModeForOpcode,
                          self.asm.assemble, 'BIT #$17')

    def test_beq(self):
        self.asm.assemble('loop:\nNOP\nBEQ loop')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\xEA\xF0\xFD')

    def test_beq_numeric(self):
        self.asm.assemble('BEQ -3')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\xF0\xFD')

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
