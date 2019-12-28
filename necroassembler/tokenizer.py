'''Exposes the assembly source code tokenization features'''


class Tokenizer:
    '''Builds a list of tokenized lines from assembly source code'''

    spaces = (' ', '\r', '\t', '\n')
    escape_table = {'a': '\a', 'b': '\b', 'e': '\e', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t', 'v': '\v'}

    def __init__(self, args_splitter, interesting_symbols, special_symbols=(), case_sensitive=False, context=None):
        self.state = self._state_token
        self.current_token = ''
        self.current_arg = []
        self.statements = []
        self.case_sensitive = case_sensitive
        self.line = 1
        self.context = context
        self.args_splitter = args_splitter
        self.interesting_symbols = interesting_symbols
        self.special_symbols = special_symbols
        self.detected_label = False
        self.tokens = []

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
            else:
                self.current_token = '"'
            self._append()
            self.current_token = ''
            self.state = self._state_token
            return
        self.current_token += char

    def _state_escaped_string(self, char):
        self.current_token += self.escape_table.get(char, char)
        self.state = self._state_string

    def _state_escaped_char(self, char):
        self.current_token += self.escape_table.get(char, char)
        self.state = self._state_char

    def _state_multi_line_comment_prelude(self, char):
        if char != '*':
            if self.current_token:
                self._append()
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
            else:
                self.current_token == '\''
            self._append()
            self.state = self._state_token
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

    def _state_spaces(self, char):
        if char not in self.spaces:
            self.state = self._state_token
            self.state(char)

    def _token_spaces(self, char):
        if self.current_token:
            self._append()

        self.state = self._state_spaces

    def _token_string(self):
        if self.current_token:
            self._append()
        self.state = self._state_string

    def _token_char(self):
        if self.current_token:
            self._append()
        self.state = self._state_char

    def _token_single_line_comment(self, char):
        if self.current_token:
            self._append()
        self.state = self._state_single_line_comment

    def _token_letter(self, char):
        self.current_token += char

    def _token_slash(self, char):
        self.state = self._state_multi_line_comment_prelude

    def _append(self):
        self.current_arg.append(self.current_token)
        self.current_token = ''

    def _state_token(self, char):
        if self.args_splitter and char in self.args_splitter:
            if self.current_token:
                self._append()
            if self.current_arg:
                self.tokens.append(self.current_arg)
            self.current_arg = []
            return

        if self.special_symbols and char in self.special_symbols:
            if self.current_token:
                self._append()
            if self.current_arg:
                self.tokens.append(self.current_arg)
            self.current_arg = []
            self.current_token = char
            self._append()
            self.tokens.append(self.current_arg)
            self.current_arg = []
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

        if char in self.interesting_symbols:
            if self.current_token:
                self._append()
            self.current_token = char
            self._append()
            return

        self._token_letter(char)

    def _state_comment(self, char):
        if char in ('\n', '\r'):
            self.state = self._state_token

    def _reset(self):

        # manage uncompleted string
        if self.state  == self._state_char:
            self.current_token += '\''
        elif self.state  == self._state_string:
            self.current_token += '"'

        if self.current_token:
            self._append()
        if self.current_arg:
            self.tokens.append(self.current_arg)
        # now extract command (and label eventually)
        if self.tokens and self.tokens[0]:
            if self.tokens[0][0]:
                self.tokens.insert(0, self.tokens[0][0])
                del(self.tokens[1][0])
                if not self.tokens[1]:
                    del(self.tokens[1])
            # command ends with ':' ?
            if self.tokens[0].endswith(':'):
                if len(self.tokens) > 1 and self.tokens[1] and self.tokens[1][0]:
                    self.statements.append((self.line, [self.tokens[0]]))
                    self.tokens[0] = self.tokens[1][0]
                    del(self.tokens[1][0])
                    if not self.tokens[1]:
                        del(self.tokens[1])
            # command contains ':'
            elif ':' in self.tokens[0]:
                label, command = self.tokens[0].split(':', 1)
                self.statements.append((self.line, [label + ':']))
                self.tokens[0] = command

            if self.tokens:
                self.statements.append((self.line, self.tokens))
            
        self.current_arg = []
        self.current_token = ''
        self.tokens = []
        self.line += 1

    def parse(self, code):
        """Tokenizes a block of code

        :param str code: the source code to tokenize
        """

        # hack for avoiding losing the last statement
        code += '\n'
        for char in code:
            if char == '\n':
                self._reset()
            self.step(char)
