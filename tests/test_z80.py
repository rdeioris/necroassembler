import unittest
from necroassembler.cpu.z80 import AssemblerZ80
from necroassembler.exceptions import InvalidOpCodeArguments


class TestZ80(unittest.TestCase):

    def setUp(self):
        self.asm = AssemblerZ80()

    def test_ld_hl_address(self):
        self.asm.assemble('LD HL, ($1000)')
        self.assertEqual(self.asm.assembled_bytes, b'\x2A\x00\x10')

    def test_dec_b(self):
        self.asm.assemble('DEC b')
        self.assertEqual(self.asm.assembled_bytes, b'\x05')

    def test_call_z(self):
        self.asm.assemble('CALL z, $1234')
        self.assertEqual(self.asm.assembled_bytes, b'\xCC\x34\x12')

    def test_ex_sp_hl(self):
        self.asm.assemble('EX (sp), Hl')
        self.assertEqual(self.asm.assembled_bytes, b'\xE3')

    def test_im_1(self):
        self.asm.assemble('im 1')
        self.assertEqual(self.asm.assembled_bytes, b'\xED\x56')

    def test_sll_h(self):
        self.asm.assemble('sll h')
        self.assertEqual(self.asm.assembled_bytes, b'\xCB\x34')

    def test_set_4_l(self):
        self.asm.assemble('set 4, l')
        self.assertEqual(self.asm.assembled_bytes, b'\xCB\xE5')

    def test_ld_ixh_ixl(self):
        self.asm.assemble('ld ixh, ixl')
        self.assertEqual(self.asm.assembled_bytes, b'\xDD\x65')

    def test_ld_l_ix_3(self):
        self.asm.assemble('ld l, (ix+3)')
        self.assertEqual(self.asm.assembled_bytes, b'\xDD\x6E\x03')

    def test_adc_a_ix(self):
        self.asm.assemble('ADC a, (IX - 1)')
        self.assertEqual(self.asm.assembled_bytes, b'\xDD\x8E\xFF')

    def test_res_0_iy_a(self):
        self.asm.assemble('LD a, ReS 0, ( IY- 2)')
        self.assertEqual(self.asm.assembled_bytes, b'\xFD\xCB\xFE\x87')
    
    def test_res_7_iy(self):
        self.asm.assemble('RES 7, (IY+5)')
        self.assertEqual(self.asm.assembled_bytes, b'\xFD\xCB\x05\xBE')

    def test_rrc_iy_a(self):
        self.asm.assemble('LD a, RRc, ( IY- 2)')
        self.assertEqual(self.asm.assembled_bytes, b'\xFD\xCB\xFE\x0F')

    def test_ex_af_af_tick(self):
        self.asm.assemble('Ex Af,  af\'')
        self.assertEqual(self.asm.assembled_bytes, b'\x08')

    def test_halt(self):
        self.asm.assemble('hAlT')
        self.assertEqual(self.asm.assembled_bytes, b'\x76')

    def test_in(self):
        self.asm.assemble('IN (C)')
        self.asm.assemble('IN F, (C)')
        self.assertEqual(self.asm.assembled_bytes, b'\xED\x70\xED\x70')

    def test_rst_28h(self):
        self.asm.assemble('RST 28h')
        self.assertEqual(self.asm.assembled_bytes, b'\xEF')

    