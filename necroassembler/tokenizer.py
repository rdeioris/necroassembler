'''Exposes the assembly source code tokenization features'''


class Tokenizer:
    '''Builds a list of tokenized lines from assembly source code'''

    spaces = (' ', '\r', '\t', '\n')

    def __init__(self, args_splitter, group_pairs, interesting_symbols, special_symbols=(), case_sensitive=False, context=None):
        self.state = self._state_token
        self.current_token = ''
        self.current_token_index = 0
        self.statements = []
        self.case_sensitive = case_sensitive
        self.line = 0  # will be incremented by reset
        self.context = context
        self.args_splitter = args_splitter
        self.interesting_symbols = interesting_symbols
        self.group_pairs = group_pairs
        self.special_symbols = special_symbols
        self.detected_label = False
        self.elements_stack = []

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
            self.current_token = ''
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
        if self.detected_label and self.elements_stack[-1]:
            self._fix_label()

        self.state = self._state_spaces

    def _fix_label(self):
        self.detected_label = False
        additional = ''
        if len(self.elements_stack[-1]) > 1:
            additional = self.elements_stack[-1][1]
        self._pop_arg()
        self._push_arg()
        self.current_token = additional
        if self.current_token:
            self._append()

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

    def _push_arg(self):
        if self.current_token:
            self._append()
        self.elements_stack.append([])

    def _pop_arg(self):
        if self.current_token:
            self._append()

        element = self.elements_stack.pop()
        if element:
            self.elements_stack[-1].append(element)

    def _append(self):
        self.elements_stack[-1].append(self.current_token)
        self.current_token = ''
        self.current_token_index += 1

    def _state_token(self, char):
        if self.args_splitter and char in self.args_splitter:
            self._pop_arg()
            self._push_arg()
            return

        if self.special_symbols and char in self.special_symbols:
            self._pop_arg()
            self._push_arg()
            self.current_token = char
            self._append()
            self._pop_arg()
            self._push_arg()
            return

        if self.group_pairs and char in [_open for _open, _ in self.group_pairs]:
            self._push_arg()
            return

        if self.group_pairs and char in [_close for _, _close in self.group_pairs]:
            self._pop_arg()
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

        # special case for supporting labels on the same line of instruction and directives
        if self.current_token_index == 0 and char == ':':
            self.current_token += char
            self._append()
            self.detected_label = True
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
        if self.current_token:
            self._append()
        # hack for spaceless label
        if self.detected_label and self.elements_stack[-1]:
            additional = self.elements_stack[-1][0][1]
            del(self.elements_stack[-1][0][1])
            self.elements_stack[-1].insert(1, [additional])
        while len(self.elements_stack) > 1:
            self.elements_stack.pop()
        if self.elements_stack and self.elements_stack[0]:
            tokens = self.elements_stack[0]
            if tokens[0][0]:
                # special case, label followed by instruction
                if tokens[0][0].endswith(':') and len(tokens) > 1:
                    self.statements.append((self.line, [tokens[0][0]]))
                    del(tokens[0])
                tokens.insert(0, tokens[0][0])

                del(tokens[1][0])
                if not tokens[1]:
                    del(tokens[1])
                self.statements.append((self.line, tokens))
        self.current_token = ''
        self.current_token_index = 0
        self.line += 1
        self.elements_stack = []
        self.detected_label = False
        self._push_arg()
        self._push_arg()

    def parse(self, code):
        """Tokenizes a block of code

        :param str code: the source code to tokenize
        """

        self._reset()

        # hack for avoiding losing the last statement
        code += '\n'
        for char in code:
            if char == '\n':
                self._pop_arg()
                self._reset()
            self.step(char)
