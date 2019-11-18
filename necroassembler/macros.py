'''Assembler Macro system'''

from necroassembler.exceptions import InvalidArgumentsForDirective
from necroassembler.statements import Scope


class Macro(Scope):
    '''Represents a user-defined macro'''

    @classmethod
    def directive_macro(cls, instr):
        if len(instr.args) < 1:
            raise InvalidArgumentsForDirective(instr)
        name, *args = instr.args
        instr.assembler.push_scope(Macro(instr.assembler, name, *args))

    @classmethod
    def directive_end_macro(cls, instr):
        instr.assembler.get_current_scope().end_repeat()

    def __init__(self, assembler, name, *args):
        super().__init__(assembler)
        self.lines = []


class Macro:

    def __init__(self, tokens):
        self.name, *self.args = tokens
        self.instructions = []

    def add_instruction(self, instr):
        """Appends an instruction to a macro

        :param statements.Instruction instr: the Instrction to add, generally built by the Tokenizer
        """
        self.instructions.append(instr)

    def assemble(self, assembler, tokens):
        """Assembles a macro using the specified assembler

        :param assembler.Assembler assembler: the assembler to use
        :param list tokens: the tokens used to invoke the macro (macro name included)
        """
        _, *args = tokens
        macro_args = self.args
        for instr in self.instructions:
            original_tokens = instr.tokens.copy()
            # check for known macro args:
            # first build a dictionary of arg: value
            macro_dict = {}
            for macro_arg_index, macro_arg in enumerate(macro_args):
                macro_dict[macro_arg] = args[macro_arg_index]

            substitute_with_dict(instr.tokens, macro_dict, 0)

            instr.assemble(assembler)
            instr.tokens = original_tokens
