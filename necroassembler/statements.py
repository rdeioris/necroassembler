from necroassembler.exceptions import (InvalidOpCodeArguments, UnknownInstruction, LabelNotAllowedInMacro,
                                       InvalidInstruction, UnknownDirective, LabelAlreadyDefined, InvalidLabel, AssemblerException)
from necroassembler.utils import is_valid_label


class Scope:

    def __init__(self, assembler):
        self.assembler = assembler
        self.labels = {}
        # this gets a meaningful value only after pushing
        self.parent = None

    def add_label(self, label):
        if label in self.labels:
            raise LabelAlreadyDefined()
        self.labels[label] = {
            'scope': self.assembler.get_current_scope(),
            'base': self.assembler.org_counter,
            'org': self.assembler.current_org,
            'section': self.assembler.current_section}


class Statement:
    def __init__(self, assembler, tokens, line, context):
        self.assembler = assembler
        self.tokens = tokens
        self.line = line
        self.context = context
        self.arg_index = 1
        self.cleaned_tokens = []

    def __str__(self):
        if self.context is not None:
            return 'at line {1} of {0}: {2}'.format(self.context, self.line, str(self.tokens))
        return 'at line {0}: {1}'.format(self.line, str(self.tokens))

    @property
    def args(self):
        return self.cleaned_tokens[1:]

    @property
    def command(self):
        return self.cleaned_tokens[0]

    def clean_tokens(self):
        self.cleaned_tokens = []
        for token in self.tokens:
            new_elements = []
            for element in token:
                anti_loop_check = []
                while element not in anti_loop_check:
                    if element not in self.assembler.defines:
                        break
                    anti_loop_check.append(element)
                    element = self.assembler.defines[element]
                new_elements.append(element)
            self.cleaned_tokens.append(new_elements)

    def assemble(self):
        # first of all: rebuild using defines
        self.clean_tokens()

        # check for labels
        if self.cleaned_tokens[0][-1] == ':':
            label = ''.join(self.cleaned_tokens[0][:-1])
            if is_valid_label(label):
                self.assembler.get_current_scope().add_label(label)
            else:
                raise InvalidLabel(label)
            # after a label, directives and instructions are allowed so pop the zero one
            self.cleaned_tokens.pop(0)
            # fast exit if no relevant data remain
            if not self.cleaned_tokens[0]:
                return

        # now check for directives
        if self.cleaned_tokens[0][0] == '.':
            directive = ''.join(self.cleaned_tokens[0][1:])
            if not self.assembler.case_sensitive:
                directive = directive.upper()
            if not directive in self.assembler.directives:
                raise UnknownDirective(self)
            self.assembler.directives[directive](self)
            return

        # finally check for instructions
        key = ''.join(self.cleaned_tokens[0])
        if not key in self.assembler.instructions:
            raise UnknownInstruction(self)
        instruction = self.assembler.instructions[key]
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
            except:
                # here we have a non-AssemblerException, so we
                # need to report the whole exceptions chain
                raise InvalidInstruction(self)
        else:
            if len(self.tokens) != 1:
                raise InvalidOpCodeArguments(self)
            blob = instruction
        self.assembler.append_assembled_bytes(blob)


class Instruction(Statement):
    def assemble(self, assembler):
        # first check if we are in macro recording mode
        if assembler.macro_recording is not None:
            macro = assembler.macro_recording
            macro.add_instruction(self)
            return

        # apply defines
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
            except:
                # here we have a non-AssemblerException, so we
                # need to report the whole exceptions chain
                raise InvalidInstruction(self)
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
                if pattern(self.tokens[index+start]):
                    continue
            else:
                if isinstance(pattern, str):
                    if self.tokens[index + start].upper() == pattern.upper():
                        continue
                if any([self.tokens[index + start].upper() == x.upper() for x in pattern]):
                    continue
            return False
        return True

    def unbound_match(self, *args, start=1):
        if (len(self.tokens) - start) < len(args):
            return False, None
        for index, pattern in enumerate(args):
            if pattern is None:
                continue
            if callable(pattern):
                if pattern(self.tokens[index+start]):
                    continue
            else:
                if isinstance(pattern, str):
                    if self.tokens[index + start].upper() == pattern.upper():
                        continue
                if any([self.tokens[index + start].upper() == x.upper() for x in pattern]):
                    continue
            return False, None
        return True, start+index+1

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
        if not is_valid_name(key):
            raise InvalidLabel(self)
        if assembler.parse_integer(key, 64, False) is not None:
            raise InvalidLabel(self)


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
