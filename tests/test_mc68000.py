import unittest
from necroassembler.cpu.mc68000 import AssemblerMC68000
from necroassembler.exceptions import NotInBitRange


class TestMC68000(unittest.TestCase):

    def setUp(self):
        self.asm = AssemblerMC68000()

    def test_move_address_indexed(self):
        self.asm.assemble('move #17, (17, a0, a1)')
        self.assertEqual(self.asm.assembled_bytes, b'\x31\xBC\x00\x11\x90\x11')

    def test_move_w_address_indexed(self):
        self.asm.assemble('move.w #17, (17, a0, a1)')
        self.assertEqual(self.asm.assembled_bytes, b'\x31\xBC\x00\x11\x90\x11')

    def test_move_w_address_indexed_l(self):
        self.asm.assemble('move.w #17, (17, a0, a1.L)')
        self.assertEqual(self.asm.assembled_bytes, b'\x31\xBC\x00\x11\x98\x11')

    def test_move_d4_d3(self):
        self.asm.assemble(' move d4, d3')
        self.assertEqual(self.asm.assembled_bytes, b'\x36\x04')

    def test_move_d5_a6(self):
        self.asm.assemble('MOVE d5, a6')
        self.assertEqual(self.asm.assembled_bytes, b'\x3C\x45')

    def test_move_d1_ind_a1(self):
        self.asm.assemble('move d1, (a1)')
        self.assertEqual(self.asm.assembled_bytes, b'\x32\x81')

    def test_move_a3_dec_ind_a2(self):
        self.asm.assemble('move a3, -(a2)')
        self.assertEqual(self.asm.assembled_bytes, b'\x35\x0B')

    def test_move_label_pc_a1(self):
        self.asm.assemble('move (foo, PC), a1\nfoo:')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\x32\x7A\x00\x02')

    def test_move_label_backward_pc_a1(self):
        self.asm.assemble('foo: move (foo, PC), a1')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\x32\x7A\xFF\xFE')

    def test_move_too_far_backward_pc_a1(self):
        self.assertRaises(NotInBitRange, self.asm.assemble,
                          'move (-32769, PC), a1')

    def test_move_far_backward_pc_a1(self):
        self.asm.assemble('move (-32768, PC), a1')
        self.assertEqual(self.asm.assembled_bytes, b'\x32\x7A\x80\x00')

    def test_move_disp_pc_a0l_a3(self):
        self.asm.assemble('move (8, PC, a0.l), a3')
        self.assertEqual(self.asm.assembled_bytes, b'\x36\x7b\x88\x08')

    def test_move_abs_l_a0(self):
        self.asm.assemble('move (100).l, a0')
        self.assertEqual(self.asm.assembled_bytes, b'\x30\x79\x00\x00\x00\x64')

    def test_move_abs_w_a0(self):
        self.asm.assemble('move (100).w, a0')
        self.assertEqual(self.asm.assembled_bytes, b'\x30\x78\x00\x64')

    def test_ori_ccr(self):
        self.asm.assemble('ori #100, ccr')
        self.assertEqual(self.asm.assembled_bytes, b'\x00\x3C\x00\x64')

    def test_ori_sr(self):
        self.asm.assemble('ori #-1, sr')
        self.assertEqual(self.asm.assembled_bytes, b'\x00\x7C\xff\xff')

    def test_ori_l_disp_a3(self):
        self.asm.assemble('ori.l #10000, (100, a3)')
        self.assertEqual(self.asm.assembled_bytes, b'\x00\xAB\x00\x00\x27\x10\x00\x64')

    def test_andi_l_disp_a4(self):
        self.asm.assemble('andi.l #10001, (101, a4)')
        self.assertEqual(self.asm.assembled_bytes, b'\x02\xAC\x00\x00\x27\x11\x00\x65')

    def test_jmp(self):
        self.asm.assemble('jmp 2048')
        self.assertEqual(self.asm.assembled_bytes, b'\x4e\xf9\x00\x00\x08\x00')

    def test_jmp_word(self):
        self.asm.assemble('jmp 2048.w')
        self.assertEqual(self.asm.assembled_bytes, b'\x4e\xf8\x08\x00')
