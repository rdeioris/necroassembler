import unittest
from necroassembler import Assembler, opcode
from necroassembler.utils import pack_be32u, pack_bits
from necroassembler.exceptions import UnsupportedNestedMacro, LabelNotAllowedInMacro, NotInBitRange


class TestAssembler(unittest.TestCase):

    class AssemblerDumb(Assembler):
        hex_prefixes = ('0x',)

        big_endian = True

        @opcode('LOAD')
        def load(self, instr):
            arg = instr.tokens[1]
            value = self.parse_integer(instr.tokens[1], 32, signed=False)
            # label ?
            if value is None:
                self.add_label_translation(label=arg, bits_size=32, size=4)
                return pack_be32u(0xaabbccdd, 0)
            return pack_be32u(0xaabbccdd, value)

    def setUp(self):
        self.asm = self.AssemblerDumb()

    def test_assemble(self):
        self.asm.assemble('LOAD 0x12345678')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xAA\xBB\xCC\xDD\x12\x34\x56\x78')

    def test_assemble_db(self):
        self.asm.assemble('  .db 0x17 ; hello world, i am a comment')
        self.assertEqual(self.asm.assembled_bytes, b'\x17')

    def test_assemble_dd(self):
        self.asm.assemble('  .dd 0x11223344 ; hello world, i am a comment')
        self.assertEqual(self.asm.assembled_bytes, b'\x11\x22\x33\x44')

    def test_override(self):
        class AssemblerDumber(Assembler):
            pass
        dumber = AssemblerDumber()
        dumber.defines = {'foo': 'bar'}
        self.assertFalse('foo' in Assembler.defines)

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

    def test_macro_with_labels(self):
        code = """
        .macro HELLO
        foobar:
        .endmacro
        """
        self.assertRaises(LabelNotAllowedInMacro, self.asm.assemble, code)

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
                                   ((2, 0), -2),
                                   ((10, 7), 15)
                                   ), 0b11110000110)

    def test_ram(self):
        self.asm.assemble("""
        .org 0x1000
        one: .ram 2
        two: .ram 4
        three: .ram 8
        end:
        """)
        self.assertEqual(
            self.asm.get_label_absolute_address_by_name('one'), 0x1000)
        self.assertEqual(
            self.asm.get_label_absolute_address_by_name('two'), 0x1002)
        self.assertEqual(
            self.asm.get_label_absolute_address_by_name('three'), 0x1006)
        self.assertEqual(
            self.asm.get_label_absolute_address_by_name('end'), 0x100e)
        self.assertEqual(len(self.asm.assembled_bytes), 0)

    def test_parse_integer_unsigned_red(self):
        self.assertRaises(
            NotInBitRange, self.asm.parse_integer, '17', 1, False)

    def test_parse_integer_signed_red(self):
        self.assertRaises(
            NotInBitRange, self.asm.parse_integer, '17', 5, True)

    def test_parse_integer_unsigned(self):
        self.assertEqual(self.asm.parse_integer('17', 5, False), 17)

    def test_parse_integer_signed(self):
        self.assertEqual(self.asm.parse_integer('-1000', 11, True), -1000)

    def test_parse_integer_signed_edge(self):
        self.assertEqual(self.asm.parse_integer('-1024', 11, True), -1024)

    def test_parse_integer_signed_positive_edge(self):
        self.assertEqual(self.asm.parse_integer('1023', 11, True), 1023)

    def test_parse_integer_signed_too_low(self):
        self.assertRaises(
            NotInBitRange, self.asm.parse_integer, '-1025', 11, True)

    def test_parse_integer_signed_too_high(self):
        self.assertRaises(
            NotInBitRange, self.asm.parse_integer, '1024', 11, True)

    def test_parse_integer_signed_too_high_hex(self):
        self.assertRaises(
            NotInBitRange, self.asm.parse_integer, '0x800', 11, True)

    def test_parse_integer_signed_edge_hex(self):
        self.assertEqual(self.asm.parse_integer('0x7FF', 11, True), 2047)

    def test_parse_integer_signed_edge_hex_plus(self):
        self.assertEqual(self.asm.parse_integer('0x7FE+', 11, True), 2047)

    def test_parse_integer_unsigned_edge_hex_plus(self):
        self.assertEqual(self.asm.parse_integer('0x7FE+', 11, True), 2047)
