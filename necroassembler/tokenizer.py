
from necroassembler.statements import Instruction, Directive, Label


class Tokenizer:

    class InvalidLabel(Exception):
        def __init__(self, tokenizer):
            super().__init__(
                'invalid label at line {0}'.format(tokenizer.line))

    def __init__(self, case_sensitive=False, context=None):
        self.state = self.token
        self.current_token = ''
        self.statements = []
        self.tokens = []
        self.case_sensitive = case_sensitive
        self.line = 1
        self.context = context

    def step(self, char):
        self.state(char)

    def string(self, char):
        if char == '\\':
            self.state = self.escaped_string
            return
        if char == '"':
            if self.current_token:
                self.tokens.append('"' + self.current_token + '"')
            self.current_token = ''
            self.state = self.token
            return
        self.current_token += char

    def escaped_string(self, char):
        self.current_token += char
        self.state = self.string

    def escaped_char(self, char):
        self.current_token += char
        self.state = self.char

    def char(self, char):
        if char == '\\':
            self.state = self.escaped_char
            return
        if char == '\'':
            if self.current_token:
                self.tokens.append('\'' + self.current_token + '\'')
            self.current_token = ''
            self.state = self.token
            return
        self.current_token += char

    def token(self, char):
        if char in (' ', '\n', '\r', '\t', ',', ';'):
            if self.current_token:
                self.tokens.append(self.current_token)
            self.current_token = ''
            if char in ('\n', '\r', ';'):
                if len(self.tokens) > 0:
                    if (self.tokens[0].startswith('.')):
                        self.statements.append(
                            Directive(self.tokens, self.line, self.context))
                    else:
                        self.statements.append(
                            Instruction(self.tokens, self.line, self.context))
                self.tokens = []
                if char in (';',):
                    self.state = self.comment
                else:
                    self.state = self.token
            return
        if char in ('(', ')', '[', ']', '{', '}'):
            if self.current_token:
                self.tokens.append(self.current_token)
            self.tokens.append(char)
            self.current_token = ''
            return
        if char == ':':
            if len(self.tokens) > 0:
                raise Tokenizer.InvalidLabel(self)
            if self.current_token:
                self.tokens.append(self.current_token)
            self.statements.append(
                Label(self.tokens, self.line, self.context))
            self.state = self.token
            self.current_token = ''
            self.tokens = []
            return
        if char == '"':
            if self.current_token:
                self.tokens.append(self.current_token)
            self.current_token = ''
            self.state = self.string
            return
        if char == '\'':
            if self.current_token:
                self.tokens.append(self.current_token)
            self.current_token = ''
            self.state = self.char
            return
        self.current_token += char

    def comment(self, char):
        if char in ('\n', '\r'):
            self.state = self.token
        return

    def parse(self, code):
        # hack for avoiding losing the last statement
        code += '\n'
        for b in code:
            if b == '\n':
                self.line += 1
            self.step(b)
