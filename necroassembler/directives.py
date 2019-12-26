from necroassembler.scope import Scope
from necroassembler.exceptions import InvalidArgumentsForDirective
from necroassembler.utils import pack_byte, pack_be16u, pack_be32u, pack_le16u, pack_le32u, pack_le32f, pack_be32f


class Repeat(Scope):

    @classmethod
    def directive_repeat(cls, instr):
        if len(instr.directive_args) not in (1, 2):
            raise InvalidArgumentsForDirective(instr)
        iterations = instr.assembler.parse_unsigned_integer(
            instr.directive_args[0])
        if iterations is None or iterations <= 0:
            raise InvalidArgumentsForDirective(instr)
        i_variable = None
        if len(instr.directive_args) == 2:
            i_variable = instr.directive_args[1]
        instr.assembler.push_scope(
            Repeat(instr.assembler, iterations, 0, i_variable))

    @classmethod
    def directive_endrepeat(cls, instr):
        instr.assembler.get_current_scope().end_repeat()

    def __init__(self, assembler, iterations, current_i, i_variable=None):
        super().__init__(assembler)
        self.iterations = iterations
        self.start_statement_index = assembler.statement_index
        self.current_i = current_i
        self.i_variable = i_variable
        if self.i_variable:
            self.defines[self.i_variable] = str(self.current_i)

    def end_repeat(self):
        self.iterations -= 1
        self.assembler.pop_scope()
        if self.iterations == 0:
            return
        self.assembler.statement_index = self.start_statement_index
        next_repeat = Repeat(self.assembler, self.iterations,
                             self.current_i + 1, self.i_variable)
        next_repeat.start_statement_index = self.start_statement_index
        self.assembler.push_scope(next_repeat)


class TryCatch(Scope):

    class Catch(Scope):
        pass

    @classmethod
    def directive_try(cls, instr):
        instr.assembler.push_scope(TryCatch(instr.assembler))

    def __init__(self, assembler):
        super().__init__(assembler)
        self.rollback_index = len(assembler.assembled_bytes)
        self.in_exception = None

    def assemble(self, instr):
        if self.in_exception is not None:
            # search for .catch or .endtry
            print(instr.tokens[0])
            return

        if instr.tokens[0].lower() == '.endtry':
            self.assembler.pop_scope()
            return

        try:
            super().assemble(instr)
        except:
            import sys
            print(sys.exc_info())
            self.in_exception = sys.exc_info()[1].__class__.__name__
            print(self.in_exception)


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
            blob = assembler.stringify(
                arg, 'utf-16-be' if assembler.big_endian else 'utf-16-le')
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
            blob = assembler.stringify(
                arg, 'utf-32-be' if assembler.big_endian else 'utf-32-le')
            if blob is None:
                value = assembler.parse_integer_or_label(
                    label=arg, bits_size=32, size=4)
                if assembler.big_endian:
                    blob = pack_be32u(value)
                else:
                    blob = pack_le32u(value)
            assembler.append_assembled_bytes(blob)

    @staticmethod
    def directive_df(instr):
        assembler = instr.assembler
        for arg in instr.args:
            if assembler.big_endian:
                blob = pack_be32f(float(''.join(arg)))
            else:
                blob = pack_le32f(float(''.join(arg)))
            assembler.append_assembled_bytes(blob)

    @staticmethod
    def directive_align(instr):
        assembler = instr.assembler
        if len(instr.directive_args) != 1:
            raise InvalidArgumentsForDirective(instr)
        size = assembler.parse_unsigned_integer(instr.directive_args[0])
        if size is None:
            raise InvalidArgumentsForDirective(instr)

        mod = (assembler.current_org + assembler.org_counter) % size
        if mod != 0:
            blob = bytes([assembler.fill_value]) * (size - mod)
            assembler.append_assembled_bytes(blob)
