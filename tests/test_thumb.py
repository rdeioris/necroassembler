import unittest
from necroassembler.cpu.thumb import AssemblerThumb


class TestThumb(unittest.TestCase):

    def setUp(self):
        self.asm = AssemblerThumb()

    def test_lsl(self):
        self.asm.assemble('LSL r3, r4, #31')
        self.assertEqual(self.asm.assembled_bytes, b'\xE3\x07')

    def test_lsr(self):
        self.asm.assemble('LSR r1, r2, #2')
        self.assertEqual(self.asm.assembled_bytes, b'\x91\x08')

    def test_asr(self):
        self.asm.assemble('ASR r5, r6, #3')
        self.assertEqual(self.asm.assembled_bytes, b'\xF5\x10')

    def test_sub(self):
        self.asm.assemble('SUB r1, r2, r3\nSUB r4, r5, #7\nSUB r6, #5')
        self.assertEqual(self.asm.assembled_bytes, b'\xD1\x1A\xEC\x1F\x05\x3E')

    def test_cmp(self):
        self.asm.assemble('CMP r7, #0xff')
        self.assertEqual(self.asm.assembled_bytes, b'\xFF\x2F')
