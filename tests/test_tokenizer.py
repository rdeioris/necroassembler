import unittest
from necroassembler.tokenizer import Tokenizer


class TestTokenizer(unittest.TestCase):

    def setUp(self):
        self.tokenizer = Tokenizer()

    def test_parser_comment(self):
        self.tokenizer.parse('  .db 0x17 ; hello world, i am a comment')
        self.assertEqual(len(self.tokenizer.statements), 1)

    def test_parser_string(self):
        self.tokenizer.parse('.ascii "hell\\"o",1,2,3')
        self.assertEqual(self.tokenizer.statements[0].tokens, ['.ascii', '"hell"o"', '1', '2', '3'])
