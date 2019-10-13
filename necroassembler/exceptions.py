

class InvalidOpCodeArguments(Exception):
    def __init__(self, subject):
        super().__init__(
            'invalid arguments for {0}'.format(subject))


class UnknownInstruction(Exception):
    def __init__(self, subject):
        super().__init__(
            'unknown instruction {0}'.format(subject))


class InvalidInstruction(Exception):
    def __init__(self, subject):
        super().__init__(
            'invalid instruction {0}'.format(subject))


class UnknownLabel(Exception):
    def __init__(self, label, subject):
        super().__init__(
            'unknown label "{0}" for {1}'.format(label, subject))


class AlignmentError(Exception):
    def __init__(self, label, subject):
        super().__init__(
            'wrong alignment for label "{0}" for {1}'.format(label, subject))


class NotInBitRange(Exception):
    def __init__(self, label, value, max_bits, subject):
        super().__init__(
            'value {1} of label "{0}" is not in the {2} bit range for {3}'.format(label, value, max_bits, subject))


class UnknownDirective(Exception):
    def __init__(self, subject):
        super().__init__(
            'unknown directive {0}'.format(subject))


class UnsupportedNestedMacro(Exception):
    def __init__(self, subject):
        super().__init__(
            'nested macros are not supported {0}'.format(subject))


class NotInMacroRecordingMode(Exception):
    def __init__(self, subject):
        super().__init__(
            'not in macro recording mode {0}'.format(subject))


class UnkownRegister(Exception):
    def __init__(self, subject):
        super().__init__(
            'unkown cpu register {0}'.format(subject))


class InvalidRegister(Exception):
    def __init__(self, subject):
        super().__init__(
            'unkown cpu register {0}'.format(subject))


class InvalideImmediateValue(Exception):
    def __init__(self, subject):
        super().__init__(
            'invalid immediate value {0}'.format(subject))
