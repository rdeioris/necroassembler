import unittest
from necroassembler import Assembler, opcode, pack_be_32s


class TestAssembler(unittest.TestCase):

    class DumbAssembler(Assembler):
        hex_prefixes = ('0x',)

        @opcode('LOAD')
        def load(self, tokens):
            arg = tokens[1]
            value = self.parse_integer(tokens[1])
            # label ?
            if value is None:
                self.add_label_translation(label=arg, size=4, pack='>I')
                return pack_be_32s(0xaabbccdd, 0)
            return pack_be_32s(0xaabbccdd, value)

    def setUp(self):
        self.asm = self.DumbAssembler()

    def test_assemble(self):
        self.asm.assemble('LOAD 0x12345678')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xAA\xBB\xCC\xDD\x12\x34\x56\x78')

    def test_assemble_db(self):
        self.asm.assemble('  .db 0x17 ; hello world, i am a comment')
        self.assertEqual(self.asm.assembled_bytes, b'\x17')
