import unittest
from necroassembler.cpu.intel8086 import AssemblerIntel8086
from necroassembler.exceptions import InvalidOpCodeArguments


class TestIntel8086(unittest.TestCase):

    def setUp(self):
        self.asm = AssemblerIntel8086()

    def test_mov_ch_bh(self):
        self.asm.assemble('MOV CH, BH')
        self.assertEqual(self.asm.assembled_bytes, b'\x88\xFD')

    def test_mov_cx_bx(self):
        self.asm.assemble('MOV CX, BX')
        self.assertEqual(self.asm.assembled_bytes, b'\x89\xD9')

    def test_mov_cx_ind_bx(self):
        self.asm.assemble('MOV CX, [BX]')
        self.assertEqual(self.asm.assembled_bytes, b'\x8B\x0F')

    def test_mov_ind_bx_cx(self):
        self.asm.assemble('MOV [BX], CX')
        self.assertEqual(self.asm.assembled_bytes, b'\x89\x0F')

    def test_mov_ind_bx_cx_displacement(self):
        self.asm.assemble('MOV [BX - 2], CX')
        self.assertEqual(self.asm.assembled_bytes, b'\x89\x8F\xFE\xFF')

    def test_mov_ind_bx_cx_displacement_plus(self):
        self.asm.assemble('MOV [BX + 2], CX')
        self.assertEqual(self.asm.assembled_bytes, b'\x89\x8F\x02\x00')

    def test_mov_immediate8(self):
        self.asm.assemble('MOV DL, 0x17')
        self.assertEqual(self.asm.assembled_bytes, b'\xB2\x17')

    def test_mov_immediate16(self):
        self.asm.assemble('MOV DX, 0x17')
        self.assertEqual(self.asm.assembled_bytes, b'\xBA\x17\x00')

    def test_lds(self):
        self.asm.assemble('LDS AX, [0x17]')
        self.assertEqual(self.asm.assembled_bytes, b'\xC5\x06\x17\x00')

    def test_al_ob(self):
        self.asm.assemble('MOV AL, [0x17]')
        self.assertEqual(self.asm.assembled_bytes, b'\xA0\x17\x00')

    def test_jmp_b(self):
        self.asm.assemble('JMP 4')
        self.assertEqual(self.asm.assembled_bytes, b'\xE9\x04\x00')

    def test_aaa(self):
        self.asm.assemble('AAA')
        self.assertEqual(self.asm.assembled_bytes, b'\x37')

    def test_aaa_args(self):
        self.assertRaises(InvalidOpCodeArguments, self.asm.assemble, 'AAA AX')

    def test_aad(self):
        self.asm.assemble('AAD')
        self.assertEqual(self.asm.assembled_bytes, b'\xD5')

    def test_aad_a(self):
        self.asm.assemble('AAD 0x0A')
        self.assertEqual(self.asm.assembled_bytes, b'\xD5')

    def test_aad_1(self):
        self.asm.assemble('AAD 0x01')
        self.assertEqual(self.asm.assembled_bytes, b'\xD5\x01')

    def test_aam(self):
        self.asm.assemble('AAM')
        self.assertEqual(self.asm.assembled_bytes, b'\xD4')

    def test_aam_a(self):
        self.asm.assemble('AAM 0x0A')
        self.assertEqual(self.asm.assembled_bytes, b'\xD4')

    def test_aam_2(self):
        self.asm.assemble('AAM 0x02')
        self.assertEqual(self.asm.assembled_bytes, b'\xD4\x02')

    def test_aas(self):
        self.asm.assemble('AAS')
        self.assertEqual(self.asm.assembled_bytes, b'\x3F')

    def test_aas_args(self):
        self.assertRaises(InvalidOpCodeArguments, self.asm.assemble, 'AAS BX')
