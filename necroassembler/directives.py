from necroassembler.scope import Scope
from necroassembler.exceptions import InvalidArgumentsForDirective


class Repeat(Scope):

    @classmethod
    def directive_repeat(cls, instr):
        if len(instr.args) != 1:
            raise InvalidArgumentsForDirective(instr)
        iterations = instr.assembler.parse_integer(instr.args[0], 64, False)
        if iterations is None or iterations <= 0:
            raise InvalidArgumentsForDirective(instr)
        instr.assembler.push_scope(Repeat(instr.assembler, iterations))

    @classmethod
    def directive_endrepeat(cls, instr):
        instr.assembler.get_current_scope().end_repeat()

    def __init__(self, assembler, iterations):
        super().__init__(assembler)
        self.iterations = iterations
        self.start_statement_index = assembler.statement_index

    def end_repeat(self):
        self.iterations -= 1
        self.assembler.pop_scope()
        if self.iterations == 0:
            return
        self.assembler.statement_index = self.start_statement_index
        next_repeat = Repeat(self.assembler, self.iterations)
        next_repeat.start_statement_index = self.start_statement_index
        self.assembler.push_scope(next_repeat)

