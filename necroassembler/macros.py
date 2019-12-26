'''Assembler Macro system'''

from necroassembler.exceptions import (
    InvalidArgumentsForDirective, UnsupportedNestedMacro,
    NotInMacroRecordingMode, NotEnoughArgumentsForMacro, BadOptionalArgumentsForMacro)
from necroassembler.scope import Scope


class MacroTemplate:

    def __init__(self, assembler, name, args):
        self.assembler = assembler
        self.name = name
        # sanitize optional args
        optional = False
        for arg in args:
            if optional:
                if not '=' in arg:
                    raise BadOptionalArgumentsForMacro()
            else:
                if '=' in arg:
                    optional = True
        self.args = args
        self.start_statement_index = assembler.statement_index

    def __call__(self, instr):
        macro = Macro(self, instr.args)
        instr.assembler.push_scope(macro)
        instr.assembler.statement_index = self.start_statement_index


class MacroRecording(Scope):

    def assemble(self, instr):
        # check for nested
        if instr.tokens[0].lower() == '.macro':
            raise UnsupportedNestedMacro(instr)
        # check for .endmacro
        if instr.tokens[0].lower() == '.endmacro':
            instr.assembler.pop_scope()
            return
        return


class Macro(Scope):
    '''Represents a user-defined macro'''

    @classmethod
    def directive_macro(cls, instr):
        key = instr.directive_args[0]

        new_template = MacroTemplate(
            instr.assembler, key, instr.directive_args[1:])
        if not instr.assembler.case_sensitive:
            key = key.upper()
        instr.assembler.macros[key] = new_template
        instr.assembler.push_scope(MacroRecording(instr.assembler))

    @classmethod
    def directive_endmacro(cls, instr):
        current_macro = instr.assembler.pop_scope()
        instr.assembler.statement_index = current_macro.caller_statement_index

    def __init__(self, template, args):
        super().__init__(template.assembler)
        self.template = template
        self.args = args
        self.caller_statement_index = template.assembler.statement_index

        # check for optional arguments
        if len(self.args) < len(self.template.args):
            for index in range(len(self.args), len(self.template.args)):
                if '=' in self.template.args[index]:
                    _, value = self.template.args[index].split('=', 1)
                    self.args.append([value])

        if len(self.args) != len(self.template.args):
            raise NotEnoughArgumentsForMacro()
        for index, arg in enumerate(self.template.args):
            if '=' in arg:
                arg, _ = arg.split('=', 1)
            self.defines[arg] = self.args[index]
