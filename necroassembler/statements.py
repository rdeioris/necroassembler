from necroassembler.exceptions import (InvalidOpCodeArguments, UnknownInstruction,
                                       InvalidInstruction, UnknownDirective, LabelAlreadyDefined, InvalidLabel, AssemblerException, UnsupportedNestedMacro)
from necroassembler.utils import is_valid_label
from necroassembler.macros import Macro


class Instruction:
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

    @property
    def command_str(self):
        return ''.join(self.command)

    def clean_tokens(self):
        self.cleaned_tokens = []
        for token in self.tokens:
            new_elements = []
            for element in token:
                anti_loop_check = []
                while element not in anti_loop_check:
                    found_define = self.assembler.get_define(element)
                    if not found_define:
                        break
                    anti_loop_check.append(found_define)
                    element = found_define
                new_elements.append(element)
            self.cleaned_tokens.append(new_elements)

    def assemble(self):

        # special case for macro recording mode
        if self.assembler.macro_recording is not None:
            # check for nested
            if self.tokens[0][0] == '.' and self.tokens[0][1] == 'macro':
                raise UnsupportedNestedMacro(self)
            # check for .endmacro
            if self.tokens[0][0] == '.' and self.tokens[0][1] == 'endmacro':
                Macro.directive_endmacro(self)
            return

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

        # get the command key
        key = self.command_str

        # check for macro
        if key in self.assembler.macros:
            self.assembler.macros[key](self)
            return

        # finally check for instructions
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
