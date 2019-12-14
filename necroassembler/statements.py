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
        if not self.cleaned_tokens:
            self.cleaned_tokens = self.tokens
        if self.context is not None:
            return 'at line {1} of {0}: {2} {3}'.format(self.context, self.line, self.command, str(self.args))
        return 'at line {0}: {1} {2}'.format(self.line, self.command, str(self.args))

    @property
    def args(self):
        return self.cleaned_tokens[1:]

    @property
    def directive_args(self):
        if not self.args:
            return []
        return self.args[0]

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
            if isinstance(element, list):
                del(container[index])
                for additional_index, item in enumerate(element):
                    container.insert(index+additional_index, item)
                # hack for not losing the first element after substitution
                self._recursive_apply_define(container, index)
            else:
                container[index] = element
            return

        for sub_index, _ in enumerate(container[index]):
            self._recursive_apply_define(container[index], sub_index)

    def clean_tokens(self):
        self.cleaned_tokens = copy.deepcopy(self.tokens)
        for index, _ in enumerate(self.cleaned_tokens):
            self._recursive_apply_define(self.cleaned_tokens, index)

    def assemble(self):
        self.assembler.get_current_scope().assemble(self)

    def match_arg(self, index, *pattern):
        if index >= len(self.args):
            return False
        arg = self.args[index]
        if isinstance(pattern, str) or callable(pattern):
            return self._match_arg_simple(arg, pattern)

        return self._match_arg_internal(arg, pattern)

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

    def unbound_match(self, start, *pattern):
        # first check if the number of arguments matches
        if (len(self.args) - start) < len(pattern):
            return False, -1
        for arg_index, arg_pattern in enumerate(pattern):
            arg_index += start
            if isinstance(arg_pattern, str) or callable(arg_pattern):
                if not self._match_arg_simple(self.args[arg_index], arg_pattern):
                    return False, -1
            elif arg_pattern is None:
                continue
            else:
                if isinstance(arg_pattern, list):
                    if not self._match_arg_internal(self.args[arg_index], arg_pattern):
                        return False, -1
                else:
                    if not self._match_arg_internal(self.args[arg_index], [arg_pattern]):
                        return False, -1
        return True, len(pattern)

    def apply(self, *filters):
        if len(self.args) != len(filters):
            raise InvalidOpCodeArguments(self)

        values = []
        for index, _filter in enumerate(filters):
            if _filter is None:
                continue
            values.append(_filter(self.args[index]))

        return tuple(values)
