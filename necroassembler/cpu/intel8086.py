from necroassembler import Assembler, opcode
from necroassembler.utils import pack_bits, pack_byte, pack_le16u, pack_le16s, pack_8s, match
from necroassembler.exceptions import InvalidOpCodeArguments


REGS8 = ('AL', 'CL', 'DL', 'BL', 'AH', 'CH', 'DH', 'BH')
REGS16 = ('AX', 'CX', 'DX', 'BX', 'SP', 'BP', 'SI', 'DI')
SEGMENTS = ('ES', 'CS', 'SS', 'DS')


def _build_modrm(assembler, modrm):
    blob = pack_byte(pack_bits(0,
                               ((7, 6), modrm['mod']),
                               ((5, 3), modrm['reg']),
                               ((2, 0), modrm['rm'])))

    if modrm.get('displacement') is not None:
        blob += pack_le16s(assembler.parse_integer_or_label(
            modrm['displacement'],
            size=2,
            bits_size=16,
            offset=1,
            signed=True))
    return blob


def _get_modrm_mod(arg):
    if match(arg, 'BX', '+', 'SI'):
        return 0b00, 0b000, None
    if match(arg, 'BX', '+', 'DI'):
        return 0b00, 0b001, None
    if match(arg, 'BP', '+', 'SI'):
        return 0b00, 0b010, None
    if match(arg, 'BP', '+', 'DI'):
        return 0b00, 0b011, None
    if match(arg, 'SI'):
        return 0b00, 0b100, None
    if match(arg, 'DI'):
        return 0b00, 0b101, None
    if match(arg, 'BP'):
        return 0b00, 0b110, None
    if match(arg, 'BX'):
        return 0b00, 0b111, None
    # displacement (16 bit only)
    if match(arg, 'BX', '+', 'SI', ('+', '-'), ...):
        return 0b10, 0b000, arg[3:]
    if match(arg, 'BX', '+', 'DI', ('+', '-'), ...):
        return 0b10, 0b001, arg[3:]
    if match(arg, 'BP', '+', 'SI', ('+', '-'), ...):
        return 0b10, 0b010, arg[3:]
    if match(arg, 'BP', '+', 'DI', ('+', '-'), ...):
        return 0b10, 0b011, arg[3:]
    if match(arg, 'SI', ('+', '-'), ...):
        return 0b10, 0b100, arg[1:]
    if match(arg, 'DI', ('+', '-'), ...):
        return 0b10, 0b101, arg[1:]
    if match(arg, 'BP', ('+', '-'), ...):
        return 0b10, 0b110, arg[1:]
    if match(arg, 'BX', ('+', '-'), ...):
        return 0b10, 0b111, arg[1:]
    raise InvalidOpCodeArguments()


def _Gb(instr, assembler, index, modrm):
    if instr.match_arg(index, REGS8):
        modrm['reg'] = REGS8.index(instr.args[index][0])
        if index > 0:
            return 1, _build_modrm(assembler, modrm)
        return 1, b''


def _Gv(instr, assembler, index, modrm):
    if instr.match_arg(index, REGS16):
        modrm['reg'] = REGS16.index(instr.args[index][0])
        if index > 0:
            return 1, _build_modrm(assembler, modrm)
        return 1, b''


def _AL(instr, assembler, index, modrm):
    if instr.match_arg(index, 'AL'):
        return 1, b''


def _BL(instr, assembler, index, modrm):
    if instr.match_arg(index, 'BL'):
        return 1, b''


def _CL(instr, assembler, index, modrm):
    if instr.match_arg(index, 'CL'):
        return 1, b''


def _DL(instr, assembler, index, modrm):
    if instr.match_arg(index, 'DL'):
        return 1, b''


def _AH(instr, assembler, index, modrm):
    if instr.match_arg(index, 'AH'):
        return 1, b''


def _BH(instr, assembler, index, modrm):
    if instr.tokens[index].upper() == 'BH':
        return 1, b''


def _CH(instr, assembler, index, modrm):
    if instr.match_arg(index, 'CH'):
        return 1, b''


def _DH(instr, assembler, index, modrm):
    if instr.match_arg(index, 'DH'):
        return 1, b''


def _eAX(instr, assembler, index, modrm):
    if instr.match_arg(index, 'AX'):
        return 1, b''


def _eBX(instr, assembler, index, modrm):
    if instr.match_arg(index, 'BX'):
        return 1, b''


def _eCX(instr, assembler, index, modrm):
    if instr.match_arg(index, 'CX'):
        return 1, b''


def _eDX(instr, assembler, index, modrm):
    if instr.match_arg(index, 'DX'):
        return 1, b''


def _eSP(instr, assembler, index, modrm):
    if instr.match_arg(index, 'SP'):
        return 1, b''


def _eBP(instr, assembler, index, modrm):
    if instr.match_arg(index, 'BP'):
        return 1, b''


def _eDI(instr, assembler, index, modrm):
    if instr.match_arg(index, 'DI'):
        return 1, b''


def _eSI(instr, assembler, index, modrm):
    if instr.match_arg(index, 'SI'):
        return 1, b''


def _ES(instr, assembler, index, modrm):
    if instr.match_arg(index, 'ES'):
        return 1, b''


def _CS(instr, assembler, index, modrm):
    if instr.match_arg(index, 'CS'):
        return 1, b''


def _DS(instr, assembler, index, modrm):
    if instr.match_arg(index, 'DS'):
        return 1, b''


def _SS(instr, assembler, index, modrm):
    if instr.match_arg(index, 'SS'):
        return 1, b''


def _Ib(instr, assembler, index, modrm):
    if not instr.match_arg(index, REGS8 + REGS16 + SEGMENTS + ('[', ']')):
        return 1, pack_byte(assembler.parse_integer_or_label(
            instr.args[index], size=1, bits_size=8, offset=1))


def _Iv(instr, assembler, index, modrm):
    if not instr.match_arg(index, REGS8 + REGS16 + SEGMENTS + ('[', ']')):
        return 1, pack_le16u(assembler.parse_integer_or_label(
            instr.args[index], size=2, bits_size=16, offset=1))


def _Jb(instr, assembler, index, modrm):
    if not instr.match_arg(index, REGS8 + REGS16 + SEGMENTS + ('[', ']')):
        return 1, pack_8s(
            assembler.parse_integer_or_label(
                instr.args[index],
                size=1,
                bits_size=8,
                offset=1,
                relative=assembler.pc+2))


def _Ob(instr, assembler, index, modrm):
    if instr.match_arg(index, '[') and instr.match_arg(index+2, ']'):
        try:
            return 3, pack_le16u(assembler.parse_integer_or_label(
                instr.args[index+1], size=1, bits_size=8, offset=1))
        except InvalidOpCodeArguments:
            return None


def _Ov(instr, assembler, index, modrm):
    if instr.match_arg(index, '[') and instr.match_arg(index+2, ']'):
        try:
            return 3, pack_le16u(assembler.parse_integer_or_label(
                instr.args[index+1], size=2, bits_size=16, offset=1))

        except InvalidOpCodeArguments:
            return None


def _Eb(instr, assembler, index, modrm):
    if instr.match_arg(index, REGS8):
        modrm['mod'] = 3
        modrm['rm'] = REGS8.index(instr.args[index][0])
        return 1, b'' if 'reg' not in modrm else _build_modrm(assembler, modrm)

    if instr.match_arg(index, '[') and instr.match_arg(index+2, ']'):
        try:
            modrm['mod'], modrm['rm'], modrm['displacement'] = _get_modrm_mod(
                tuple(instr.args[index+1]))
            return 3, b'' if 'reg' not in modrm else _build_modrm(assembler, modrm)
        except InvalidOpCodeArguments:
            return None


def _Ev(instr, assembler, index, modrm):
    if instr.match_arg(index, REGS16):
        modrm['mod'] = 3
        modrm['rm'] = REGS16.index(instr.args[index][0])
        return 1, b'' if 'reg' not in modrm else _build_modrm(assembler, modrm)

    if instr.match_arg(index, '[') and instr.match_arg(index+2, ']'):
        try:
            modrm['mod'], modrm['rm'], modrm['displacement'] = _get_modrm_mod(
                tuple(instr.args[index+1]))
            return 3, b'' if 'reg' not in modrm else _build_modrm(assembler, modrm)
        except InvalidOpCodeArguments:
            return None


def _I0(instr, assembler, index, modrm):
    if len(instr.args) == 0:
        return 1, b''
    if len(instr.args) == 1:
        value = assembler.parse_integer(
            instr.args[index], 8, False)
        if value is None:
            return None
        if value == 0xA:
            return 1, b''
        return 1, pack_byte(value)


def _Sw(instr, assembler, index, modrm):
    if instr.match_arg(index, SEGMENTS):
        modrm['reg'] = SEGMENTS.index(instr.args[index][0])
        if index > 1:
            return 1, _build_modrm(assembler, modrm)
        return 1, b''


def _M(instr, assembler, index, modrm):
    if instr.match_arg(index, '[') and instr.match_arg(index+2, ']'):
        try:
            modrm['mod'], modrm['rm'], modrm['displacement'] = _get_modrm_mod(
                tuple(instr.args[index+1]))
            return 3, b'' if 'reg' not in modrm else _build_modrm(assembler, modrm)
        except InvalidOpCodeArguments:
            return None


def _Mp(instr, assembler, index, modrm):
    if instr.match_arg(index, '[') and instr.match_arg(index+2, ']'):
        try:
            modrm['mod'] = 0
            modrm['rm'] = 6
            return 3, _build_modrm(assembler, modrm) + pack_le16u(assembler.parse_integer_or_label(
                instr.args[index+1], size=2, bits_size=16, offset=1))
        except InvalidOpCodeArguments:
            return None


def _Ap(instr, assembler, index, modrm):
    arg = instr.tokens[index]
    if ':' in arg and arg.upper() not in REGS8 + REGS16 + SEGMENTS:
        segment, offset = arg.split(':')
        return 1, pack_le16u(
            assembler.parse_integer_or_label(
                offset, size=2, bits_size=16, offset=1),
            assembler.parse_integer_or_label(segment, size=2, bits_size=16, offset=3))


def _3(instr, assembler, index, modrm):
    if instr.match_arg(index, '3'):
        return 1, b''


def _1(instr, assembler, index, modrm):
    if instr.match_arg(index, '1'):
        return 1, b''


def _Jv(instr, assembler, index, modrm):
    if not instr.match_arg(index, REGS8 + REGS16 + SEGMENTS + ('[', ']')):
        return 1, pack_le16u(
            assembler.parse_integer_or_label(
                instr.args[index],
                size=2,
                bits_size=16,
                offset=1,
                relative=assembler.pc+3))


OPCODES_TABLE = (
    (0x00, 'ADD', _Eb, _Gb),
    (0x01, 'ADD', _Ev, _Gv),
    (0x02, 'ADD', _Gb, _Eb),
    (0x03, 'ADD', _Gv, _Ev),
    (0x04, 'ADD', _AL, _Ib),
    (0x05, 'ADD', _eAX, _Iv),
    (0x06, 'PUSH', _ES),
    (0x07, 'POP', _ES),
    (0x08, 'OR', _Eb, _Gb),
    (0x09, 'OR', _Ev, _Gv),
    (0x0A, 'OR', _Gb, _Eb),
    (0x0B, 'OR', _Gv, _Ev),
    (0x0C, 'OR', _AL, _Ib),
    (0x0D, 'OR', _eAX, _Iv),
    (0x0E, 'PUSH', _CS),
    (0x10, 'ADC', _Eb, _Gb),
    (0x11, 'ADC', _Ev, _Gv),
    (0x12, 'ADC', _Gb, _Eb),
    (0x13, 'ADC', _Gv, _Ev),
    (0x14, 'ADC', _AL, _Ib),
    (0x15, 'ADC', _eAX, _Iv),
    (0x16, 'PUSH', _SS),
    (0x17, 'POP', _SS),
    (0x18, 'SBB', _Eb, _Gb),
    (0x19, 'SBB', _Ev, _Gv),
    (0x1A, 'SBB', _Gb, _Eb),
    (0x1B, 'SBB', _Gv, _Ev),
    (0x1C, 'SBB', _AL, _Ib),
    (0x1D, 'SBB', _eAX, _Iv),
    (0x1E, 'PUSH', _DS),
    (0x1F, 'POP', _DS),
    (0x20, 'AND', _Eb, _Gb),
    (0x21, 'AND', _Ev, _Gv),
    (0x22, 'AND', _Gb, _Eb),
    (0x23, 'AND', _Gv, _Ev),
    (0x24, 'AND', _AL, _Ib),
    (0x25, 'AND', _eAX, _Iv),
    (0x27, 'DAA'),
    (0x28, 'SUB', _Eb, _Gb),
    (0x29, 'SUB', _Ev, _Gv),
    (0x2A, 'SUB', _Gb, _Eb),
    (0x2B, 'SUB', _Gv, _Ev),
    (0x2C, 'SUB', _AL, _Ib),
    (0x2D, 'SUB', _eAX, _Iv),
    (0x2F, 'DAS'),
    (0x30, 'XOR', _Eb, _Gb),
    (0x31, 'XOR', _Ev, _Gv),
    (0x32, 'XOR', _Gb, _Eb),
    (0x33, 'XOR', _Gv, _Ev),
    (0x34, 'XOR', _AL, _Ib),
    (0x35, 'XOR', _eAX, _Iv),
    (0x37, 'AAA'),
    (0x38, 'CMP', _Eb, _Gb),
    (0x39, 'CMP', _Ev, _Gv),
    (0x3A, 'CMP', _Gb, _Eb),
    (0x3B, 'CMP', _Gv, _Ev),
    (0x3C, 'CMP', _AL, _Ib),
    (0x3D, 'CMP', _eAX, _Iv),
    (0x3F, 'AAS'),
    (0x40, 'INC', _eAX),
    (0x41, 'INC', _eCX),
    (0x42, 'INC', _eDX),
    (0x43, 'INC', _eBX),
    (0x44, 'INC', _eSP),
    (0x45, 'INC', _eBP),
    (0x46, 'INC', _eSI),
    (0x47, 'INC', _eDI),
    (0x48, 'DEC', _eAX),
    (0x49, 'DEC', _eCX),
    (0x4A, 'DEC', _eDX),
    (0x4B, 'DEC', _eBX),
    (0x4C, 'DEC', _eSP),
    (0x4D, 'DEC', _eBP),
    (0x4E, 'DEC', _eSI),
    (0x4F, 'DEC', _eDI),
    (0x50, 'PUSH', _eAX),
    (0x51, 'PUSH', _eCX),
    (0x52, 'PUSH', _eDX),
    (0x53, 'PUSH', _eBX),
    (0x54, 'PUSH', _eSP),
    (0x55, 'PUSH', _eBP),
    (0x56, 'PUSH', _eSI),
    (0x57, 'PUSH', _eDI),
    (0x58, 'POP', _eAX),
    (0x59, 'POP', _eCX),
    (0x5A, 'POP', _eDX),
    (0x5B, 'POP', _eBX),
    (0x5C, 'POP', _eSP),
    (0x5D, 'POP', _eBP),
    (0x5E, 'POP', _eSI),
    (0x5F, 'POP', _eDI),
    (0x70, 'JO', _Jb),
    (0x71, 'JNO', _Jb),
    (0x72, 'JB', _Jb),
    (0x73, 'JNB', _Jb),
    (0x74, 'JZ', _Jb),
    (0x75, 'JNZ', _Jb),
    (0x76, 'JBE', _Jb),
    (0x77, 'JA', _Jb),
    (0x78, 'JS', _Jb),
    (0x79, 'JNS', _Jb),
    (0x7A, 'JPE', _Jb),
    (0x7B, 'JPO', _Jb),
    (0x7C, 'JL', _Jb),
    (0x7D, 'JGE', _Jb),
    (0x7E, 'JLE', _Jb),
    (0x7F, 'JG', _Jb),
    (0x84, 'TEST', _Gb, _Eb),
    (0x85, 'TEST', _Gv, _Ev),
    (0x86, 'XCHG', _Gb, _Eb),
    (0x87, 'XCHG', _Gv, _Ev),
    (0x88, 'MOV', _Eb, _Gb),
    (0x89, 'MOV', _Ev, _Gv),
    (0x8A, 'MOV', _Gb, _Eb),
    (0x8B, 'MOV', _Gv, _Ev),
    (0x8C, 'MOV', _Ev, _Sw),
    (0x8D, 'LEA', _Gv, _M),
    (0x8E, 'MOV', _Sw, _Ev),
    (0x8F, 'POP', _Ev),
    (0x90, 'NOP'),
    (0x91, 'XCHG', _eCX, _eAX),
    (0x92, 'XCHG', _eDX, _eAX),
    (0x93, 'XCHG', _eBX, _eAX),
    (0x94, 'XCHG', _eSP, _eAX),
    (0x95, 'XCHG', _eBP, _eAX),
    (0x96, 'XCHG', _eSI, _eAX),
    (0x97, 'XCHG', _eDI, _eAX),
    (0x98, 'CBW'),
    (0x99, 'CWD'),
    (0x9A, 'CALL', _Ap),
    (0x9B, 'WAIT'),
    (0x9C, 'PUSHF'),
    (0x9D, 'POPF'),
    (0x9E, 'SAHF'),
    (0x9F, 'LAHF'),
    (0xA0, 'MOV', _AL, _Ob),
    (0xA1, 'MOV', _eAX, _Ov),
    (0xA2, 'MOV', _Ob, _AL),
    (0xA3, 'MOV', _Ov, _eAX),
    (0xA4, 'MOVSB'),
    (0xA5, 'MOVSW'),
    (0xA6, 'CMPSB'),
    (0xA7, 'CMPSW'),
    (0xA8, 'TEST', _AL, _Ib),
    (0xA9, 'TEST', _eAX, _Iv),
    (0xAA, 'STOSB'),
    (0xAB, 'STOSW'),
    (0xAC, 'LODSB'),
    (0xAD, 'LODSW'),
    (0xAE, 'SCASB'),
    (0xAF, 'SCASW'),
    (0xB0, 'MOV', _AL, _Ib),
    (0xB1, 'MOV', _CL, _Ib),
    (0xB2, 'MOV', _DL, _Ib),
    (0xB3, 'MOV', _BL, _Ib),
    (0xB4, 'MOV', _AH, _Ib),
    (0xB5, 'MOV', _CH, _Ib),
    (0xB6, 'MOV', _DH, _Ib),
    (0xB7, 'MOV', _BH, _Ib),
    (0xB8, 'MOV', _eAX, _Iv),
    (0xB9, 'MOV', _eCX, _Iv),
    (0xBA, 'MOV', _eDX, _Iv),
    (0xBB, 'MOV', _eBX, _Iv),
    (0xBC, 'MOV', _eSP, _Iv),
    (0xBD, 'MOV', _eBP, _Iv),
    (0xBE, 'MOV', _eSI, _Iv),
    (0xBF, 'MOV', _eDI, _Iv),
    (0xC2, 'RET', _Iv),
    (0xC3, 'RET'),
    (0xC4, 'LES', _Gv, _Mp),
    (0xC5, 'LDS', _Gv, _Mp),
    (0xC6, 'MOV', _Eb, _Ib),
    (0xC7, 'MOV', _Ev, _Iv),
    (0xCA, 'RETF', _Iv),
    (0xCB, 'RETF'),
    (0xCC, 'INT', _3),
    (0xCD, 'INT', _Ib),
    (0xCE, 'INTO'),
    (0xCF, 'IRET'),
    (0xD4, 'AAM', _I0),
    (0xD5, 'AAD', _I0),
    (0xD4, 'AAM'),
    (0xD5, 'AAD'),
    (0xD7, 'XLAT'),
    (0xE0, 'LOOPNZ', _Jb),
    (0xE1, 'LOOPZ', _Jb),
    (0xE2, 'LOOP', _Jb),
    (0xE3, 'JCXZ', _Jb),
    (0xE4, 'IN', _AL, _Ib),
    (0xE5, 'IN', _eAX, _Ib),
    (0xE6, 'OUT', _Ib, _AL),
    (0xE7, 'OUT', _Ib, _eAX),
    (0xE8, 'CALL', _Jv),
    (0xE9, 'JMP', _Jv),
    (0xEA, 'JMP', _Ap),
    (0xEB, 'JMP', _Jb),
    (0xEC, 'IN', _AL, _eDX),
    (0xED, 'IN', _eAX, _eDX),
    (0xEE, 'OUT', _eDX, _AL),
    (0xEF, 'OUT', _eDX, _eAX),
    (0xF0, 'LOCK'),
    (0xF2, 'REPNZ'),
    (0xF3, 'REPZ'),
    (0xF4, 'HLT'),
    (0xF5, 'CMC'),
    (0xF8, 'CLC'),
    (0xF9, 'STC'),
    (0xFA, 'CLI'),
    (0xFB, 'STI'),
    (0xFC, 'CLD'),
    (0xFD, 'STD'),

    # extended opcodes
    (0xF706, 'DIV', _Ev),
    (0xF704, 'MUL', _Ev),
    (0xD004, 'SHL', _Eb),
    (0xD104, 'SHL', _Ev),
    (0xD005, 'SHR', _Eb),
    (0xD105, 'SHR', _Ev)
)


class Intel8086OpCode:

    def __init__(self, assembler, name, base, args):
        self.assembler = assembler
        self.name = name
        self.conditions = [(base, args)]

    def add_condition(self, base, args):
        self.conditions.append((base, args))

    def __call__(self, instr):
        print(instr)
        for base, args in self.conditions:
            modrm = {}
            if base > 0xFF:
                modrm['reg'] = base & 0xFF
                base = base >> 8
            if not args:
                if len(instr.args) == 0:
                    return pack_byte(base)
                raise InvalidOpCodeArguments(instr)
            if len(instr.args) < 1:
                continue
            index = 0
            skip = False
            full_blob = b''
            for arg in args:
                delta_and_blob = arg(instr, self.assembler, index, modrm)
                if not delta_and_blob or not delta_and_blob[0]:
                    skip = True
                    break
                else:
                    index += delta_and_blob[0]
                    full_blob += delta_and_blob[1]
            if not skip:
                return pack_byte(base) + full_blob


class AssemblerIntel8086(Assembler):

    hex_prefixes = ('0x', '0h', '$0')
    hex_suffixes = ('h',)

    dec_prefixes = ('0d',)
    dec_suffixes = ('d',)

    bin_prefixes = ('0b', '0y')
    bin_suffixes = ('b', 'y')

    oct_prefixes = ('0o', '0q')
    oct_suffixes = ('o', 'q')

    special_symbols = ('[', ']')
    math_brackets = ('(', ')')

    def register_instructions(self):
        for item in OPCODES_TABLE:
            if item[1].upper() in self.instructions:
                self.instructions[item[1].upper()].add_condition(
                    item[0], item[2:])
            else:
                i8086_opcode = Intel8086OpCode(
                    self, item[1], item[0], item[2:])
                self.register_instruction(item[1], i8086_opcode)


if __name__ == '__main__':
    AssemblerIntel8086.main()
