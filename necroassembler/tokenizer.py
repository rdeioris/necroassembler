'''Exposes the assembly source code tokenization features'''
from necroassembler.statements import Instruction, Directive, Label


class InvalidLabel(Exception):
    '''Raised when a label is specified after other tokens'''

    def __init__(self, tokenizer):
        super().__init__(
            'invalid label at line {0}'.format(tokenizer.line))


class Tokenizer:
    '''Builds a list of tokenized statements from assembly source code'''

    def __init__(self, case_sensitive=False, context=None):
        self.state = self._state_token
        self.current_token = ''
        self.statements = []
        self.tokens = []
        self.case_sensitive = case_sensitive
        self.line = 1
        self.context = context

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
                self.tokens.append('"' + self.current_token + '"')
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

    def _state_char(self, char):
        if char == '\\':
            self.state = self._state_escaped_char
            return
        if char == '\'':
            if self.current_token:
                self.tokens.append('\'' + self.current_token + '\'')
            self.current_token = ''
            self.state = self._state_token
            return
        self.current_token += char

    def _token_spaces(self, char):
        if self.current_token:
            self.tokens.append(self.current_token)
        self.current_token = ''
        if char in ('\n', '\r', ';'):
            if self.tokens:
                if self.tokens[0].startswith('.'):
                    self.statements.append(
                        Directive(self.tokens, self.line, self.context))
                else:
                    self.statements.append(
                        Instruction(self.tokens, self.line, self.context))
            self.tokens = []
            if char in (';',):
                self.state = self._state_comment
            else:
                self.state = self._state_token

    def _token_brackets(self, char):
        if self.current_token:
            self.tokens.append(self.current_token)
        self.tokens.append(char)
        self.current_token = ''

    def _token_colon(self):
        if self.tokens:
            raise InvalidLabel(self)
        if self.current_token:
            self.tokens.append(self.current_token)
        self.statements.append(
            Label(self.tokens, self.line, self.context))
        self.state = self._state_token
        self.current_token = ''
        self.tokens = []

    def _token_string(self):
        if self.current_token:
            self.tokens.append(self.current_token)
        self.current_token = ''
        self.state = self._state_string

    def _token_char(self):
        if self.current_token:
            self.tokens.append(self.current_token)
        self.current_token = ''
        self.state = self._state_char

    def _state_token(self, char):
        if char in (' ', '\n', '\r', '\t', ',', ';'):
            self._token_spaces(char)
            return
        if char in ('(', ')', '[', ']', '{', '}'):
            self._token_brackets(char)
            return
        if char == ':':
            self._token_colon()
            return
        if char == '"':
            self._token_string()
            return
        if char == '\'':
            self._token_char()
            return
        self.current_token += char

    def _state_comment(self, char):
        if char in ('\n', '\r'):
            self.state = self._state_token

    def parse(self, code):
        """Tokenizes a block of code

        :param str code: the source code to tokenize
        """
        # hack for avoiding losing the last statement
        code += '\n'
        for byte in code:
            if byte == '\n':
                self.line += 1
            self.step(byte)
