class AssemblerException(Exception):
    message = None

    def __init__(self, context=None):
        if context is not None:
            self.message += ' ' + str(context)
        super().__init__(self.message)


class InvalidOpCodeArguments(AssemblerException):
    message = 'invalid arguments for opcode'


class UnknownInstruction(AssemblerException):
    message = 'unknown instruction'


class InvalidInstruction(AssemblerException):
    message = 'invalid instruction'


class UnknownLabel(AssemblerException):
    def __init__(self, label):
        self.message = 'unknown label "{0}"'.format(label)
        super().__init__()


class AlignmentError(AssemblerException):
    def __init__(self, label):
        self.message = 'wrong alignment for label "{0}"'.format(label)
        super().__init__()


class NotInBitRange(AssemblerException):
    def __init__(self, value, max_bits, label=None):
        self.message = 'value {0} is not in the {1} bit range'.format(
            value, max_bits)
        if label is not None:
            self.message = 'label {2} with value {0} is not in the {1} bit range'.format(
                value, max_bits, label)
        super().__init__()


class InvalidBitRange(AssemblerException):
    message = 'invalid bit range'


class OnlyForwardAddressesAllowed(AssemblerException):
    def __init__(self, label, value):
        self.message = 'value {1} of label "{0}" is not higher than the start location'.format(
            label, value)
        super().__init__()


class UnknownDirective(AssemblerException):
    message = 'unknown directive'


class UnsupportedNestedMacro(AssemblerException):
    message = 'nested macros are not supported'


class NotInMacroRecordingMode(AssemblerException):
    message = 'not in macro recording mode'


class UnknownRegister(AssemblerException):
    message = 'unknown cpu register'


class InvalidRegister(AssemblerException):
    message = 'invalid cpu register'


class InvalideImmediateValue(AssemblerException):
    message = 'invalid immediate value'


class InvalidArgumentsForDirective(AssemblerException):
    message = 'invalid arguments for directive'


class AddressOverlap(AssemblerException):
    message = 'address overlap'


class LabelAlreadyDefined(AssemblerException):
    message = 'label already defined'


class InvalidLabel(AssemblerException):
    message = 'invalid label'
