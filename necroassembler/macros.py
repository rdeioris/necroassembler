'''Assembler Macro system'''


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
            # check for known macro args
            for macro_arg_index, macro_arg in enumerate(macro_args):
                prefix = '<>' + ''.join(assembler.special_prefixes)
                for index in [index for index, value in enumerate(instr.tokens) if value.lstrip(prefix).rstrip('+-') == macro_arg]:
                    # should be safe to use .replace here, as we already checked via lstrip/rstrip
                    instr.tokens[index] = instr.tokens[index].replace(
                        macro_arg, args[macro_arg_index])

            instr.assemble(assembler)
            instr.tokens = original_tokens
