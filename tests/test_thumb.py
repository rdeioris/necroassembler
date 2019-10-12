import unittest
from necroassembler.cpu.thumb import AssemblerThumb


class TestThumb(unittest.TestCase):

    def setUp(self):
        self.asm = AssemblerThumb()

    def test_lsl(self):
        self.asm.assemble('LSL r3, r4, #31\n')
        self.assertEqual(self.asm.assembled_bytes, b'\xE3\x07')

    def test_lsr(self):
        self.asm.assemble('LSR r1, r2, #2\n')
        self.assertEqual(self.asm.assembled_bytes, b'\x91\x08')

    def test_asr(self):
        self.asm.assemble('ASR r5, r6, #3\n')
        self.assertEqual(self.asm.assembled_bytes, b'\xF5\x10')
