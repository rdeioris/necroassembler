'''Assembler Macro system'''

from necroassembler.exceptions import (
    InvalidArgumentsForDirective, UnsupportedNestedMacro, NotInMacroRecordingMode)
from necroassembler.scope import Scope


class MacroTemplate:

    def __init__(self, assembler, name, args):
        self.assembler = assembler
        self.name = name
        self.args = args
        self.start_line_index = assembler.line_index

    def __call__(self, instr):
        macro = Macro(self, instr.args)
        instr.assembler.push_scope(macro)
        instr.assembler.line_index = self.start_line_index


class Macro(Scope):
    '''Represents a user-defined macro'''

    macro_recording = None

    @classmethod
    def directive_macro(cls, instr):
        if instr.assembler.macro_recording is not None:
            raise UnsupportedNestedMacro(instr)
        key = instr.args[0][0]

        instr.assembler.macro_recording = MacroTemplate(
            instr.assembler, key, instr.args[0][1:])
        if not instr.assembler.case_sensitive:
            key = key.upper()
        instr.assembler.macros[key] = instr.assembler.macro_recording

    @classmethod
    def directive_endmacro(cls, instr):
        if instr.assembler.macro_recording is None:
            # check if we are in execution mode
            if isinstance(instr.assembler.get_current_scope(), Macro):
                current_macro = instr.assembler.pop_scope()
                instr.assembler.line_index = current_macro.caller_line_index
                return
            raise NotInMacroRecordingMode(instr)
        instr.assembler.macro_recording = None

    def __init__(self, template, args):
        super().__init__(template.assembler)
        self.template = template
        self.args = args
        self.caller_line_index = template.assembler.line_index
        for index, arg in enumerate(self.template.args):
            self.defines[arg] = self.args[0][index]
