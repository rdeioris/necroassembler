import unittest
from necroassembler import Assembler, opcode
from necroassembler.utils import pack_be32u, pack_bits
from necroassembler.exceptions import UnsupportedNestedMacro


class TestAssembler(unittest.TestCase):

    class DumbAssembler(Assembler):
        hex_prefixes = ('0x',)

        @opcode('LOAD')
        def load(self, instr):
            arg = instr.tokens[1]
            value = self.parse_integer(instr.tokens[1])
            # label ?
            if value is None:
                self.add_label_translation(label=arg, size=4)
                return pack_be32u(0xaabbccdd, 0)
            return pack_be32u(0xaabbccdd, value)

    def setUp(self):
        self.asm = self.DumbAssembler()

    def test_assemble(self):
        self.asm.assemble('LOAD 0x12345678')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xAA\xBB\xCC\xDD\x12\x34\x56\x78')

    def test_assemble_db(self):
        self.asm.assemble('  .db 0x17 ; hello world, i am a comment')
        self.assertEqual(self.asm.assembled_bytes, b'\x17')

    def test_macro_simple(self):
        self.asm.assemble("""
        .macro HELLO
        LOAD 1
        LOAD 2
        LOAD 3
        .endmacro
        HELLO
        HELLO
        """)
        opcode = b'\xAA\xBB\xCC\xDD'
        arg1 = b'\x00\x00\x00\x01'
        arg2 = b'\x00\x00\x00\x02'
        arg3 = b'\x00\x00\x00\x03'
        self.assertEqual(self.asm.assembled_bytes,
                         (opcode+arg1+opcode+arg2+opcode+arg3) * 2)

    def test_macro_args(self):
        self.asm.assemble("""
        .macro HELLO arg0 arg1 arg2
        LOAD arg0
        LOAD arg1
        LOAD arg2
        .endmacro
        HELLO 1 2 3
        HELLO 1,2,3
        HELLO,1,2 3
        """)
        opcode = b'\xAA\xBB\xCC\xDD'
        arg1 = b'\x00\x00\x00\x01'
        arg2 = b'\x00\x00\x00\x02'
        arg3 = b'\x00\x00\x00\x03'
        self.assertEqual(self.asm.assembled_bytes,
                         (opcode+arg1+opcode+arg2+opcode+arg3) * 3)

    def test_macro_nested(self):
        code = """
        .macro HELLO
        .macro NESTED
        .endmacro
        .endmacro
        """
        self.assertRaises(UnsupportedNestedMacro, self.asm.assemble, code)

    def test_pack_bits(self):
        self.assertEqual(pack_bits(0b00000000000,
                                   ((2, 0), 3),
                                   ((10, 7), 15)
                                   ), 0b11110000011)

    def test_pack_bits_bigger_base(self):
        self.assertEqual(pack_bits(0b100000000000,
                                   ((2, 0), 3),
                                   ((10, 7), 15),
                                   ((4, 4), 1),
                                   ), 0b111110010011)

    def test_pack_bits_signed(self):
        self.assertEqual(pack_bits(0b00000000000,
                                   ((2, 0), -2, True),
                                   ((10, 7), 15)
                                   ), 0b11110000110)
