'''Assembler Macro system'''
from necroassembler.utils import substitute_with_dict


class Macro:
    '''Represents a user-defined macro'''

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
