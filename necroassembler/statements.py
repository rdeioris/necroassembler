from necroassembler.exceptions import InvalidOpCodeArguments, UnknownInstruction, InvalidInstruction


class Statement:
    def __init__(self, tokens, line, context):
        self.tokens = tokens
        self.line = line
        self.context = context

    def __str__(self):
        if self.context is not None:
            return '{0} at line {1}: {2}'.format(self.context, self.line, str(self.tokens))
        return 'line {0}: {1}'.format(self.line, str(self.tokens))


class Instruction(Statement):
    def assemble(self, assembler):
        key = self.tokens[0]
        if not assembler.case_sensitive:
            key = key.upper()
        if not key in assembler.instructions:
            raise UnknownInstruction(self)
        instruction = assembler.instructions[key]
        if callable(instruction):
            blob = instruction(self)
            if blob is None:
                raise InvalidInstruction(self)
        else:
            if len(self.tokens) != 1:
                raise InvalidOpCodeArguments(self)
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
        assembler.directives[key](self)
