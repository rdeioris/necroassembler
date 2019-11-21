import unittest
from necroassembler.tokenizer import Tokenizer


class TestTokenizer(unittest.TestCase):

    def setUp(self):
        self.tokenizer = Tokenizer(
            args_splitter=',',
            group_pairs=(('(', ')'), ('[', ']'), ('{', '}')),
            interesting_symbols=('+', '-', '>', '<', '*', '/'))

    def test_parser_comment(self):
        self.tokenizer.parse('  .db 0x17 ; hello world, i am a comment')
        self.assertEqual(len(self.tokenizer.lines), 1)
        self.assertEqual(self.tokenizer.lines[0], (1, ['.db', ['0x17']]))

    def test_parser_string(self):
        self.tokenizer.parse('.ascii "hell\\"o",1,2,3')
        self.assertEqual(self.tokenizer.lines[0], (1, [
                         '.ascii', ['"hell"o"'], ['1'], ['2'], ['3']]))

    def test_parser_string_no_splitargs(self):
        self.tokenizer.parse('one two three')
        self.assertEqual(self.tokenizer.lines[0], (1, [
                         'one', ['two', 'three']]))

    def test_parser_string_complex(self):
        self.tokenizer.parse('one two + (three >> 8) + 5, foo + 2')
        self.assertEqual(self.tokenizer.lines[0], (1, [
                         'one', ['two', '+', ['three', '>', '>', '8'], '+', '5'], ['foo', '+', '2']]))

    def test_parser_multi_line_comment_inline(self):
        self.tokenizer.parse('  .db 0x17 /* nothing  */, 2 ,3')
        self.assertEqual(self.tokenizer.lines[0], (1, [
                         '.db', ['0x17'], ['2'], ['3']]))

    def test_parser_multi_line_comment(self):
        self.tokenizer.parse(
            '  .db 0x17 /* \ntest\ntest2\ntest 3 4 5 */ .db 0x22')
        self.assertEqual(
            self.tokenizer.lines[0], (1, ['.db', ['0x17']]))
        self.assertEqual(
            self.tokenizer.lines[1], (4, ['.db', ['0x22']]))

    def test_parser_inline_label(self):
        self.tokenizer.parse('dummy: hello world')
        self.assertEqual(self.tokenizer.lines[0], (1, [
                         ['dummy', ':'], ['hello'], ['world']]))

    def test_parser_inline_label_no_space(self):
        self.tokenizer.parse('dummy:hello world')
        self.assertEqual(self.tokenizer.lines[0], (1, [
                         'dummy:', 'hello', ['world']]))

    def test_parser_dot_instruction(self):
        self.tokenizer.parse('move.b hello world, foobar')
        self.assertEqual(self.tokenizer.lines[0], (1, [
                         ['move', '.', 'b'], ['hello', 'world'], ['foobar']]))

    def test_parser_dot_instruction_complex(self):
        self.tokenizer.parse('move.b hello world test001+2, foobar, 3')
        self.assertEqual(self.tokenizer.lines[0], (1, [
                         ['move', '.', 'b'], ['hello', 'world', 'test001', '+', '2'], ['foobar'], ['3']]))

    def test_parser_symbols(self):
        self.tokenizer.parse('FOO $hello$world, 1 2 $foo!bar, hello world')
        self.assertEqual(self.tokenizer.lines[0], (1, [
                         'FOO', ['$hello$world'], ['1', '2', '$foo!bar'], ['hello', 'world']]))

    def test_parser_6502_ind_x(self):
        self.tokenizer.parse('LDA ($44, X)')
        self.assertEqual(
            self.tokenizer.lines[0], (1, ['LDA', [['$44'], ['X']]]))

    def test_parser_6502_ind_y(self):
        self.tokenizer.parse('LDA ($44), Y')
        self.assertEqual(
            self.tokenizer.lines[0], (1, ['LDA', [['$44']], ['Y']]))

    def test_parser_6502_zp_x(self):
        self.tokenizer.parse('LDA $44, X')
        self.assertEqual(
            self.tokenizer.lines[0], (1, ['LDA', ['$44'], ['X']]))

    def test_parser_m68k_pre_dec(self):
        self.tokenizer.parse('MOVE.b d0, -(a0)')
        self.assertEqual(
            self.tokenizer.lines[0], (1, ['MOVE.b', ['d0'], ['-', ['a0']]]))

    def test_parser_m68k_indirect_disp(self):
        self.tokenizer.parse('MOVE.b d0, (1+( 2+3)*(10/(2* 3)), a0)')
        self.assertEqual(
            self.tokenizer.lines[0], (1, ['MOVE.b', ['d0'], [['1', '+', ['2', '+', '3'], '*', ['10', '/', ['2', '*', '3']]], ['a0']]]))
