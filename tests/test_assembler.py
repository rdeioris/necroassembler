import unittest
from necroassembler import Assembler, opcode
from necroassembler.utils import pack_be32u, pack_bits
from necroassembler.exceptions import UnsupportedNestedMacro, NotInBitRange, UnknownLabel, NotInSignedBitRange
from necroassembler.statements import Instruction


class TestAssembler(unittest.TestCase):

    class AssemblerDumb(Assembler):
        hex_prefixes = ('0x', '$')
        hex_suffixes = ('h', )
        bin_prefixes = ('%', '0b')

        big_endian = True
        math_brackets = ('(', ')')

        @opcode('LOAD')
        def load(self, instr):
            value = self.parse_integer_or_label(
                instr.args[0], bits_size=32, size=4, offset=4)
            return pack_be32u(0xaabbccdd, value)

    def setUp(self):
        self.asm = self.AssemblerDumb()

    def test_label_and_directive(self):
        self.asm.assemble('data:  .db 0x17 ; hello world, i am a comment')
        self.assertEqual(self.asm.assembled_bytes, b'\x17')

    def test_math(self):
        self.asm.assemble('data: .db 1+2+3*4/5*2+1*3')
        self.assertEqual(self.asm.assembled_bytes, b'\x0A')

    def test_math_simple(self):
        self.asm.assemble('data: .db 1+4*3')
        self.assertEqual(self.asm.assembled_bytes, b'\x0D')

    def test_parse_integer(self):
        self.asm.assemble(
            '.db $17 + 5 + 0x08 - 08h +%1 - (0b1 << 3), 0x17, 0x22+$30+0x30, 1')
        self.assertEqual(self.asm.assembled_bytes, b'\x15\x17\x82\x01')

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

    def test_repeat_simple(self):
        self.asm.assemble('.repeat 2\ntest: .db 0x17\n.endrepeat')
        self.assertEqual(self.asm.assembled_bytes, b'\x17\x17')

    def test_repeat_label(self):
        self.asm.assemble(
            '.repeat 2\nLOAD test\ntest: .db 0x17\n.endrepeat')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xAA\xBB\xCC\xDD\x00\x00\x00\x08\x17\xAA\xBB\xCC\xDD\x00\x00\x00\x11\x17')

    def test_repeat(self):
        self.asm.assemble(
            '.repeat 5\ntest: .db 0x17\n.repeat 3\n.db 0x30\n.endrepeat\n .db 0x22\n.endrepeat')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x17\x30\x30\x30\x22\x17\x30\x30\x30\x22\x17\x30\x30\x30\x22\x17\x30\x30\x30\x22\x17\x30\x30\x30\x22')

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
        HELLO 1 2           3
        HELLO 1  2\t3
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
        .macro HELLO iterations
        foobar:
        .repeat iterations
        .db 1
        .endrepeat
        LOAD foobar
        .endmacro

        HELLO 1
        HELLO 2
        """
        self.asm.assemble(code)
        self.assertEqual(self.asm.assembled_bytes, b'\x01\xAA\xBB\xCC\xDD\x00\x00\x00\x00\x01\x01\xAA\xBB\xCC\xDD\x00\x00\x00\x00')

    def test_macro_with_labels_and_link(self):
        code = """
        .macro HELLO iterations
        .db 2
        foobar:
        .repeat iterations
        .db 1
        .endrepeat
        LOAD foobar
        .endmacro

        HELLO 1
        HELLO 2
        """
        self.asm.assemble(code)
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\x02\x01\xAA\xBB\xCC\xDD\x00\x00\x00\x01\x02\x01\x01\xAA\xBB\xCC\xDD\x00\x00\x00\x0B')

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
            NotInBitRange, self.asm.parse_integer, ['17'], 1, False)

    def test_parse_integer_signed_red(self):
        self.assertRaises(
            NotInSignedBitRange, self.asm.parse_integer, ['33'], 5, True)

    def test_parse_integer_unsigned(self):
        self.assertEqual(self.asm.parse_integer(['17'], 5, False), 17)

    def test_parse_integer_signed(self):
        self.assertEqual(self.asm.parse_integer(['-1000'], 11, True), -1000)

    def test_parse_integer_signed_edge(self):
        self.assertEqual(self.asm.parse_integer(['-1024'], 11, True), -1024)

    def test_parse_integer_signed_positive_edge(self):
        self.assertEqual(self.asm.parse_integer(['1023'], 11, True), 1023)

    def test_parse_integer_signed_too_low(self):
        self.assertRaises(
            NotInSignedBitRange, self.asm.parse_integer, ['-', '2049'], 11, True)

    def test_parse_integer_signed_too_high(self):
        self.assertRaises(
            NotInSignedBitRange, self.asm.parse_integer, ['2048'], 11, True)

    def test_parse_integer_signed_too_high_hex(self):
        self.assertRaises(
            NotInSignedBitRange, self.asm.parse_integer, ['0x800'], 11, True)

    def test_parse_integer_signed_edge_hex(self):
        self.assertEqual(self.asm.parse_integer(['0x7FF'], 11, True), -1)

    def test_parse_integer_signed_edge_hex_plus(self):
        self.assertEqual(self.asm.parse_integer(
            ['0x7FE', '+', '1'], 11, True), -1)

    def test_parse_integer_negative_hex(self):
        self.assertEqual(self.asm.parse_integer(['0xFF'], 8, True), -1)

    def test_parse_integer_negative_dec(self):
        self.assertEqual(self.asm.parse_integer(['-', '1'], 8, True), -1)

    def test_parse_integer_negative_dec_unsigned(self):
        self.assertEqual(self.asm.parse_integer(['-', '1'], 8, False), 255)

    def test_parse_integer_unsigned_edge_hex_plus(self):
        self.assertEqual(self.asm.parse_integer(
            ['0x7FE', '+', '1'], 11, False), 2047)

    def test_repeat10(self):
        self.asm.assemble('.repeat 10\n.db 0x17\n.endrepeat')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x17\x17\x17\x17\x17\x17\x17\x17\x17\x17')

    def test_complex_math(self):
        self.asm.assemble('.org 1\nstart:\n.org 10\nend:\n.db end-start-2')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\x07')

    def test_complex_math_triple(self):
        self.asm.assemble(
            '.org 1\nstart:\n.org 10\nend:\n.db end-start-2+start+start+1')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\x0A')

    def test_complex_math_wrong(self):
        self.asm.assemble(
            '.org 1\nstart:\n.org 10\nend:\n.db end-start-2+start+unknown+1')
        self.assertRaises(UnknownLabel, self.asm.link)

    def test_complex_math_multiply(self):
        self.asm.assemble(
            '.org 1\nstart:\n.org 10\nend:\n.db end-start-2+start+start+1*2')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\x0b')

    def test_complex_math_divide(self):
        self.asm.assemble(
            '.org 1\nstart:\n.org 10\nend:\n.db end-start-2+start+start+1/2')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\x09')

    def test_complex_math_bitmask(self):
        self.asm.assemble(
            '.define ONE 1\n.define TWO 2\n.define FOUR 4')
        self.asm.assemble('LOAD ONE|TWO|FOUR|8')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xAA\xBB\xCC\xDD\x00\x00\x00\x0F')

    def test_upto(self):
        self.asm.assemble('.org 1\n.upto 100')
        self.assertEqual(len(self.asm.assembled_bytes), 100)

    def test_upto_filled(self):
        self.asm.assemble('.org 1\n.db 0\n.upto 100')
        self.assertEqual(len(self.asm.assembled_bytes), 100)

    def test_upto_after_goto(self):
        self.asm.assemble('.org 1\n.db 0\n.org 10\n.upto 100')
        self.assertEqual(len(self.asm.assembled_bytes), 101)

    def test_instruction_match(self):
        statement = Instruction(self.asm, ['LOAD', ['X'], [[['Y', 'Z']]]], 1, None)
        statement.assemble()
        self.assertTrue(statement.match('X', [[['Y', 'Z']]]))
