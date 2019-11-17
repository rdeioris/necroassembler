'''Exposes the assembly source code tokenization features'''
import string


class Tokenizer:
    '''Builds a list of tokenized lines from assembly source code'''

    spaces = (' ', '\r', '\t', '\n')

    def __init__(self, args_splitter, case_sensitive=False, context=None):
        self.state = self._state_token
        self.current_token = ''
        self.current_token_index = 0
        self.lines = []
        self.tokens = [[]]
        self.case_sensitive = case_sensitive
        self.line = 1
        self.context = context
        self.args_splitter = args_splitter
        self.initial_index = 0

    def step(self, char):
        """Advances the Tokenizer State Machine

        :param str char:  the character that will be passed to the State Machine

        """
        self.state(char)

    def _state_string(self, char):
        if char == '\\':
            self.state = self._state_escaped_string
            return
        if char == '"':
            if self.current_token:
                self.current_token = '"{0}"'.format(self.current_token)
                self._append()
            self.current_token = ''
            self.state = self._state_token
            return
        self.current_token += char

    def _state_escaped_string(self, char):
        self.current_token += char
        self.state = self._state_string

    def _state_escaped_char(self, char):
        self.current_token += char
        self.state = self._state_char

    def _state_multi_line_comment_prelude(self, char):
        if char != '*':
            self.current_token = '/'
            self._append()
            self.current_token = ''
            self.state = self._state_token
            self._state_token(char)
            return
        self.state = self._state_multi_line_comment

    def _state_char(self, char):
        if char == '\\':
            self.state = self._state_escaped_char
            return
        if char == '\'':
            if self.current_token:
                self.current_token = '\'{0}\''.format(self.current_token)
            self.current_token = ''
            self.state = self._state_token
            return
        self.current_token += char

    def _state_letter(self, char):
        if char not in string.ascii_letters + string.digits + '_':
            if self.current_token:
                self._append()
            self.current_token = ''
            self.state = self._state_token
            self._state_token(char)
            return
        self.current_token += char

    def _state_single_line_comment(self, char):
        if char == '\n':
            self.state = self._state_token

    def _state_multi_line_comment_postlude(self, char):
        if char == '/':
            self.state = self._state_token
            return
        self.state = self._state_multi_line_comment

    def _state_multi_line_comment(self, char):
        if char == '*':
            self.state = self._state_multi_line_comment_postlude

    def _token_spaces(self, char):
        if self.current_token:
            self._append()
        self.current_token = ''
        if self.current_token_index == self.initial_index and self.tokens[self.initial_index]:
            self._add_arg()
        if char not in self.spaces:
            self.state = self._state_token

    def _token_string(self):
        if self.current_token:
            self._append()
        self.current_token = ''
        self.state = self._state_string

    def _token_char(self):
        if self.current_token:
            self._append()
        self.current_token = ''
        self.state = self._state_char

    def _token_single_line_comment(self, char):
        if self.current_token:
            self._append()
        self.current_token = ''
        self.state = self._state_single_line_comment

    def _token_letter(self, char):
        if self.current_token:
            self._append()
        self.current_token = char
        self.state = self._state_letter

    def _token_slash(self, char):
        self.state = self._state_multi_line_comment_prelude

    def _add_arg(self):
        if self.current_token:
            self._append()
            self.current_token = ''
        self.tokens.append([])
        self.current_token_index = len(self.tokens) - 1

    def _append(self):
        self.tokens[self.current_token_index].append(self.current_token)

    def _state_token(self, char):
        if char in self.args_splitter:
            self._add_arg()
            return

        if char in self.spaces:
            self._token_spaces(char)
            return

        if char == '/':
            self._token_slash(char)
            return

        if char == ';':
            self._token_single_line_comment(char)
            return

        if char == '"':
            self._token_string()
            return

        if char == '\'':
            self._token_char()
            return

        if char in string.ascii_letters + string.digits + '_':
            self._token_letter(char)
            return

        if self.current_token:
            self._append()

        self.current_token = char
        self._append()
        self.current_token = ''

        # special case for supporting labels on the same line of instruction and directives
        if self.current_token_index == 0 and char == ':':
            self._add_arg()
            self.initial_index = 1

    def _state_comment(self, char):
        if char in ('\n', '\r'):
            self.state = self._state_token

    def _reset(self):
        if self.current_token:
            self._append()
        if self.tokens[0]:
            self.lines.append((self.line, self.tokens))
        self.tokens = [[]]
        self.current_token = ''
        self.current_token_index = 0
        self.initial_index = 0
        self.line += 1

    def parse(self, code):
        """Tokenizes a block of code

        :param str code: the source code to tokenize
        """
        # hack for avoiding losing the last statement
        code += '\n'
        for byte in code:
            if byte == '\n':
                self._reset()
            self.step(byte)
