from necroassembler.scope import Scope
from necroassembler.exceptions import InvalidArgumentsForDirective
from necroassembler.utils import pack_byte, pack_be16u, pack_be32u, pack_le16u, pack_le32u


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


class Data:

    @staticmethod
    def directive_db(instr):
        assembler = instr.assembler
        for arg in instr.args:
            blob = assembler.stringify(arg, 'ascii')
            if blob is None:
                value = assembler.parse_integer_or_label(
                    label=arg, bits_size=8, size=1)
                blob = pack_byte(value)
            assembler.append_assembled_bytes(blob)

    @staticmethod
    def directive_dw(instr):
        assembler = instr.assembler
        for arg in instr.args:
            blob = assembler.stringify(arg, 'utf-16-be' if assembler.big_endian else 'utf-16-le')
            if blob is None:
                value = assembler.parse_integer_or_label(
                    label=arg, bits_size=16, size=2)
                if assembler.big_endian:
                    blob = pack_be16u(value)
                else:
                    blob = pack_le16u(value)
            assembler.append_assembled_bytes(blob)

    @staticmethod
    def directive_dd(instr):
        assembler = instr.assembler
        for arg in instr.args:
            blob = assembler.stringify(arg, 'utf-32-be' if assembler.big_endian else 'utf-32-le')
            if blob is None:
                value = assembler.parse_integer_or_label(
                    label=arg, bits_size=32, size=4)
                if assembler.big_endian:
                    blob = pack_be32u(value)
                else:
                    blob = pack_le32u(value)
            assembler.append_assembled_bytes(blob)
