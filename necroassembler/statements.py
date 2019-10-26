from necroassembler.exceptions import (InvalidOpCodeArguments, UnknownInstruction, LabelNotAllowedInMacro,
                                       InvalidInstruction, UnknownDirective, LabelAlreadyDefined, InvalidLabel, AssemblerException)
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
            try:
                blob = instruction(self)
                if blob is None:
                    # do not add 'self' here, will be added in the exception
                    raise InvalidInstruction()
            except AssemblerException as exc:
                # trick for adding more infos to the exception
                exc.args = (exc.args[0] + ' ' + str(self),)
                raise exc from None
        else:
            if len(self.tokens) != 1:
                raise InvalidOpCodeArguments(self)
            blob = instruction
        assembler.append_assembled_bytes(blob)

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
        if assembler.macro_recording is not None:
            raise LabelNotAllowedInMacro(self)
        key = self.tokens[0]
        if key in assembler.labels:
            raise LabelAlreadyDefined(self)
        if key in ('>', '<', '-', '+'):
            raise InvalidLabel(self)
        if assembler.parse_integer(key, 64, False) is not None:
            raise InvalidLabel(self)
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
