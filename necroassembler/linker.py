from necroassembler.utils import pack, in_bit_range, to_two_s_complement, pack_bits
from necroassembler.exceptions import (
    UnknownLabel, AssemblerException, AlignmentError, OnlyForwardAddressesAllowed, NotInBitRange)


class RelocationNotImplemented(AssemblerException):
    message = 'please subclass the ELF class and implement the \'relocate\' method'


class Linker:

    def _resolve_labels(self, assembler):

        for address in assembler.labels_addresses:
            data = assembler.labels_addresses[address]
            label = data.label
            scope = data.scope
            is_relative = data.relative != 0

            absolute_address = assembler.parse_integer(
                label, 64, False, False, scope)
            if not is_relative:
                true_address = absolute_address
            else:
                true_address = absolute_address - data.relative

            if true_address is None:
                true_address = self.resolve_unknown_symbol(
                    assembler, address, data)
                absolute_address = true_address

            if data.hook:
                data.hook(address, true_address)
                continue

            if absolute_address % data.alignment != 0:
                raise AlignmentError(label)

            size = data.size
            total_bits = data.bits_size

            if not is_relative and true_address < 0:
                raise OnlyForwardAddressesAllowed(label, true_address)

            if is_relative:
                true_address = to_two_s_complement(true_address, total_bits)

            if not in_bit_range(true_address, total_bits):
                raise NotInBitRange(true_address, total_bits, label)

            if data.filter:
                true_address = data.filter(true_address)

            if data.bits:
                true_address = pack_bits(0, (data.bits, true_address))

            for i in range(0, size):
                value = (true_address >> (8 * i)) & 0xFF
                if assembler.big_endian:
                    assembler.assembled_bytes[address +
                                              ((size-1) - i)] |= value
                else:
                    assembler.assembled_bytes[address + i] |= value

            if assembler.log:
                print('label "{0}" translated to ({1}) at address {2}'.format(
                    label, ','.join(['0x{0:02x}'.format(x) for x in assembler.assembled_bytes[address:address+size]]), hex(address)))

    def resolve_unknown_symbol(self, assembler, address, symbol_data):
        raise UnknownLabel(symbol_data.label)
        # make pylint happy ;)
        return 0

    def link(self, assembler):
        self._resolve_labels(assembler)
        return assembler.assembled_bytes


class ELF(Linker):

    def __init__(self, bits, big_endian, e_type, machine, alignment=0):
        self.header = b'\x7fELF' + \
            pack('BBBB', 2 if bits == 64 else 1, 2 if big_endian else 1, 1, 0)
        self.bits = bits
        self.endianess_prefix = '>' if big_endian else '<'
        self.header += bytes(8)
        self.header += pack(self.endianess_prefix + 'HHI', e_type, machine, 1)
        self.entry_point = 0
        if self.bits == 32:
            self.section_pack_format = self.endianess_prefix + 'IIIIIIIIII'
            self.section_header_size = 40
            self.header_size = 52
        elif self.bits == 64:
            self.section_pack_format = self.endianess_prefix + 'IIQQQQIIQQ'
            self.section_header_size = 64
            self.header_size = 64
        self.alignment = alignment
        self.relocations = {}

    def _build_null_section(self):
        return pack(self.section_pack_format, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    def _build_section(self, section_data):
        sh_type = 0x01
        if section_data['size'] == 0:
            sh_type = 0x08
        sh_flags = 0
        if 'R' in section_data['permissions']:
            sh_flags |= 0x02
        if 'W' in section_data['permissions']:
            sh_flags |= 0x01
        if 'X' in section_data['permissions']:
            sh_flags |= 0x04
        if 'E' in section_data['permissions']:
            sh_flags |= 0x04

        return pack(self.section_pack_format, section_data['elf_string_offset'], sh_type, sh_flags, section_data['start'],
                    self.file_base + section_data['offset'], section_data['size'], 0, 0, self.alignment, 0)

    def _build_string_section(self, name_offset, offset, data):
        return pack(self.section_pack_format, name_offset, 0x03, 0x20, 0, offset, len(data), 0, 0, 0, 0)

    def _build_symtab_section(self, name_offset, offset, data, link):
        return pack(self.section_pack_format, name_offset, 0x02, 0, 0, offset, len(data), link, 0, 0, 16 if self.bits == 32 else 24)

    def resolve_unknown_symbol(self, assembler, address, symbol_data):
        self.relocations[address] = symbol_data
        return 0

    def relocate(self, address, symbol_data):
        raise RelocationNotImplemented()

    def link(self, assembler):

        # first prepare the .shstrtab section
        sh_string_table = b'\x00'
        for section_name, section_data in assembler.sections.items():
            section_data['elf_string_offset'] = len(sh_string_table)
            sh_string_table += section_name.encode() + b'\0'

        sh_string_table_name_offset = len(sh_string_table)

        sh_string_table += '.shstrtab'.encode() + b'\0'

        # then build the symbols names table
        string_table = b'\x00'
        for symbol_name, symbol_data in assembler.labels.items():
            if symbol_name not in assembler.exports:
                continue
            symbol_data['elf_string_offset'] = len(string_table)
            string_table += symbol_name.encode() + b'\0'

        string_table_name_offset = len(sh_string_table)
        sh_string_table += '.strtab'.encode() + b'\0'

        symtab_name_offset = len(sh_string_table)
        sh_string_table += '.symtab'.encode() + b'\0'

        self.file_base = self.header_size + \
            self.section_header_size * (len(assembler.sections) + 4)

        sections = b''
        sections += self._build_null_section()
        for section_index, section_data in enumerate(assembler.sections.values()):
            section_data['elf_section_index'] = section_index
            sections += self._build_section(section_data)

        symtab = b''
        for symbol_name, symbol_data in assembler.labels.items():
            if symbol_name not in assembler.exports:
                continue
            if self.bits == 32:
                symtab += pack(self.endianess_prefix + 'IIIBBH',
                               symbol_data['elf_string_offset'], symbol_data['base'], 0,
                               0x10, 0, assembler.sections[symbol_data['section']]['elf_section_index'] + 1)
            if self.bits == 64:
                symtab += pack(self.endianess_prefix + 'IBBHQQ',
                               symbol_data['elf_string_offset'], 0x10, 0,
                               assembler.sections[symbol_data['section']]['elf_section_index'] + 1, symbol_data['base'], 0)

        code_size = len(assembler.assembled_bytes)

        sections += self._build_string_section(
            sh_string_table_name_offset, self.file_base + code_size, sh_string_table)

        sections += self._build_string_section(
            string_table_name_offset, self.file_base + code_size + len(sh_string_table), string_table)

        sections += self._build_symtab_section(
            symtab_name_offset, self.file_base + code_size + len(sh_string_table) + len(string_table), symtab, len(assembler.sections) + 2)

        if self.bits == 32:
            self.header += pack(self.endianess_prefix + 'IIIIHHHHHH', self.entry_point,
                                0, self.header_size, 0, self.header_size, 0, 0, self.section_header_size,
                                len(assembler.sections) + 4, len(assembler.sections) + 1)
        elif self.bits == 64:
            self.header += pack(self.endianess_prefix + 'QQQIHHHHHH', self.entry_point,
                                0, self.header_size, 0, self.header_size, 0, 0, self.section_header_size,
                                len(assembler.sections) + 4, len(assembler.sections) + 1)

        return self.header + sections + assembler.assembled_bytes + sh_string_table + string_table + symtab
