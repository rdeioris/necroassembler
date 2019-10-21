import unittest
from necroassembler.cpu.mips32 import AssemblerMIPS32
from necroassembler.exceptions import InvalidBitRange, NotInBitRange


class TestMIPS32(unittest.TestCase):

    def setUp(self):
        self.asm = AssemblerMIPS32()

    def test_add(self):
        self.asm.assemble('add $t3, $t4, $t5')
        self.assertEqual(self.asm.assembled_bytes, b'\x01\x8d\x58\x20')

    def test_add_alias(self):
        self.asm.assemble('add $11, $12, $13')
        self.assertEqual(self.asm.assembled_bytes, b'\x01\x8d\x58\x20')

    def test_addi_wrong(self):
        self.assertRaises(NotInBitRange, self.asm.assemble,
                          'addi $t5, $t6, 65000')

    def test_addi(self):
        self.asm.assemble('addi $t5, $t6, 32767')
        self.assertEqual(self.asm.assembled_bytes, b'\x21\xcd\x7F\xFF')

    def test_addiu(self):
        self.asm.assemble('addiu $t5, $t6, 65500')
        self.assertEqual(self.asm.assembled_bytes, b'\x25\xcd\xFF\xDC')

    def test_lhi(self):
        self.asm.assemble('lhi $0, 0x12345678')
        self.assertEqual(self.asm.assembled_bytes, b'\x64\x00\x12\x34')

    def test_llo(self):
        self.asm.assemble('llo $0, 0x12345678')
        self.assertEqual(self.asm.assembled_bytes, b'\x60\x00\x56\x78')

    def test_lhi_llo_ffffffff(self):
        self.asm.assemble('lhi $0, 0xFFFFFFFF\nllo $0, 0xFFFFFFFF')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x64\x00\xFF\xFF\x60\x00\xFF\xFF')

    def test_lhi_llo_label(self):
        self.asm.assemble('lhi $0, end\nllo $0, end\n.org 0xffffffff\nend:')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x64\x00\xFF\xFF\x60\x00\xFF\xFF')

    def test_lhi_llo_label_too_far(self):
        self.asm.assemble('lhi $0, end\nllo $0, end\n.org 0xffffffff1\nend:')
        self.assertRaises(NotInBitRange, self.asm.link)

    def test_jump_too_far(self):
        self.asm.assemble('j end\n.org 0xffffffff1\nend:')
        self.assertRaises(NotInBitRange, self.asm.link)

    def test_jump(self):
        self.asm.assemble('j end\n.org 0xFFFFFFF\nend:')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\x0b\xFF\xFF\xFF')
