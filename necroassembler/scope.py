from necroassembler.exceptions import (
    LabelAlreadyDefined, InvalidLabel, UnknownDirective, UnknownInstruction, AssemblerException, InvalidInstruction, InvalidOpCodeArguments)
from necroassembler.utils import is_valid_label


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

    def assemble(self, instr):
        # first of all: rebuild using defines
        instr.clean_tokens()

        # check for labels
        if instr.command.endswith(':'):
            label = instr.command[:-1]
            if is_valid_label(label):
                self.assembler.get_current_scope().add_label(label)
            else:
                raise InvalidLabel(label)
            return

        # now check for directives
        if instr.command.startswith('.'):
            directive = instr.command[1:]
            if not self.assembler.case_sensitive:
                directive = directive.upper()
            if not directive in self.assembler.directives:
                raise UnknownDirective(instr)
            self.assembler.directives[directive](instr)
            return

        # get the command key
        key = instr.command.upper()

        # check for macro
        if key in self.assembler.macros:
            self.assembler.macros[key](instr)
            return

        # finally check for instructions
        if key not in self.assembler.instructions:
            raise UnknownInstruction(instr)
        instruction = self.assembler.instructions[key]
        if callable(instruction):
            try:
                blob = instruction(instr)
                if blob is None:
                    # do not add 'self' here, will be added in the exception
                    raise InvalidInstruction()
            except AssemblerException as exc:
                # trick for adding more infos to the exception
                exc.args = (exc.args[0] + ' ' + str(instr),)
                raise exc from None
            except:
                # here we have a non-AssemblerException, so we
                # need to report the whole exceptions chain
                raise InvalidInstruction(instr)
        else:
            if len(instr.args) != 0:
                raise InvalidOpCodeArguments(instr)
            blob = instruction
        self.assembler.append_assembled_bytes(blob)
