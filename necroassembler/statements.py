from necroassembler.exceptions import (InvalidOpCodeArguments, UnknownInstruction,
                                       InvalidInstruction, UnknownDirective, LabelAlreadyDefined, InvalidLabel, AssemblerException, UnsupportedNestedMacro)
from necroassembler.utils import is_valid_label
from necroassembler.macros import Macro
import copy


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

    def _recursive_apply_define(self, container, index):
        if isinstance(container[index], str):
            anti_loop_check = []
            element = container[index]
            while element not in anti_loop_check:
                found_define = self.assembler.get_define(element)
                if not found_define:
                    break
                anti_loop_check.append(found_define)
                element = found_define
            container[index] = element
            return

        for sub_index, _ in enumerate(container[index]):
            self._recursive_apply_define(container[index], sub_index)

    def clean_tokens(self):
        self.cleaned_tokens = copy.deepcopy(self.tokens)
        for index, _ in enumerate(self.cleaned_tokens):
            self._recursive_apply_define(self.cleaned_tokens, index)

    def assemble(self):

        # special case for macro recording mode
        if self.assembler.macro_recording is not None:
            # check for nested
            if self.tokens[0] == '.macro':
                raise UnsupportedNestedMacro(self)
            # check for .endmacro
            if self.tokens[0] == '.endmacro':
                Macro.directive_endmacro(self)
            return

        # first of all: rebuild using defines
        self.clean_tokens()

        # check for labels
        if self.command.endswith(':'):
            label = self.command[:-1]
            if is_valid_label(label):
                self.assembler.get_current_scope().add_label(label)
            else:
                raise InvalidLabel(label)
            return

        # now check for directives
        if self.command.startswith('.'):
            directive = self.command[1:]
            if not self.assembler.case_sensitive:
                directive = directive.upper()
            if not directive in self.assembler.directives:
                raise UnknownDirective(self)
            self.assembler.directives[directive](self)
            return

        # get the command key
        key = self.command.upper()

        # check for macro
        if key in self.assembler.macros:
            self.assembler.macros[key](self)
            return

        # finally check for instructions
        if key not in self.assembler.instructions:
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
            if len(self.args) != 0:
                raise InvalidOpCodeArguments(self)
            blob = instruction
        self.assembler.append_assembled_bytes(blob)

    def match_arg(self, index, *pattern):
        if index >= len(self.args):
            return False
        arg = self.args[index]
        if isinstance(pattern, str) or callable(pattern):
            return self._match_arg_simple(arg, pattern)
        if isinstance(pattern, list):
            return self._match_arg_internal(arg, pattern)
        return self._match_arg_internal(arg, [pattern])

    def _match_arg_simple(self, arg, rule):
        # str
        if isinstance(rule, str):
            if len(arg) == 1 and arg[0].upper() == rule.upper():
                return True
        if callable(rule):
            if rule(arg):
                return True
        return False

    def _match_arg_internal(self, arg, pattern):
        skip_size = False
        if pattern and pattern[-1] == Ellipsis:
            if len(arg) < len(pattern):
                return False
            skip_size = True

        if not skip_size and len(arg) != len(pattern):
            return False

        for arg_index, arg_pattern in enumerate(pattern):
            if arg_pattern == Ellipsis:
                return True
            if arg_pattern is None:
                continue
            # str
            if isinstance(arg_pattern, str):
                if arg[arg_index].upper() != arg_pattern.upper():
                    return False
                continue

            # group
            if isinstance(arg_pattern, list):
                if not isinstance(arg[arg_index], list):
                    return False
                if not self._match_arg_internal(arg[arg_index], arg_pattern):
                    return False
                continue

            # multiple choices
            if isinstance(arg_pattern, tuple):
                if not any([arg[arg_index].upper() == x.upper() for x in arg_pattern]):
                    return False
                continue

            # callable
            if callable(arg_pattern):
                if not arg_pattern(arg[arg_index]):
                    return False
                continue

            return False

        return True

    def match(self, *pattern):
        # first check if the number of arguments matches
        skip_size = False
        if pattern and pattern[-1] == Ellipsis:
            if len(self.args) < len(pattern):
                return False
            skip_size = True

        if not skip_size and len(self.args) != len(pattern):
            return False
        for arg_index, arg_pattern in enumerate(pattern):
            if isinstance(arg_pattern, str) or callable(arg_pattern):
                if not self._match_arg_simple(self.args[arg_index], arg_pattern):
                    return False
            elif arg_pattern == Ellipsis:
                return True
            elif arg_pattern is None:
                continue
            else:
                if isinstance(arg_pattern, list):
                    if not self._match_arg_internal(self.args[arg_index], arg_pattern):
                        return False
                else:
                    if not self._match_arg_internal(self.args[arg_index], [arg_pattern]):
                        return False
        return True

    def apply(self, *filters):
        if len(self.args) != len(filters):
            raise InvalidOpCodeArguments(self)

        values = []
        for index, _filter in enumerate(filters):
            if _filter is None:
                continue
            values.append(_filter(self.args[index]))

        return tuple(values)
