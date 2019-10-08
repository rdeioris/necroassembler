class Statement:
    def __init__(self, tokens):
        self.tokens = tokens

    def __str__(self):
        return self.__class__.__name__ + ' ' + str(self.tokens)


class Instruction(Statement):
    def assemble(self, assembler):
        key = self.tokens[0]
        if not assembler.case_sensitive:
            key = key.upper()
        if not key in assembler.instructions:
            raise Exception('unknown instruction')
        instruction = assembler.instructions[key]
        if callable(instruction):
            blob = instruction(self.tokens)
        else:
            blob = instruction
        assembler.assembled_bytes += blob
        assembler.org_counter += len(blob)


class Label(Statement):
    def assemble(self, assembler):
        key = self.tokens[0]
        if key in assembler.labels:
            raise Exception('label already defined')
        if assembler.parse_integer(key) is not None:
            raise Exception('invalid label')
        assembler.labels[key] = {
            'base': assembler.org_counter, 'org': assembler.current_org}


class Directive(Statement):
    def assemble(self, assembler):
        key = self.tokens[0][1:]
        if not assembler.case_sensitive:
            key = key.upper()
        if not key in assembler.directives:
            raise Exception('unknown directive')
        assembler.directives[key](self.tokens)


class Tokenizer:

    def __init__(self, case_sensitive=False):
        self.state = self.unknown
        self.current_token = ''
        self.statements = []
        self.tokens = []
        self.case_sensitive = case_sensitive

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
            self.state = self.unknown
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
            self.state = self.unknown
            return
        self.current_token += char

    def token(self, char):
        if char in (' ', '\n', '\r', '\t', ',', ';'):
            if self.current_token:
                self.tokens.append(self.current_token)
            self.current_token = ''
            if char in ('\n', '\r', ';'):
                if (self.tokens[0].startswith('.')):
                    self.statements.append(
                        Directive(self.tokens))
                else:
                    self.statements.append(
                        Instruction(self.tokens))
                self.tokens = []
                if char in (';',):
                    self.state = self.comment
                else:
                    self.state = self.unknown
            return
        if char in ('(', ')', '[', ']', '{', '}'):
            if self.current_token:
                self.tokens.append(self.current_token)
            self.tokens.append(char)
            self.current_token = ''
            return
        if char == ':':
            if len(self.tokens) > 0:
                raise Exception('invalid label definition')
            if self.current_token:
                self.tokens.append(self.current_token)
            self.statements.append(Label(self.tokens))
            self.state = self.unknown
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
            self.state = self.unknown
        return

    def unknown(self, char):
        if char in (' ', '\n', '\r', '\t', ','):
            return
        if char in (';'):
            self.state = self.comment
            return
        self.state = self.token
        self.current_token += char

    def parse(self, code):
        # hack for avoiding losing the last statement
        code += '\n'
        for b in code:
            self.step(b)
