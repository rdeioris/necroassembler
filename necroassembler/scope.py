from necroassembler.exceptions import LabelAlreadyDefined

class Scope:

    def __init__(self, assembler):
        self.assembler = assembler
        self.labels = {}
        # this gets a meaningful value only after pushing
        self.parent = None
        self.defines = {}

    def add_label(self, label):
        if label in self.labels:
            raise LabelAlreadyDefined(label)
        self.labels[label] = {
            'scope': self.assembler.get_current_scope(),
            'base': self.assembler.org_counter,
            'org': self.assembler.current_org,
            'section': self.assembler.current_section}
