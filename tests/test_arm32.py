import unittest
from necroassembler.cpu.arm32 import AssemblerARM32
from necroassembler.exceptions import InvalidOpCodeArguments


class TestARM32(unittest.TestCase):

    def setUp(self):
        self.asm = AssemblerARM32()

    def test_mov_imm(self):
        self.asm.assemble('mov r4, #17')
        self.assertEqual(self.asm.assembled_bytes, b'\x11\x40\xA0\xE3')

    def test_mov_reg(self):
        self.asm.assemble('mov r4, r5')
        self.assertEqual(self.asm.assembled_bytes, b'\x05\x40\xA0\xE1')

    def test_mov_reg_shift_reg(self):
        self.asm.assemble('mov r4, r5, lsl r2')
        self.assertEqual(self.asm.assembled_bytes, b'\x15\x42\xA0\xE1')

    def test_mov_reg_shift_n(self):
        self.asm.assemble('mov r4, r5, lsl #3')
        self.assertEqual(self.asm.assembled_bytes, b'\x85\x41\xA0\xE1')

    def test_add_reg_shift_n(self):
        self.asm.assemble('add r4, r5, r6, lsl #3')
        self.assertEqual(self.asm.assembled_bytes, b'\x86\x41\x85\xE0')

    def test_add_reg_rotate_reg(self):
        self.asm.assemble('ADD R4,R5,R6,ROR R2')
        self.assertEqual(self.asm.assembled_bytes, b'\x76\x42\x85\xE0')

    def test_add_reg_rrx(self):
        self.asm.assemble('ADD R4,R5,R6,RRX')
        self.assertEqual(self.asm.assembled_bytes, b'\x66\x40\x85\xE0')

    