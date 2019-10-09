

class InvalidOpCodeArguments(Exception):
    def __init__(self, subject):
        super().__init__(
            'invalid arguments for {0}'.format(subject))


class UnknownLabel(Exception):
    def __init__(self, label, subject):
        super().__init__(
            'unknown label "{0}" for {1}'.format(label, subject))
