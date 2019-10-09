import unittest
from necroassembler.cpu.gameboy import AssemblerGameboy


class TestGameboy(unittest.TestCase):

    def setUp(self):
        self.asm = AssemblerGameboy()

    def test_ld_a_hl_plus(self):
        self.asm.assemble('LD A,(HL+)')
        self.assertEqual(self.asm.assembled_bytes, b'\x2A')

    def test_ld_line0(self):
        self.asm.assemble(
            'NOP\nloop: LD BC, $17\nLD (BC),A\nLD B,$22\nLD (loop),SP\nLD A,(BC)\nLD C,$30')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x00\x01\x17\x00\x02\x06\x22\x08\x01\x00\x0A\x0E\x30')

    def test_inc_line0(self):
        self.asm.assemble('INC BC\nINC B\nINC C')
        self.assertEqual(self.asm.assembled_bytes, b'\x03\x04\x0C')
