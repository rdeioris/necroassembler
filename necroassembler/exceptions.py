

class InvalidOpCodeArguments(Exception):
    def __init__(self, statement):
        super().__init__(
            'invalid arguments for opcode {0}'.format(statement.tokens[0]))