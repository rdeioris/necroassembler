class Macro:
    def __init__(self, tokens):
        self.name, *self.args = tokens
        self.instructions = []

    def add_instruction(self, instr):
        self.instructions.append(instr)

    def assemble(self, assembler, tokens):
        _, *args = tokens
        macro_args = self.args
        for instr in self.instructions:
            original_tokens = instr.tokens.copy()
            # check for known macro args
            for macro_arg_index, macro_arg in enumerate(macro_args):
                if macro_arg in instr.tokens:
                    index = instr.tokens.index(macro_arg)
                    instr.tokens[index] = args[macro_arg_index]
            instr.assemble(assembler)
            instr.tokens = original_tokens
