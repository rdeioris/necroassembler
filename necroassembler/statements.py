from necroassembler.exceptions import InvalidOpCodeArguments, UnknownInstruction, InvalidInstruction, UnknownDirective
from necroassembler.utils import substitute_with_dict


class Statement:
    def __init__(self, tokens, line, context):
        self.tokens = tokens
        self.line = line
        self.context = context

    def __str__(self):
        if self.context is not None:
            return 'at line {1} of {0}: {2}'.format(self.context, self.line, str(self.tokens))
        return 'at line {0}: {1}'.format(self.line, str(self.tokens))


class Instruction(Statement):
    def assemble(self, assembler):
        # first check if we are in macro recording mode
        if assembler.macro_recording is not None:
            macro = assembler.macro_recording
            macro.add_instruction(self)
            return

        substitute_with_dict(self.tokens, assembler.defines, 0,
                             assembler.special_prefixes, assembler.special_suffixes)

        key = self.tokens[0]
        if not assembler.case_sensitive:
            key = key.upper()

        if key in assembler.macros:
            macro = assembler.macros[key]
            macro.assemble(assembler, self.tokens)
            return

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

    def match(self, *args, start=1):
        if (len(self.tokens) - start) != len(args):
            return False
        for index, pattern in enumerate(args):
            if pattern is None:
                continue
            if callable(pattern):
                if pattern(self.tokens[index+1]):
                    continue
            else:
                if isinstance(pattern, str):
                    if self.tokens[index + start].upper() == pattern.upper():
                        continue
                if any([self.tokens[index + start].upper() == x.upper() for x in pattern]):
                    continue
            return False
        return True

    def apply(self, *args, start=1):
        out = []
        for index, arg in enumerate(args):
            if arg is not None:
                out.append(arg(self.tokens[index + start]))
        return out


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
        # skip directive for defines substitution
        substitute_with_dict(self.tokens, assembler.defines, 1)
        key = self.tokens[0][1:]
        if not assembler.case_sensitive:
            key = key.upper()
        if not key in assembler.directives:
            raise UnknownDirective(self)
        assembler.directives[key](self)
