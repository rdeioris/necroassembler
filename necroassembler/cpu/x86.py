from necroassembler import Assembler, directive
from necroassembler.exceptions import InvalidOpCodeArguments, InvalidArgumentsForDirective
from necroassembler.utils import (pack_byte, pack_le16u, pack_le32u,
                                  pack_le64u, pack_bits, pack_le16s, pack_le32s, pack_le64s, match)
from necroassembler.statements import Instruction

REGS8 = ('AL', 'CL', 'DL', 'BL', 'AH', 'CH', 'DH', 'BH')
REGS16 = ('AX', 'CX', 'DX', 'BX', 'SP', 'BP', 'SI', 'DI')
REGS32 = ('EAX', 'ECX', 'EDX', 'EBX', 'ESP', 'EBP', 'ESI', 'EDI')
REGS64 = ('RAX', 'RCX', 'RDX', 'RBX', 'RSP', 'RBP', 'RSI', 'RDI')
CREGS = ('CR0', 'CR1', 'CR2', 'CR3', 'CR4', 'CR5', 'CR6', 'CR7')
SEGMENTS = ('ES', 'CS', 'SS', 'DS')

ALL_REGS = REGS8 + REGS16 + REGS32 + REGS64 + CREGS + SEGMENTS


def _build_modrm(assembler, base, modrm):
    blob = pack_byte(pack_bits(0,
                               ((7, 6), modrm['mod']),
                               ((5, 3), modrm['reg']),
                               ((2, 0), modrm['rm'])))

    if modrm.get('displacement') is not None:
        if modrm['bits'] == 16:
            blob += pack_le16s(assembler.parse_integer_or_label(
                modrm['displacement'].lstrip('+'),
                size=2,
                bits_size=16,
                offset=len(base),
                signed=True))
        if modrm['bits'] == 32:
            blob += pack_le32s(assembler.parse_integer_or_label(
                modrm['displacement'].lstrip('+'),
                size=4,
                bits_size=32,
                offset=len(base),
                signed=True))
        if modrm['bits'] == 64:
            blob += pack_le64s(assembler.parse_integer_or_label(
                modrm['displacement'].lstrip('+'),
                size=8,
                bits_size=64,
                offset=len(base),
                signed=True))
    return blob


def _get_modrm_mod(arg):
    if match(arg, ('BX', 'EBX', 'RBX'), '+', ('SI', 'ESI', 'RSI')):
        return 0b00, 0b000, 3, None
    if match(arg, ('BX', 'EBX', 'RBX'), '+', ('DI', 'EDI', 'RDI')):
        return 0b00, 0b001, 3, None
    if match(arg, ('BP', 'EBP', 'RBP'), '+', ('SI', 'ESI', 'RSI')):
        return 0b00, 0b010, 3, None
    if match(arg, ('BP', 'EBP', 'RBP'), '+', ('DI', 'EDI', 'RDI')):
        return 0b00, 0b011, 3, None
    if match(arg, ('SI', 'ESI', 'RSI')):
        return 0b00, 0b100, 1, None
    if match(arg, ('DI', 'EDI', 'RDI')):
        return 0b00, 0b101, 1, None
    if match(arg, ('BP', 'EBP', 'RBP')):
        return 0b00, 0b110, 1, None
    if match(arg, ('BX', 'EBX', 'RBX')):
        return 0b00, 0b111, 1, None
    # displacement (16 bit only)
    if match(arg, 'BX', '+', 'SI', ('+', '-'), None):
        return 0b10, 0b000, 5, arg[3] + arg[4]
    if match(arg, 'BX', '+', 'DI', ('+', '-'), None):
        return 0b10, 0b001, 5, arg[3] + arg[4]
    if match(arg, 'BP', '+', 'SI', ('+', '-'), None):
        return 0b10, 0b010, 5, arg[3] + arg[4]
    if match(arg, 'BP', '+', 'DI', ('+', '-'), None):
        return 0b10, 0b011, 5, arg[3] + arg[4]
    if match(arg, 'SI', ('+', '-'), None):
        return 0b10, 0b100, 3, arg[1] + arg[2]
    if match(arg, 'DI', ('+', '-'), None):
        return 0b10, 0b101, 3, arg[1] + arg[2]
    if match(arg, 'BP', ('+', '-'), None):
        return 0b10, 0b110, 3, arg[1] + arg[2]
    if match(arg, 'BX', ('+', '-'), None):
        return 0b10, 0b111, 3, arg[1] + arg[2]
    raise InvalidOpCodeArguments()


def _apply_Z(base, reg, regs):
    value = regs.index(reg.upper())
    base[-1] |= value
    return base


def _Eb(instr, base, assembler, index, modrm):
    pass


def _Gb(instr, base, assembler, index, modrm):
    pass


def _Evqp(instr, base, assembler, index, modrm):
    arg = instr.tokens[index].upper()
    if arg in REGS16:
        modrm['mod'] = 3
        modrm['rm'] = REGS16.index(arg)
        if 'bits' not in modrm:
            modrm['bits'] = 16
            if assembler.bits != 16:
                base.insert(0, 0x66)
        return 1, base, b'' if 'reg' not in modrm else _build_modrm(assembler, base, modrm)

    if arg in REGS32:
        modrm['mod'] = 3
        modrm['rm'] = REGS32.index(arg)
        if 'bits' not in modrm:
            modrm['bits'] = 32
            if assembler.bits == 16:
                base.insert(0, 0x66)
        return 1, base, b'' if 'reg' not in modrm else _build_modrm(assembler, base, modrm)

    if arg in REGS64:
        modrm['mod'] = 3
        modrm['rm'] = REGS64.index(arg)
        if 'bits' not in modrm:
            modrm['bits'] = 64
        return 1, base, b'' if 'reg' not in modrm else _build_modrm(assembler, base, modrm)

    if arg == '[':
        try:
            end_index = instr.tokens.index(']', index+1)
        except ValueError:
            raise InvalidOpCodeArguments(instr)
        try:
            modrm['mod'], modrm['rm'], delta, modrm['displacement'] = _get_modrm_mod(
                tuple(instr.tokens[index+1:end_index]))
            return 2 + delta, base, b'' if 'reg' not in modrm else _build_modrm(assembler, base, modrm)
        except InvalidOpCodeArguments:
            return None


def _Gvqp(instr, base, assembler, index, modrm):
    reg = instr.tokens[index].upper()
    if reg in REGS16:
        modrm['reg'] = REGS16.index(reg)
        if 'bits' not in modrm:
            modrm['bits'] = 16
            if assembler.bits != 16:
                base.insert(0, 0x66)
        if index > 1:
            return 1, base, _build_modrm(assembler, base, modrm)
        return 1, base, b''
    if reg in REGS32:
        modrm['reg'] = REGS32.index(reg)
        if 'bits' not in modrm:
            modrm['bits'] = 32
            if assembler.bits == 16:
                base.insert(0, 0x66)
        if index > 1:
            return 1, base, _build_modrm(assembler, base, modrm)
        return 1, base, b''
    if reg in REGS64:
        modrm['reg'] = REGS64.index(reg)
        if 'bits' not in modrm:
            modrm['bits'] = 64
        if index > 1:
            return 1, base, _build_modrm(assembler, base, modrm)
        return 1, base, b''


def _Zvqp(instr, base, assembler, index, modrm):
    reg = instr.tokens[index].upper()
    if reg in REGS32:
        base = _apply_Z(base, reg, REGS32)
        if assembler.bits == 16:
            base.insert(0, 0x66)
        modrm['bits'] = 32
        return 1, base, b''
    if reg in REGS64:
        base = _apply_Z(base, reg, REGS64)
        modrm['bits'] = 64
        return 1, base, b''
    if reg in REGS16:
        if assembler.bits != 16:
            base.insert(0, 0x66)
        modrm['bits'] = 16
        base = _apply_Z(base, reg, REGS16)
        return 1, base, b''


def _Rvqp(instr, base, assembler, index, modrm):
    pass


def _AL(instr, base, assembler, index, modrm):
    pass


def _CL(instr, base, assembler, index, modrm):
    pass


def _DX(instr, base, assembler, index, modrm):
    pass


def _Ib(instr, base, assembler, index, modrm):
    pass


def _Ivds(instr, base, assembler, index, modrm):
    if instr.tokens[index].upper() not in ALL_REGS + ('[', ']'):
        if 'bits' in modrm:
            if modrm['bits'] == 16:
                return 1, base, pack_le16u(assembler.parse_integer_or_label(
                    instr.tokens[index], size=2, bits_size=16, offset=len(base)))
            if modrm['bits'] == 32:
                return 1, base, pack_le32u(assembler.parse_integer_or_label(
                    instr.tokens[index], size=4, bits_size=32, offset=len(base)))


def _rAX(instr, base, assembler, index, modrm):
    if instr.tokens[index].upper() == 'AX':
        modrm['bits'] = 16
        if assembler.bits != 16:
            base.insert(0, 0x66)
        return 1, base, b''
    if instr.tokens[index].upper() == 'EAX':
        modrm['bits'] = 32
        if assembler.bits == 16:
            base.insert(0, 0x66)
        return 1, base, b''
    if instr.tokens[index].upper() == 'RAX':
        modrm['bits'] = 64
        return 1, base, b''


def _Zv(instr, base, assembler, index, modrm):
    pass


def _Zvq(instr, base, assembler, index, modrm):
    reg = instr.tokens[index].upper()
    if reg in REGS64:
        base = _apply_Z(base, reg, REGS64)
        if assembler.bits == 16:
            base.insert(0, 0x66)
        modrm['bits'] = 64
        return 1, base, b''
    if reg in REGS16:
        if assembler.bits != 16:
            base.insert(0, 0x66)
        modrm['bits'] = 16
        base = _apply_Z(base, reg, REGS16)
        return 1, base, b''


def _Jbs(instr, base, assembler, index, modrm):
    pass


def _Ibs(instr, base, assembler, index, modrm):
    pass


def _Gv(instr, base, assembler, index, modrm):
    pass


def _Ew(instr, base, assembler, index, modrm):
    pass


def _Ev(instr, base, assembler, index, modrm):
    pass


def _1(instr, base, assembler, index, modrm):
    pass


def _Gdqp(instr, base, assembler, index, modrm):
    pass


def _Ed(instr, base, assembler, index, modrm):
    pass


def _Ivs(instr, base, assembler, index, modrm):
    pass


def _Ibss(instr, base, assembler, index, modrm):
    pass


def _ST(instr, base, assembler, index, modrm):
    pass


def _EST(instr, base, assembler, index, modrm):
    pass


def _Mw(instr, base, assembler, index, modrm):
    pass


def _Sw(instr, base, assembler, index, modrm):
    pass


def _M(instr, base, assembler, index, modrm):
    if instr.tokens[index] == '[':
        try:
            end_index = instr.tokens.index(']', index+1)
        except ValueError:
            raise InvalidOpCodeArguments(instr)
        try:
            modrm['mod'], modrm['rm'], delta, modrm['displacement'] = _get_modrm_mod(
                tuple(instr.tokens[index+1:end_index]))
            return 2 + delta, base,  b'' if 'reg' not in modrm else _build_modrm(assembler, base, modrm)
        except InvalidOpCodeArguments:
            return None


def _Evq(instr, base, assembler, index, modrm):
    pass


def _Ap(instr, base, assembler, index, modrm):
    pass


def _Ob(instr, base, assembler, index, modrm):
    pass


def _Ovqp(instr, base, assembler, index, modrm):
    pass


def _Zb(instr, base, assembler, index, modrm):
    pass


def _Ivqp(instr, base, assembler, index, modrm):
    if instr.tokens[index].upper() not in ALL_REGS + ('[', ']'):
        if 'bits' in modrm:
            if modrm['bits'] == 16:
                return 1, base, pack_le16u(assembler.parse_integer_or_label(
                    instr.tokens[index], size=2, bits_size=16, offset=len(base)))
            if modrm['bits'] == 32:
                return 1, base, pack_le32u(assembler.parse_integer_or_label(
                    instr.tokens[index], size=4, bits_size=32, offset=len(base)))
            if modrm['bits'] == 64:
                return 1, base, pack_le64u(assembler.parse_integer_or_label(
                    instr.tokens[index], size=8, bits_size=64, offset=len(base)))


def _Iw(instr, base, assembler, index, modrm):
    pass


def _3(instr, base, assembler, index, modrm):
    pass


def _Msr(instr, base, assembler, index, modrm):
    pass


def _ESsr(instr, base, assembler, index, modrm):
    pass


def _Me(instr, base, assembler, index, modrm):
    pass


def _Yb(instr, base, assembler, index, modrm):
    pass


def _Ywo(instr, base, assembler, index, modrm):
    pass


def _Yv(instr, base, assembler, index, modrm):
    pass


def _Xb(instr, base, assembler, index, modrm):
    pass


def _Xwo(instr, base, assembler, index, modrm):
    pass


def _Xv(instr, base, assembler, index, modrm):
    pass


def _Yvqp(instr, base, assembler, index, modrm):
    pass


def _Xvqp(instr, base, assembler, index, modrm):
    pass


def _I(instr, base, assembler, index, modrm):
    pass


def _BBb(instr, base, assembler, index, modrm):
    pass


def _Mdi(instr, base, assembler, index, modrm):
    pass


def _Mer(instr, base, assembler, index, modrm):
    pass


def _Mdr(instr, base, assembler, index, modrm):
    pass


def _Mqi(instr, base, assembler, index, modrm):
    pass


def _Mst(instr, base, assembler, index, modrm):
    pass


def _Mwi(instr, base, assembler, index, modrm):
    pass


def _Mbcd(instr, base, assembler, index, modrm):
    pass


def _AX(instr, base, assembler, index, modrm):
    pass


def _eAX(instr, base, assembler, index, modrm):
    pass


def _Jvds(instr, base, assembler, index, modrm):
    if instr.tokens[index].upper() not in ALL_REGS + ('[', ']'):
        if assembler.bits == 16:
            return 1, base, pack_le16u(assembler.parse_integer_or_label(
                instr.tokens[index],
                relative=assembler.pc + len(base) + 2,
                size=2, bits_size=16, offset=len(base)))

        if assembler.bits in (32, 64):
            return 1, base, pack_le32u(assembler.parse_integer_or_label(
                instr.tokens[index],
                relative=assembler.pc + len(base) + 4,
                size=2, bits_size=16, offset=len(base)))


def _Eq(instr, base, assembler, index, modrm):
    pass


def _Mptp(instr, base, assembler, index, modrm):
    pass


def _Ms(instr, base, assembler, index, modrm):
    if match(instr.tokens[index:index+3], '[', None, ']'):
        if instr.tokens[index+1].upper() not in ALL_REGS:
            modrm['reg'] = 0
            modrm['mod'] = 0
            modrm['rm'] = 6
            if assembler.bits == 16:
                return 3, base, _build_modrm(assembler, base, modrm) + pack_le16u(assembler.parse_integer_or_label(
                    instr.tokens[index+1], size=2, bits_size=16, offset=len(base)))
            elif assembler.bits == 32:
                return 3, base, _build_modrm(assembler, base, modrm) + pack_le32u(assembler.parse_integer_or_label(
                    instr.tokens[index+1], size=4, bits_size=32, offset=len(base)))
            elif assembler.bits == 64:
                return 3, base, _build_modrm(assembler, base, modrm) + pack_le64u(assembler.parse_integer_or_label(
                    instr.tokens[index+1], size=8, bits_size=64, offset=len(base)))


def _Rv(instr, base, assembler, index, modrm):
    pass


def _Vps(instr, base, assembler, index, modrm):
    pass


def _Wps(instr, base, assembler, index, modrm):
    pass


def _Vss(instr, base, assembler, index, modrm):
    pass


def _Wss(instr, base, assembler, index, modrm):
    pass


def _Vpd(instr, base, assembler, index, modrm):
    pass


def _Wpd(instr, base, assembler, index, modrm):
    pass


def _Vsd(instr, base, assembler, index, modrm):
    pass


def _Wsd(instr, base, assembler, index, modrm):
    pass


def _Vq(instr, base, assembler, index, modrm):
    pass


def _Uq(instr, base, assembler, index, modrm):
    pass


def _Mq(instr, base, assembler, index, modrm):
    pass


def _Wq(instr, base, assembler, index, modrm):
    pass


def _Mb(instr, base, assembler, index, modrm):
    pass


def _Rd(instr, base, assembler, index, modrm):
    reg = instr.tokens[index].upper()
    if reg in REGS32:
        modrm['mod'] = 3
        modrm['rm'] = REGS32.index(reg)
        return 1, base, b'' if 'reg' not in modrm else _build_modrm(assembler, base, modrm)


def _Cd(instr, base, assembler, index, modrm):
    reg = instr.tokens[index].upper()
    if reg in CREGS:
        modrm['reg'] = CREGS.index(reg)
        if index > 1:
            return 1, base, _build_modrm(assembler, base, modrm)
        return 1, base, b''


def _Hd(instr, base, assembler, index, modrm):
    pass


def _Rq(instr, base, assembler, index, modrm):
    pass


def _Cq(instr, base, assembler, index, modrm):
    pass


def _Hq(instr, base, assembler, index, modrm):
    pass


def _Dd(instr, base, assembler, index, modrm):
    pass


def _Dq(instr, base, assembler, index, modrm):
    pass


def _Td(instr, base, assembler, index, modrm):
    pass


def _Qpi(instr, base, assembler, index, modrm):
    pass


def _Edqp(instr, base, assembler, index, modrm):
    pass


def _Mps(instr, base, assembler, index, modrm):
    pass


def _Mpd(instr, base, assembler, index, modrm):
    pass


def _Ppi(instr, base, assembler, index, modrm):
    pass


def _Wpsq(instr, base, assembler, index, modrm):
    pass


def _Pq(instr, base, assembler, index, modrm):
    pass


def _Qq(instr, base, assembler, index, modrm):
    pass


def _Vdq(instr, base, assembler, index, modrm):
    pass


def _Wdq(instr, base, assembler, index, modrm):
    pass


def _Udq(instr, base, assembler, index, modrm):
    pass


def _Md(instr, base, assembler, index, modrm):
    pass


def _Mdq(instr, base, assembler, index, modrm):
    pass


def _Gd(instr, base, assembler, index, modrm):
    pass


def _Gq(instr, base, assembler, index, modrm):
    pass


def _Mvqp(instr, base, assembler, index, modrm):
    pass


def _Rdqp(instr, base, assembler, index, modrm):
    pass


def _Eqp(instr, base, assembler, index, modrm):
    pass


def _Ups(instr, base, assembler, index, modrm):
    pass


def _Upd(instr, base, assembler, index, modrm):
    pass


def _Qd(instr, base, assembler, index, modrm):
    pass


def _Nq(instr, base, assembler, index, modrm):
    pass


def _Edq(instr, base, assembler, index, modrm):
    pass


def _Mstx(instr, base, assembler, index, modrm):
    pass


def _G(instr, base, assembler, index, modrm):
    pass


def _Mdqp(instr, base, assembler, index, modrm):
    pass


OPCODES_TABLE = (
    (0x0, 'ADD', _Eb, _Gb),
    (0x1, 'ADD', _Evqp, _Gvqp),
    (0x2, 'ADD', _Gb, _Eb),
    (0x3, 'ADD', _Gvqp, _Evqp),
    (0x4, 'ADD', _AL, _Ib),
    (0x5, 'ADD', _rAX, _Ivds),
    (0x8, 'OR', _Eb, _Gb),
    (0x9, 'OR', _Evqp, _Gvqp),
    (0xa, 'OR', _Gb, _Eb),
    (0xb, 'OR', _Gvqp, _Evqp),
    (0xc, 'OR', _AL, _Ib),
    (0xd, 'OR', _rAX, _Ivds),
    (0x10, 'ADC', _Eb, _Gb),
    (0x11, 'ADC', _Evqp, _Gvqp),
    (0x12, 'ADC', _Gb, _Eb),
    (0x13, 'ADC', _Gvqp, _Evqp),
    (0x14, 'ADC', _AL, _Ib),
    (0x15, 'ADC', _rAX, _Ivds),
    (0x18, 'SBB', _Eb, _Gb),
    (0x19, 'SBB', _Evqp, _Gvqp),
    (0x1a, 'SBB', _Gb, _Eb),
    (0x1b, 'SBB', _Gvqp, _Evqp),
    (0x1c, 'SBB', _AL, _Ib),
    (0x1d, 'SBB', _rAX, _Ivds),
    (0x20, 'AND', _Eb, _Gb),
    (0x21, 'AND', _Evqp, _Gvqp),
    (0x22, 'AND', _Gb, _Eb),
    (0x23, 'AND', _Gvqp, _Evqp),
    (0x24, 'AND', _AL, _Ib),
    (0x25, 'AND', _rAX, _Ivds),
    (0x27, 'DAA'),
    (0x28, 'SUB', _Eb, _Gb),
    (0x29, 'SUB', _Evqp, _Gvqp),
    (0x2a, 'SUB', _Gb, _Eb),
    (0x2b, 'SUB', _Gvqp, _Evqp),
    (0x2c, 'SUB', _AL, _Ib),
    (0x2d, 'SUB', _rAX, _Ivds),
    (0x2e, 'NTAKEN'),
    (0x2f, 'DAS'),
    (0x30, 'XOR', _Eb, _Gb),
    (0x31, 'XOR', _Evqp, _Gvqp),
    (0x32, 'XOR', _Gb, _Eb),
    (0x33, 'XOR', _Gvqp, _Evqp),
    (0x34, 'XOR', _AL, _Ib),
    (0x35, 'XOR', _rAX, _Ivds),
    (0x37, 'AAA'),
    (0x38, 'CMP', _Eb),
    (0x39, 'CMP', _Evqp),
    (0x3a, 'CMP', _Gb),
    (0x3b, 'CMP', _Gvqp),
    (0x3c, 'CMP', _AL),
    (0x3d, 'CMP', _rAX),
    (0x3e, 'TAKEN'),
    (0x3f, 'AAS'),
    (0x40, 'INC', _Zv),
    (0x40, 'REX'),
    (0x41, 'REX.B'),
    (0x42, 'REX.X'),
    (0x43, 'REX.XB'),
    (0x44, 'REX.R'),
    (0x45, 'REX.RB'),
    (0x46, 'REX.RX'),
    (0x47, 'REX.RXB'),
    (0x48, 'DEC', _Zv),
    (0x48, 'REX.W'),
    (0x49, 'REX.WB'),
    (0x4a, 'REX.WX'),
    (0x4b, 'REX.WXB'),
    (0x4c, 'REX.WR'),
    (0x4d, 'REX.WRB'),
    (0x4e, 'REX.WRX'),
    (0x4f, 'REX.WRXB'),
    (0x50, 'PUSH', _Zv),
    (0x50, 'PUSH', _Zvq),
    (0x58, 'POP', _Zv),
    (0x58, 'POP', _Zvq),
    (0x60, 'PUSHA'),
    (0x60, 'PUSHAD'),
    (0x61, 'POPA'),
    (0x61, 'POPAD'),
    (0x62, 'BOUND', _Gv),
    (0x63, 'ARPL', _Ew),
    (0x63, 'MOVSXD', _Gdqp, _Ed),
    (0x64, 'ALTER'),
    (0x68, 'PUSH', _Ivs),
    (0x69, 'IMUL', _Gvqp, _Evqp),
    (0x6a, 'PUSH', _Ibss),
    (0x6b, 'IMUL', _Gvqp, _Evqp),
    (0x6c, 'INS', _Yb, _DX),
    (0x6c, 'INSB'),
    (0x6d, 'INS', _Ywo, _DX),
    (0x6d, 'INSW'),
    (0x6d, 'INS', _Yv, _DX),
    (0x6d, 'INSD'),
    (0x6e, 'OUTS', _DX, _Xb),
    (0x6e, 'OUTSB'),
    (0x6f, 'OUTS', _DX, _Xwo),
    (0x6f, 'OUTSW'),
    (0x6f, 'OUTS', _DX, _Xv),
    (0x6f, 'OUTSD'),
    (0x70, 'JO', _Jbs),
    (0x71, 'JNO', _Jbs),
    (0x72, 'JB', _Jbs),
    (0x72, 'JNAE', _Jbs),
    (0x72, 'JC', _Jbs),
    (0x73, 'JNB', _Jbs),
    (0x73, 'JAE', _Jbs),
    (0x73, 'JNC', _Jbs),
    (0x74, 'JZ', _Jbs),
    (0x74, 'JE', _Jbs),
    (0x75, 'JNZ', _Jbs),
    (0x75, 'JNE', _Jbs),
    (0x76, 'JBE', _Jbs),
    (0x76, 'JNA', _Jbs),
    (0x77, 'JNBE', _Jbs),
    (0x77, 'JA', _Jbs),
    (0x78, 'JS', _Jbs),
    (0x79, 'JNS', _Jbs),
    (0x7a, 'JP', _Jbs),
    (0x7a, 'JPE', _Jbs),
    (0x7b, 'JNP', _Jbs),
    (0x7b, 'JPO', _Jbs),
    (0x7c, 'JL', _Jbs),
    (0x7c, 'JNGE', _Jbs),
    (0x7d, 'JNL', _Jbs),
    (0x7d, 'JGE', _Jbs),
    (0x7e, 'JLE', _Jbs),
    (0x7e, 'JNG', _Jbs),
    (0x7f, 'JNLE', _Jbs),
    (0x7f, 'JG', _Jbs),
    (0x80, 'ADD', _Eb, _Ib),
    (0x80, 'OR', _Eb, _Ib),
    (0x80, 'ADC', _Eb, _Ib),
    (0x80, 'SBB', _Eb, _Ib),
    (0x80, 'AND', _Eb, _Ib),
    (0x80, 'SUB', _Eb, _Ib),
    (0x80, 'XOR', _Eb, _Ib),
    (0x80, 'CMP', _Eb),
    (0x81, 'ADD', _Evqp, _Ivds),
    (0x81, 'OR', _Evqp, _Ivds),
    (0x81, 'ADC', _Evqp, _Ivds),
    (0x81, 'SBB', _Evqp, _Ivds),
    (0x81, 'AND', _Evqp, _Ivds),
    (0x81, 'SUB', _Evqp, _Ivds),
    (0x81, 'XOR', _Evqp, _Ivds),
    (0x81, 'CMP', _Evqp),
    (0x82, 'ADD', _Eb, _Ib),
    (0x82, 'OR', _Eb, _Ib),
    (0x82, 'ADC', _Eb, _Ib),
    (0x82, 'SBB', _Eb, _Ib),
    (0x82, 'AND', _Eb, _Ib),
    (0x82, 'SUB', _Eb, _Ib),
    (0x82, 'XOR', _Eb, _Ib),
    (0x82, 'CMP', _Eb),
    (0x83, 'ADD', _Evqp, _Ibs),
    (0x83, 'OR', _Evqp, _Ibs),
    (0x83, 'ADC', _Evqp, _Ibs),
    (0x83, 'SBB', _Evqp, _Ibs),
    (0x83, 'AND', _Evqp, _Ibs),
    (0x83, 'SUB', _Evqp, _Ibs),
    (0x83, 'XOR', _Evqp, _Ibs),
    (0x83, 'CMP', _Evqp),
    (0x84, 'TEST', _Eb),
    (0x85, 'TEST', _Evqp),
    (0x86, 'XCHG', _Gb),
    (0x87, 'XCHG', _Gvqp),
    (0x88, 'MOV', _Eb, _Gb),
    (0x89, 'MOV', _Evqp, _Gvqp),
    (0x8a, 'MOV', _Gb, _Eb),
    (0x8b, 'MOV', _Gvqp, _Evqp),
    (0x8c, 'MOV', _Mw, _Sw),
    (0x8c, 'MOV', _Rvqp, _Sw),
    (0x8d, 'LEA', _Gvqp, _M),
    (0x8e, 'MOV', _Sw, _Ew),
    (0x8f, 'POP', _Ev),
    (0x8f, 'POP', _Evq),
    (0x90, 'XCHG', _Zvqp),
    (0x90, 'NOP'),
    (0x90, 'NOP'),
    (0x90, 'PAUSE'),
    (0x98, 'CBW'),
    (0x98, 'CWDE'),
    (0x98, 'CBW'),
    (0x98, 'CWDE'),
    (0x98, 'CDQE'),
    (0x99, 'CWD'),
    (0x99, 'CDQ'),
    (0x99, 'CWD'),
    (0x99, 'CDQ'),
    (0x99, 'CQO'),
    (0x9a, 'CALLF', _Ap),
    (0x9b, 'FWAIT'),
    (0x9b, 'WAIT'),
    (0x9c, 'PUSHF'),
    (0x9c, 'PUSHFD'),
    (0x9c, 'PUSHF'),
    (0x9c, 'PUSHFQ'),
    (0x9d, 'POPF'),
    (0x9d, 'POPFD'),
    (0x9d, 'POPF'),
    (0x9d, 'POPFQ'),
    (0x9e, 'SAHF'),
    (0x9f, 'LAHF'),
    (0xa0, 'MOV', _AL, _Ob),
    (0xa1, 'MOV', _rAX, _Ovqp),
    (0xa2, 'MOV', _Ob, _AL),
    (0xa3, 'MOV', _Ovqp, _rAX),
    (0xa4, 'MOVS', _Yb, _Xb),
    (0xa4, 'MOVSB'),
    (0xa5, 'MOVS', _Ywo, _Xwo),
    (0xa5, 'MOVSW'),
    (0xa5, 'MOVS', _Yv, _Xv),
    (0xa5, 'MOVSD'),
    (0xa5, 'MOVS', _Yvqp, _Xvqp),
    (0xa5, 'MOVSW'),
    (0xa5, 'MOVSD'),
    (0xa5, 'MOVSQ'),
    (0xa6, 'CMPS', _Yb),
    (0xa6, 'CMPSB'),
    (0xa7, 'CMPS', _Ywo),
    (0xa7, 'CMPSW'),
    (0xa7, 'CMPS', _Yv),
    (0xa7, 'CMPSD'),
    (0xa7, 'CMPS', _Yvqp),
    (0xa7, 'CMPSW'),
    (0xa7, 'CMPSD'),
    (0xa7, 'CMPSQ'),
    (0xa8, 'TEST', _AL),
    (0xa9, 'TEST', _rAX),
    (0xaa, 'STOS', _Yb),
    (0xaa, 'STOSB'),
    (0xab, 'STOS', _Ywo),
    (0xab, 'STOSW'),
    (0xab, 'STOS', _Yv),
    (0xab, 'STOSD'),
    (0xab, 'STOS', _Yvqp),
    (0xab, 'STOSW'),
    (0xab, 'STOSD'),
    (0xab, 'STOSQ'),
    (0xac, 'LODS', _Xb),
    (0xac, 'LODSB'),
    (0xad, 'LODS', _Xwo),
    (0xad, 'LODSW'),
    (0xad, 'LODS', _Xv),
    (0xad, 'LODSD'),
    (0xad, 'LODS', _Xvqp),
    (0xad, 'LODSW'),
    (0xad, 'LODSD'),
    (0xad, 'LODSQ'),
    (0xae, 'SCAS', _Yb),
    (0xae, 'SCASB'),
    (0xaf, 'SCAS', _Ywo),
    (0xaf, 'SCASW'),
    (0xaf, 'SCAS', _Yv),
    (0xaf, 'SCASD'),
    (0xaf, 'SCAS', _Yvqp),
    (0xaf, 'SCASW'),
    (0xaf, 'SCASD'),
    (0xaf, 'SCASQ'),
    (0xb0, 'MOV', _Zb, _Ib),
    (0xb8, 'MOV', _Zvqp, _Ivqp),
    (0xc0, 'ROL', _Eb, _Ib),
    (0xc0, 'ROR', _Eb, _Ib),
    (0xc0, 'RCL', _Eb, _Ib),
    (0xc0, 'RCR', _Eb, _Ib),
    (0xc0, 'SHL', _Eb, _Ib),
    (0xc0, 'SAL', _Eb, _Ib),
    (0xc0, 'SHR', _Eb, _Ib),
    (0xc0, 'SAL', _Eb, _Ib),
    (0xc0, 'SHL', _Eb, _Ib),
    (0xc0, 'SAR', _Eb, _Ib),
    (0xc1, 'ROL', _Evqp, _Ib),
    (0xc1, 'ROR', _Evqp, _Ib),
    (0xc1, 'RCL', _Evqp, _Ib),
    (0xc1, 'RCR', _Evqp, _Ib),
    (0xc1, 'SHL', _Evqp, _Ib),
    (0xc1, 'SAL', _Evqp, _Ib),
    (0xc1, 'SHR', _Evqp, _Ib),
    (0xc1, 'SAL', _Evqp, _Ib),
    (0xc1, 'SHL', _Evqp, _Ib),
    (0xc1, 'SAR', _Evqp, _Ib),
    (0xc2, 'RETN'),
    (0xc3, 'RETN'),
    (0xc3, 'RET'),
    (0xc6, 'MOV', _Eb, _Ib),
    (0xc7, 'MOV', _Evqp, _Ivds),
    (0xc8, 'ENTER', _Iw),
    (0xc8, 'ENTER', _Iw),
    (0xc9, 'LEAVE'),
    (0xc9, 'LEAVE'),
    (0xca, 'RETF', _Iw),
    (0xcb, 'RETF'),
    (0xcc, 'INT', _I),
    (0xcd, 'INT', _Ib),
    (0xce, 'INTO'),
    (0xcf, 'IRET'),
    (0xcf, 'IRETD'),
    (0xcf, 'IRET'),
    (0xcf, 'IRETD'),
    (0xcf, 'IRETQ'),
    (0xd0, 'ROL', _Eb, _I),
    (0xd0, 'ROR', _Eb, _I),
    (0xd0, 'RCL', _Eb, _I),
    (0xd0, 'RCR', _Eb, _I),
    (0xd0, 'SHL', _Eb, _I),
    (0xd0, 'SAL', _Eb, _I),
    (0xd0, 'SHR', _Eb, _I),
    (0xd0, 'SAL', _Eb, _I),
    (0xd0, 'SHL', _Eb, _I),
    (0xd0, 'SAR', _Eb, _I),
    (0xd1, 'ROL', _Evqp, _I),
    (0xd1, 'ROR', _Evqp, _I),
    (0xd1, 'RCL', _Evqp, _I),
    (0xd1, 'RCR', _Evqp, _I),
    (0xd1, 'SHL', _Evqp, _I),
    (0xd1, 'SAL', _Evqp, _I),
    (0xd1, 'SHR', _Evqp, _I),
    (0xd1, 'SAL', _Evqp, _I),
    (0xd1, 'SHL', _Evqp, _I),
    (0xd1, 'SAR', _Evqp, _I),
    (0xd2, 'ROL', _Eb, _CL),
    (0xd2, 'ROR', _Eb, _CL),
    (0xd2, 'RCL', _Eb, _CL),
    (0xd2, 'RCR', _Eb, _CL),
    (0xd2, 'SHL', _Eb, _CL),
    (0xd2, 'SAL', _Eb, _CL),
    (0xd2, 'SHR', _Eb, _CL),
    (0xd2, 'SAL', _Eb, _CL),
    (0xd2, 'SHL', _Eb, _CL),
    (0xd2, 'SAR', _Eb, _CL),
    (0xd3, 'ROL', _Evqp, _CL),
    (0xd3, 'ROR', _Evqp, _CL),
    (0xd3, 'RCL', _Evqp, _CL),
    (0xd3, 'RCR', _Evqp, _CL),
    (0xd3, 'SHL', _Evqp, _CL),
    (0xd3, 'SAL', _Evqp, _CL),
    (0xd3, 'SHR', _Evqp, _CL),
    (0xd3, 'SAL', _Evqp, _CL),
    (0xd3, 'SHL', _Evqp, _CL),
    (0xd3, 'SAR', _Evqp, _CL),
    (0xd4, 'AAM'),
    (0xd4, 'AMX', _Ib),
    (0xd5, 'AAD'),
    (0xd5, 'ADX', _Ib),
    (0xd6, 'SALC'),
    (0xd6, 'SETALC'),
    (0xd7, 'XLAT', _BBb),
    (0xd7, 'XLATB'),
    (0xd8, 'FADD', _Msr),
    (0xd8, 'FADD', _ST, _EST),
    (0xd8, 'FMUL', _Msr),
    (0xd8, 'FMUL', _ST, _EST),
    (0xd8, 'FCOM'),
    (0xd8, 'FCOM'),
    (0xd8, 'FCOMP'),
    (0xd8, 'FCOMP'),
    (0xd8, 'FSUB', _Msr),
    (0xd8, 'FSUB', _ST, _EST),
    (0xd8, 'FSUBR', _Msr),
    (0xd8, 'FSUBR', _ST, _EST),
    (0xd8, 'FDIV', _Msr),
    (0xd8, 'FDIV', _ST, _EST),
    (0xd8, 'FDIVR', _Msr),
    (0xd8, 'FDIVR', _ST, _EST),
    (0xd9, 'FLD', _ESsr),
    (0xd9, 'FXCH'),
    (0xd9, 'FXCH'),
    (0xd9, 'FST', _Msr),
    (0xd9, 'FNOP'),
    (0xd9, 'FSTP', _Msr),
    (0xd9, 'FSTP1', _EST),
    (0xd9, 'FSTP1', _EST),
    (0xd9, 'FLDENV', _Me),
    (0xd9, 'FCHS'),
    (0xd9, 'FABS'),
    (0xd9, 'FTST'),
    (0xd9, 'FXAM'),
    (0xd9, 'FLDCW', _Mw),
    (0xd9, 'FLD1'),
    (0xd9, 'FLDL2T'),
    (0xd9, 'FLDL2E'),
    (0xd9, 'FLDPI'),
    (0xd9, 'FLDLG2'),
    (0xd9, 'FLDLN2'),
    (0xd9, 'FLDZ'),
    (0xd9, 'FNSTENV', _Me),
    (0xd9, 'FSTENV', _Me),
    (0xd9, 'F2XM1'),
    (0xd9, 'FYL2X'),
    (0xd9, 'FPTAN'),
    (0xd9, 'FPATAN'),
    (0xd9, 'FXTRACT'),
    (0xd9, 'FPREM1'),
    (0xd9, 'FDECSTP'),
    (0xd9, 'FINCSTP'),
    (0xd9, 'FNSTCW', _Mw),
    (0xd9, 'FSTCW', _Mw),
    (0xd9, 'FPREM'),
    (0xd9, 'FYL2XP1'),
    (0xd9, 'FSQRT'),
    (0xd9, 'FSINCOS'),
    (0xd9, 'FRNDINT'),
    (0xd9, 'FSCALE'),
    (0xd9, 'FSIN'),
    (0xd9, 'FCOS'),
    (0xda, 'FIADD', _Mdi),
    (0xda, 'FCMOVB', _ST, _EST),
    (0xda, 'FIMUL', _Mdi),
    (0xda, 'FCMOVE', _ST, _EST),
    (0xda, 'FICOM'),
    (0xda, 'FCMOVBE', _ST, _EST),
    (0xda, 'FICOMP'),
    (0xda, 'FCMOVU', _ST, _EST),
    (0xda, 'FISUB', _Mdi),
    (0xda, 'FISUBR', _Mdi),
    (0xda, 'FUCOMPP'),
    (0xda, 'FIDIV', _Mdi),
    (0xda, 'FIDIVR', _Mdi),
    (0xdb, 'FILD', _Mdi),
    (0xdb, 'FCMOVNB', _ST, _EST),
    (0xdb, 'FISTTP', _Mdi),
    (0xdb, 'FCMOVNE', _ST, _EST),
    (0xdb, 'FIST', _Mdi),
    (0xdb, 'FCMOVNBE', _ST, _EST),
    (0xdb, 'FISTP', _Mdi),
    (0xdb, 'FCMOVNU', _ST, _EST),
    (0xdb, 'FNENI'),
    (0xdb, 'FENI'),
    (0xdb, 'FNENI'),
    (0xdb, 'FNDISI'),
    (0xdb, 'FDISI'),
    (0xdb, 'FNDISI'),
    (0xdb, 'FNCLEX'),
    (0xdb, 'FCLEX'),
    (0xdb, 'FNINIT'),
    (0xdb, 'FINIT'),
    (0xdb, 'FNSETPM'),
    (0xdb, 'FSETPM'),
    (0xdb, 'FNSETPM'),
    (0xdb, 'FLD', _Mer),
    (0xdb, 'FUCOMI', _ST),
    (0xdb, 'FCOMI', _ST),
    (0xdb, 'FSTP', _Mer),
    (0xdc, 'FADD', _Mdr),
    (0xdc, 'FADD', _EST, _ST),
    (0xdc, 'FMUL', _Mdr),
    (0xdc, 'FMUL', _EST, _ST),
    (0xdc, 'FCOM'),
    (0xdc, 'FCOM2'),
    (0xdc, 'FCOM2'),
    (0xdc, 'FCOMP'),
    (0xdc, 'FCOMP3'),
    (0xdc, 'FCOMP3'),
    (0xdc, 'FSUB', _Mdr),
    (0xdc, 'FSUBR', _EST, _ST),
    (0xdc, 'FSUBR', _Mdr),
    (0xdc, 'FSUB', _EST, _ST),
    (0xdc, 'FDIV', _Mdr),
    (0xdc, 'FDIVR', _EST, _ST),
    (0xdc, 'FDIVR', _Mdr),
    (0xdc, 'FDIV', _EST, _ST),
    (0xdd, 'FLD', _Mdr),
    (0xdd, 'FFREE', _EST),
    (0xdd, 'FISTTP', _Mqi),
    (0xdd, 'FXCH4'),
    (0xdd, 'FXCH4'),
    (0xdd, 'FST', _Mdr),
    (0xdd, 'FST', _EST),
    (0xdd, 'FSTP', _Mdr),
    (0xdd, 'FSTP', _EST),
    (0xdd, 'FRSTOR', _Mst),
    (0xdd, 'FUCOM'),
    (0xdd, 'FUCOM'),
    (0xdd, 'FUCOMP'),
    (0xdd, 'FUCOMP'),
    (0xdd, 'FNSAVE', _Mst),
    (0xdd, 'FSAVE', _Mst),
    (0xdd, 'FNSTSW', _Mw),
    (0xdd, 'FSTSW', _Mw),
    (0xde, 'FIADD', _Mwi),
    (0xde, 'FADDP', _EST, _ST),
    (0xde, 'FADDP'),
    (0xde, 'FIMUL', _Mwi),
    (0xde, 'FMULP', _EST, _ST),
    (0xde, 'FMULP'),
    (0xde, 'FICOM'),
    (0xde, 'FCOMP5'),
    (0xde, 'FCOMP5'),
    (0xde, 'FICOMP'),
    (0xde, 'FCOMPP'),
    (0xde, 'FISUB', _Mwi),
    (0xde, 'FSUBRP', _EST, _ST),
    (0xde, 'FSUBRP'),
    (0xde, 'FISUBR', _Mwi),
    (0xde, 'FSUBP', _EST, _ST),
    (0xde, 'FSUBP'),
    (0xde, 'FIDIV', _Mwi),
    (0xde, 'FDIVRP', _EST, _ST),
    (0xde, 'FDIVRP'),
    (0xde, 'FIDIVR', _Mwi),
    (0xde, 'FDIVP', _EST, _ST),
    (0xde, 'FDIVP'),
    (0xdf, 'FILD', _Mwi),
    (0xdf, 'FFREEP', _EST),
    (0xdf, 'FISTTP', _Mwi),
    (0xdf, 'FXCH7'),
    (0xdf, 'FXCH7'),
    (0xdf, 'FIST', _Mwi),
    (0xdf, 'FSTP8', _EST),
    (0xdf, 'FSTP8', _EST),
    (0xdf, 'FISTP', _Mwi),
    (0xdf, 'FSTP9', _EST),
    (0xdf, 'FSTP9', _EST),
    (0xdf, 'FBLD', _Mbcd),
    (0xdf, 'FNSTSW', _AX),
    (0xdf, 'FSTSW', _AX),
    (0xdf, 'FILD', _Mqi),
    (0xdf, 'FUCOMIP', _ST),
    (0xdf, 'FBSTP', _Mbcd),
    (0xdf, 'FCOMIP', _ST),
    (0xdf, 'FISTP', _Mqi),
    (0xe0, 'LOOPNZ', _Jbs),
    (0xe0, 'LOOPNE', _Jbs),
    (0xe0, 'LOOPNZ', _Jbs),
    (0xe0, 'LOOPNE', _Jbs),
    (0xe1, 'LOOPZ', _Jbs),
    (0xe1, 'LOOPE', _Jbs),
    (0xe1, 'LOOPZ', _Jbs),
    (0xe1, 'LOOPE', _Jbs),
    (0xe2, 'LOOP', _Jbs),
    (0xe2, 'LOOP', _Jbs),
    (0xe3, 'JCXZ', _Jbs),
    (0xe3, 'JECXZ', _Jbs),
    (0xe3, 'JECXZ', _Jbs),
    (0xe3, 'JRCXZ', _Jbs),
    (0xe4, 'IN', _AL, _Ib),
    (0xe5, 'IN', _eAX, _Ib),
    (0xe6, 'OUT', _Ib, _AL),
    (0xe7, 'OUT', _Ib, _eAX),
    (0xe8, 'CALL', _Jvds),
    (0xe9, 'JMP', _Jvds),
    (0xea, 'JMPF', _Ap),
    (0xeb, 'JMP', _Jbs),
    (0xec, 'IN', _AL, _DX),
    (0xed, 'IN', _eAX, _DX),
    (0xee, 'OUT', _DX, _AL),
    (0xef, 'OUT', _DX, _eAX),
    (0xf0, 'LOCK'),
    (0xf1, 'INT1'),
    (0xf1, 'ICEBP'),
    (0xf2, 'REPNZ'),
    (0xf2, 'REPNE'),
    (0xf3, 'REPZ'),
    (0xf3, 'REPE'),
    (0xf3, 'REP'),
    (0xf3, 'REPZ'),
    (0xf3, 'REPE'),
    (0xf3, 'REP'),
    (0xf4, 'HLT'),
    (0xf5, 'CMC'),
    (0xf6, 'TEST', _Eb),
    (0xf6, 'TEST', _Eb),
    (0xf6, 'NOT', _Eb),
    (0xf6, 'NEG', _Eb),
    (0xf6, 'MUL'),
    (0xf6, 'IMUL'),
    (0xf6, 'DIV'),
    (0xf6, 'IDIV'),
    (0xf7, 'TEST', _Evqp),
    (0xf7, 'TEST', _Evqp),
    (0xf7, 'NOT', _Evqp),
    (0xf7, 'NEG', _Evqp),
    (0xf7, 'MUL', _Evqp),
    (0xf7, 'IMUL', _Evqp),
    (0xf7, 'DIV', _Evqp),
    (0xf7, 'IDIV', _Evqp),
    (0xf8, 'CLC'),
    (0xf9, 'STC'),
    (0xfa, 'CLI'),
    (0xfb, 'STI'),
    (0xfc, 'CLD'),
    (0xfd, 'STD'),
    (0xfe, 'INC', _Eb),
    (0xfe, 'DEC', _Eb),
    (0xff, 'INC', _Evqp),
    (0xff, 'DEC', _Evqp),
    (0xff, 'CALL', _Ev),
    (0xff, 'CALL', _Eq),
    (0xff, 'CALLF', _Mptp),
    (0xff, 'JMP', _Ev),
    (0xff, 'JMP', _Eq),
    (0xff, 'JMPF', _Mptp),
    (0xff, 'PUSH', _Ev),
    (0xff, 'PUSH', _Evq),
    (0xf00, 'SLDT', _Mw),
    (0xf00, 'SLDT', _Rvqp),
    (0xf00, 'STR', _Mw),
    (0xf00, 'STR', _Rvqp),
    (0xf00, 'LLDT', _Ew),
    (0xf00, 'LTR', _Ew),
    (0xf00, 'VERR', _Ew),
    (0xf00, 'VERW', _Ew),
    (0xf00, 'JMPE'),
    (0xf01, 'SGDT', _Ms),
    (0xf01, 'VMCALL'),
    (0xf01, 'VMLAUNCH'),
    (0xf01, 'VMRESUME'),
    (0xf01, 'VMXOFF'),
    (0xf01, 'SIDT', _Ms),
    (0xf01, 'MONITOR'),
    (0xf01, 'MWAIT'),
    (0xf01, 'LGDT', _Ms),
    (0xf01, 'XGETBV'),
    (0xf01, 'XSETBV'),
    (0xf01, 'LIDT', _Ms),
    (0xf01, 'SMSW', _Mw),
    (0xf01, 'SMSW', _Rvqp),
    (0xf01, 'LMSW', _Ew),
    (0xf01, 'INVLPG', _M),
    (0xf01, 'SWAPGS'),
    (0xf01, 'RDTSCP'),
    (0xf02, 'LAR', _Gvqp, _Mw),
    (0xf02, 'LAR', _Gvqp, _Rv),
    (0xf03, 'LSL', _Gvqp, _Mw),
    (0xf03, 'LSL', _Gvqp, _Rv),
    (0xf05, 'LOADALL'),
    (0xf05, 'SYSCALL'),
    (0xf06, 'CLTS'),
    (0xf07, 'LOADALL'),
    (0xf07, 'SYSRET'),
    (0xf08, 'INVD'),
    (0xf09, 'WBINVD'),
    (0xf0b, 'UD2'),
    (0xf0d, 'NOP', _Ev),
    (0xf10, 'MOVUPS', _Vps, _Wps),
    (0xf10, 'MOVSS', _Vss, _Wss),
    (0xf10, 'MOVUPD', _Vpd, _Wpd),
    (0xf10, 'MOVSD', _Vsd, _Wsd),
    (0xf11, 'MOVUPS', _Wps, _Vps),
    (0xf11, 'MOVSS', _Wss, _Vss),
    (0xf11, 'MOVUPD', _Wpd, _Vpd),
    (0xf11, 'MOVSD', _Wsd, _Vsd),
    (0xf12, 'MOVHLPS', _Vq, _Uq),
    (0xf12, 'MOVLPS', _Vq, _Mq),
    (0xf12, 'MOVLPD', _Vq, _Mq),
    (0xf12, 'MOVDDUP', _Vq, _Wq),
    (0xf12, 'MOVSLDUP', _Vq, _Wq),
    (0xf13, 'MOVLPS', _Mq, _Vq),
    (0xf13, 'MOVLPD', _Mq, _Vq),
    (0xf14, 'UNPCKLPS', _Vps, _Wq),
    (0xf14, 'UNPCKLPD', _Vpd, _Wpd),
    (0xf15, 'UNPCKHPS', _Vps, _Wq),
    (0xf15, 'UNPCKHPD', _Vpd, _Wpd),
    (0xf16, 'MOVLHPS', _Vq, _Uq),
    (0xf16, 'MOVHPS', _Vq, _Mq),
    (0xf16, 'MOVHPD', _Vq, _Mq),
    (0xf16, 'MOVSHDUP', _Vq, _Wq),
    (0xf17, 'MOVHPS', _Mq, _Vq),
    (0xf17, 'MOVHPD', _Mq, _Vq),
    (0xf18, 'HINT_NOP', _Ev),
    (0xf18, 'PREFETCHNTA', _Mb),
    (0xf18, 'PREFETCHT0', _Mb),
    (0xf18, 'PREFETCHT1', _Mb),
    (0xf18, 'PREFETCHT2', _Mb),
    (0xf18, 'HINT_NOP', _Ev),
    (0xf18, 'HINT_NOP', _Ev),
    (0xf18, 'HINT_NOP', _Ev),
    (0xf18, 'HINT_NOP', _Ev),
    (0xf19, 'HINT_NOP', _Ev),
    (0xf1a, 'HINT_NOP', _Ev),
    (0xf1b, 'HINT_NOP', _Ev),
    (0xf1c, 'HINT_NOP', _Ev),
    (0xf1d, 'HINT_NOP', _Ev),
    (0xf1e, 'HINT_NOP', _Ev),
    (0xf1f, 'HINT_NOP', _Ev),
    (0xf1f, 'NOP', _Ev),
    (0xf1f, 'HINT_NOP', _Ev),
    (0xf1f, 'HINT_NOP', _Ev),
    (0xf1f, 'HINT_NOP', _Ev),
    (0xf1f, 'HINT_NOP', _Ev),
    (0xf1f, 'HINT_NOP', _Ev),
    (0xf1f, 'HINT_NOP', _Ev),
    (0xf1f, 'HINT_NOP', _Ev),
    (0xf20, 'MOV', _Rd, _Cd),
    (0xf20, 'MOV', _Hd, _Cd),
    (0xf20, 'MOV', _Rq, _Cq),
    (0xf20, 'MOV', _Hq, _Cq),
    (0xf21, 'MOV', _Rd, _Dd),
    (0xf21, 'MOV', _Hd, _Dd),
    (0xf21, 'MOV', _Rq, _Dq),
    (0xf21, 'MOV', _Hq, _Dq),
    (0xf22, 'MOV', _Cd, _Rd),
    (0xf22, 'MOV', _Cd, _Hd),
    (0xf22, 'MOV', _Cq, _Rq),
    (0xf22, 'MOV', _Cq, _Hq),
    (0xf23, 'MOV', _Dd, _Rd),
    (0xf23, 'MOV', _Dq, _Hq),
    (0xf23, 'MOV', _Dq, _Rq),
    (0xf23, 'MOV', _Dq, _Hq),
    (0xf24, 'MOV', _Rd, _Td),
    (0xf24, 'MOV', _Hd, _Td),
    (0xf26, 'MOV', _Td, _Rd),
    (0xf26, 'MOV', _Td, _Hd),
    (0xf28, 'MOVAPS', _Vps, _Wps),
    (0xf28, 'MOVAPD', _Vpd, _Wpd),
    (0xf29, 'MOVAPS', _Wps, _Vps),
    (0xf29, 'MOVAPD', _Wpd, _Vpd),
    (0xf2a, 'CVTPI2PS', _Vps, _Qpi),
    (0xf2a, 'CVTSI2SS', _Vss, _Edqp),
    (0xf2a, 'CVTPI2PD', _Vpd, _Qpi),
    (0xf2a, 'CVTSI2SD', _Vsd, _Edqp),
    (0xf2b, 'MOVNTPS', _Mps, _Vps),
    (0xf2b, 'MOVNTPD', _Mpd, _Vpd),
    (0xf2c, 'CVTTPS2PI', _Ppi, _Wpsq),
    (0xf2c, 'CVTTSS2SI', _Gdqp, _Wss),
    (0xf2c, 'CVTTPD2PI', _Ppi, _Wpd),
    (0xf2c, 'CVTTSD2SI', _Gdqp, _Wsd),
    (0xf2d, 'CVTPS2PI', _Ppi, _Wpsq),
    (0xf2d, 'CVTSS2SI', _Gdqp, _Wss),
    (0xf2d, 'CVTPD2PI', _Ppi, _Wpd),
    (0xf2d, 'CVTSD2SI', _Gdqp, _Wsd),
    (0xf2e, 'UCOMISS', _Vss),
    (0xf2e, 'UCOMISD', _Vsd),
    (0xf2f, 'COMISS', _Vss),
    (0xf2f, 'COMISD', _Vsd),
    (0xf30, 'WRMSR'),
    (0xf31, 'RDTSC'),
    (0xf32, 'RDMSR'),
    (0xf33, 'RDPMC'),
    (0xf34, 'SYSENTER'),
    (0xf34, 'SYSENTER'),
    (0xf35, 'SYSEXIT'),
    (0xf37, 'GETSEC'),
    (0xf38, 'PSHUFB', _Pq, _Qq),
    (0xf38, 'PSHUFB', _Vdq, _Wdq),
    (0xf38, 'PHADDW', _Pq, _Qq),
    (0xf38, 'PHADDW', _Vdq, _Wdq),
    (0xf38, 'PHADDD', _Pq, _Qq),
    (0xf38, 'PHADDD', _Vdq, _Wdq),
    (0xf38, 'PHADDSW', _Pq, _Qq),
    (0xf38, 'PHADDSW', _Vdq, _Wdq),
    (0xf38, 'PMADDUBSW', _Pq, _Qq),
    (0xf38, 'PMADDUBSW', _Vdq, _Wdq),
    (0xf38, 'PHSUBW', _Pq, _Qq),
    (0xf38, 'PHSUBW', _Vdq, _Wdq),
    (0xf38, 'PHSUBD', _Pq, _Qq),
    (0xf38, 'PHSUBD', _Vdq, _Wdq),
    (0xf38, 'PHSUBSW', _Pq, _Qq),
    (0xf38, 'PHSUBSW', _Vdq, _Wdq),
    (0xf38, 'PSIGNB', _Pq, _Qq),
    (0xf38, 'PSIGNB', _Vdq, _Wdq),
    (0xf38, 'PSIGNW', _Pq, _Qq),
    (0xf38, 'PSIGNW', _Vdq, _Wdq),
    (0xf38, 'PSIGND', _Pq, _Qq),
    (0xf38, 'PSIGND', _Vdq, _Wdq),
    (0xf38, 'PMULHRSW', _Pq, _Qq),
    (0xf38, 'PMULHRSW', _Vdq, _Wdq),
    (0xf38, 'PBLENDVB', _Vdq, _Wdq),
    (0xf38, 'BLENDVPS', _Vps, _Wps),
    (0xf38, 'BLENDVPD', _Vpd, _Wpd),
    (0xf38, 'PTEST', _Vdq),
    (0xf38, 'PABSB', _Pq, _Qq),
    (0xf38, 'PABSB', _Vdq, _Wdq),
    (0xf38, 'PABSW', _Pq, _Qq),
    (0xf38, 'PABSW', _Vdq, _Wdq),
    (0xf38, 'PABSD', _Pq, _Qq),
    (0xf38, 'PABSD', _Vdq, _Wdq),
    (0xf38, 'PMOVSXBW', _Vdq, _Mq),
    (0xf38, 'PMOVSXBW', _Vdq, _Udq),
    (0xf38, 'PMOVSXBD', _Vdq, _Md),
    (0xf38, 'PMOVSXBD', _Vdq, _Udq),
    (0xf38, 'PMOVSXBQ', _Vdq, _Mw),
    (0xf38, 'PMOVSXBQ', _Vdq, _Udq),
    (0xf38, 'PMOVSXWD', _Vdq, _Mq),
    (0xf38, 'PMOVSXWD', _Vdq, _Udq),
    (0xf38, 'PMOVSXWQ', _Vdq, _Md),
    (0xf38, 'PMOVSXWQ', _Vdq, _Udq),
    (0xf38, 'PMOVSXDQ', _Vdq, _Mq),
    (0xf38, 'PMOVSXDQ', _Vdq, _Udq),
    (0xf38, 'PMULDQ', _Vdq, _Wdq),
    (0xf38, 'PCMPEQQ', _Vdq, _Wdq),
    (0xf38, 'MOVNTDQA', _Vdq, _Mdq),
    (0xf38, 'PACKUSDW', _Vdq, _Wdq),
    (0xf38, 'PMOVZXBW', _Vdq, _Mq),
    (0xf38, 'PMOVZXBW', _Vdq, _Udq),
    (0xf38, 'PMOVZXBD', _Vdq, _Md),
    (0xf38, 'PMOVZXBD', _Vdq, _Udq),
    (0xf38, 'PMOVZXBQ', _Vdq, _Mw),
    (0xf38, 'PMOVZXBQ', _Vdq, _Udq),
    (0xf38, 'PMOVZXWD', _Vdq, _Mq),
    (0xf38, 'PMOVZXWD', _Vdq, _Udq),
    (0xf38, 'PMOVZXWQ', _Vdq, _Md),
    (0xf38, 'PMOVZXWQ', _Vdq, _Udq),
    (0xf38, 'PMOVZXDQ', _Vdq, _Mq),
    (0xf38, 'PMOVZXDQ', _Vdq, _Udq),
    (0xf38, 'PCMPGTQ', _Vdq, _Wdq),
    (0xf38, 'PMINSB', _Vdq, _Wdq),
    (0xf38, 'PMINSD', _Vdq, _Wdq),
    (0xf38, 'PMINUW', _Vdq, _Wdq),
    (0xf38, 'PMINUD', _Vdq, _Wdq),
    (0xf38, 'PMAXSB', _Vdq, _Wdq),
    (0xf38, 'PMAXSD', _Vdq, _Wdq),
    (0xf38, 'PMAXUW', _Vdq, _Wdq),
    (0xf38, 'PMAXUD', _Vdq, _Wdq),
    (0xf38, 'PMULLD', _Vdq, _Wdq),
    (0xf38, 'PHMINPOSUW', _Vdq, _Wdq),
    (0xf38, 'INVEPT', _Gd),
    (0xf38, 'INVEPT', _Gq),
    (0xf38, 'INVVPID', _Gd),
    (0xf38, 'INVVPID', _Gq),
    (0xf38, 'MOVBE', _Gvqp, _Mvqp),
    (0xf38, 'CRC32', _Gdqp, _Eb),
    (0xf38, 'MOVBE', _Mvqp, _Gvqp),
    (0xf38, 'CRC32', _Gdqp, _Evqp),
    (0xf3a, 'ROUNDPS', _Vps, _Wps),
    (0xf3a, 'ROUNDPD', _Vps, _Wpd),
    (0xf3a, 'ROUNDSS', _Vss, _Wss),
    (0xf3a, 'ROUNDSD', _Vsd, _Wsd),
    (0xf3a, 'BLENDPS', _Vps, _Wps),
    (0xf3a, 'BLENDPD', _Vpd, _Wpd),
    (0xf3a, 'PBLENDW', _Vdq, _Wdq),
    (0xf3a, 'PALIGNR', _Pq, _Qq),
    (0xf3a, 'PALIGNR', _Vdq, _Wdq),
    (0xf3a, 'PEXTRB', _Mb, _Vdq),
    (0xf3a, 'PEXTRB', _Rdqp, _Vdq),
    (0xf3a, 'PEXTRW', _Mw, _Vdq),
    (0xf3a, 'PEXTRW', _Rdqp, _Vdq),
    (0xf3a, 'PEXTRD', _Ed, _Vdq),
    (0xf3a, 'PEXTRQ', _Eqp, _Vdq),
    (0xf3a, 'EXTRACTPS', _Ed, _Vdq),
    (0xf3a, 'PINSRB', _Vdq, _Mb),
    (0xf3a, 'PINSRB', _Vdq, _Rdqp),
    (0xf3a, 'INSERTPS', _Vps, _Ups),
    (0xf3a, 'INSERTPS', _Vps, _Md),
    (0xf3a, 'PINSRD', _Vdq, _Ed),
    (0xf3a, 'PINSRQ', _Vdq, _Eqp),
    (0xf3a, 'DPPS', _Vps, _Wps),
    (0xf3a, 'DPPD', _Vpd, _Wpd),
    (0xf3a, 'MPSADBW', _Vdq, _Wdq),
    (0xf3a, 'PCMPESTRM', _Vdq),
    (0xf3a, 'PCMPESTRI', _Vdq),
    (0xf3a, 'PCMPISTRM', _Vdq),
    (0xf3a, 'PCMPISTRI', _Vdq),
    (0xf40, 'CMOVO', _Gvqp, _Evqp),
    (0xf41, 'CMOVNO', _Gvqp, _Evqp),
    (0xf42, 'CMOVB', _Gvqp, _Evqp),
    (0xf42, 'CMOVNAE', _Gvqp, _Evqp),
    (0xf42, 'CMOVC', _Gvqp, _Evqp),
    (0xf43, 'CMOVNB', _Gvqp, _Evqp),
    (0xf43, 'CMOVAE', _Gvqp, _Evqp),
    (0xf43, 'CMOVNC', _Gvqp, _Evqp),
    (0xf44, 'CMOVZ', _Gvqp, _Evqp),
    (0xf44, 'CMOVE', _Gvqp, _Evqp),
    (0xf45, 'CMOVNZ', _Gvqp, _Evqp),
    (0xf45, 'CMOVNE', _Gvqp, _Evqp),
    (0xf46, 'CMOVBE', _Gvqp, _Evqp),
    (0xf46, 'CMOVNA', _Gvqp, _Evqp),
    (0xf47, 'CMOVNBE', _Gvqp, _Evqp),
    (0xf47, 'CMOVA', _Gvqp, _Evqp),
    (0xf48, 'CMOVS', _Gvqp, _Evqp),
    (0xf49, 'CMOVNS', _Gvqp, _Evqp),
    (0xf4a, 'CMOVP', _Gvqp, _Evqp),
    (0xf4a, 'CMOVPE', _Gvqp, _Evqp),
    (0xf4b, 'CMOVNP', _Gvqp, _Evqp),
    (0xf4b, 'CMOVPO', _Gvqp, _Evqp),
    (0xf4c, 'CMOVL', _Gvqp, _Evqp),
    (0xf4c, 'CMOVNGE', _Gvqp, _Evqp),
    (0xf4d, 'CMOVNL', _Gvqp, _Evqp),
    (0xf4d, 'CMOVGE', _Gvqp, _Evqp),
    (0xf4e, 'CMOVLE', _Gvqp, _Evqp),
    (0xf4e, 'CMOVNG', _Gvqp, _Evqp),
    (0xf4f, 'CMOVNLE', _Gvqp, _Evqp),
    (0xf4f, 'CMOVG', _Gvqp, _Evqp),
    (0xf50, 'MOVMSKPS', _Gdqp, _Ups),
    (0xf50, 'MOVMSKPD', _Gdqp, _Upd),
    (0xf51, 'SQRTPS', _Vps, _Wps),
    (0xf51, 'SQRTSS', _Vss, _Wss),
    (0xf51, 'SQRTPD', _Vpd, _Wpd),
    (0xf51, 'SQRTSD', _Vsd, _Wsd),
    (0xf52, 'RSQRTPS', _Vps, _Wps),
    (0xf52, 'RSQRTSS', _Vss, _Wss),
    (0xf53, 'RCPPS', _Vps, _Wps),
    (0xf53, 'RCPSS', _Vss, _Wss),
    (0xf54, 'ANDPS', _Vps, _Wps),
    (0xf54, 'ANDPD', _Vpd, _Wpd),
    (0xf55, 'ANDNPS', _Vps, _Wps),
    (0xf55, 'ANDNPD', _Vpd, _Wpd),
    (0xf56, 'ORPS', _Vps, _Wps),
    (0xf56, 'ORPD', _Vpd, _Wpd),
    (0xf57, 'XORPS', _Vps, _Wps),
    (0xf57, 'XORPD', _Vpd, _Wpd),
    (0xf58, 'ADDPS', _Vps, _Wps),
    (0xf58, 'ADDSS', _Vss, _Wss),
    (0xf58, 'ADDPD', _Vpd, _Wpd),
    (0xf58, 'ADDSD', _Vsd, _Wsd),
    (0xf59, 'MULPS', _Vps, _Wps),
    (0xf59, 'MULSS', _Vss, _Wss),
    (0xf59, 'MULPD', _Vpd, _Wpd),
    (0xf59, 'MULSD', _Vsd, _Wsd),
    (0xf5a, 'CVTPS2PD', _Vpd, _Wps),
    (0xf5a, 'CVTPD2PS', _Vps, _Wpd),
    (0xf5a, 'CVTSS2SD', _Vsd, _Wss),
    (0xf5a, 'CVTSD2SS', _Vss, _Wsd),
    (0xf5b, 'CVTDQ2PS', _Vps, _Wdq),
    (0xf5b, 'CVTPS2DQ', _Vdq, _Wps),
    (0xf5b, 'CVTTPS2DQ', _Vdq, _Wps),
    (0xf5c, 'SUBPS', _Vps, _Wps),
    (0xf5c, 'SUBSS', _Vss, _Wss),
    (0xf5c, 'SUBPD', _Vpd, _Wpd),
    (0xf5c, 'SUBSD', _Vsd, _Wsd),
    (0xf5d, 'MINPS', _Vps, _Wps),
    (0xf5d, 'MINSS', _Vss, _Wss),
    (0xf5d, 'MINPD', _Vpd, _Wpd),
    (0xf5d, 'MINSD', _Vsd, _Wsd),
    (0xf5e, 'DIVPS', _Vps, _Wps),
    (0xf5e, 'DIVSS', _Vss, _Wss),
    (0xf5e, 'DIVPD', _Vpd, _Wpd),
    (0xf5e, 'DIVSD', _Vsd, _Wsd),
    (0xf5f, 'MAXPS', _Vps, _Wps),
    (0xf5f, 'MAXSS', _Vss, _Wss),
    (0xf5f, 'MAXPD', _Vpd, _Wpd),
    (0xf5f, 'MAXSD', _Vsd, _Wsd),
    (0xf60, 'PUNPCKLBW', _Pq, _Qd),
    (0xf60, 'PUNPCKLBW', _Vdq, _Wdq),
    (0xf61, 'PUNPCKLWD', _Pq, _Qd),
    (0xf61, 'PUNPCKLWD', _Vdq, _Wdq),
    (0xf62, 'PUNPCKLDQ', _Pq, _Qd),
    (0xf62, 'PUNPCKLDQ', _Vdq, _Wdq),
    (0xf63, 'PACKSSWB', _Pq, _Qd),
    (0xf63, 'PACKSSWB', _Vdq, _Wdq),
    (0xf64, 'PCMPGTB', _Pq, _Qd),
    (0xf64, 'PCMPGTB', _Vdq, _Wdq),
    (0xf65, 'PCMPGTW', _Pq, _Qd),
    (0xf65, 'PCMPGTW', _Vdq, _Wdq),
    (0xf66, 'PCMPGTD', _Pq, _Qd),
    (0xf66, 'PCMPGTD', _Vdq, _Wdq),
    (0xf67, 'PACKUSWB', _Pq, _Qq),
    (0xf67, 'PACKUSWB', _Vdq, _Wdq),
    (0xf68, 'PUNPCKHBW', _Pq, _Qq),
    (0xf68, 'PUNPCKHBW', _Vdq, _Wdq),
    (0xf69, 'PUNPCKHWD', _Pq, _Qq),
    (0xf69, 'PUNPCKHWD', _Vdq, _Wdq),
    (0xf6a, 'PUNPCKHDQ', _Pq, _Qq),
    (0xf6a, 'PUNPCKHDQ', _Vdq, _Wdq),
    (0xf6b, 'PACKSSDW', _Pq, _Qq),
    (0xf6b, 'PACKSSDW', _Vdq, _Wdq),
    (0xf6c, 'PUNPCKLQDQ', _Vdq, _Wdq),
    (0xf6d, 'PUNPCKHQDQ', _Vdq, _Wdq),
    (0xf6e, 'MOVD', _Pq, _Ed),
    (0xf6e, 'MOVD', _Pq, _Ed),
    (0xf6e, 'MOVQ', _Pq, _Eqp),
    (0xf6e, 'MOVD', _Vdq, _Ed),
    (0xf6e, 'MOVD', _Vdq, _Ed),
    (0xf6e, 'MOVQ', _Vdq, _Eqp),
    (0xf6f, 'MOVQ', _Pq, _Qq),
    (0xf6f, 'MOVDQA', _Vdq, _Wdq),
    (0xf6f, 'MOVDQU', _Vdq, _Wdq),
    (0xf70, 'PSHUFW', _Pq, _Qq),
    (0xf70, 'PSHUFLW', _Vdq, _Wdq),
    (0xf70, 'PSHUFHW', _Vdq, _Wdq),
    (0xf70, 'PSHUFD', _Vdq, _Wdq),
    (0xf71, 'PSRLW', _Nq, _Ib),
    (0xf71, 'PSRLW', _Udq, _Ib),
    (0xf71, 'PSRAW', _Nq, _Ib),
    (0xf71, 'PSRAW', _Udq, _Ib),
    (0xf71, 'PSLLW', _Nq, _Ib),
    (0xf71, 'PSLLW', _Udq, _Ib),
    (0xf72, 'PSRLD', _Nq, _Ib),
    (0xf72, 'PSRLD', _Udq, _Ib),
    (0xf72, 'PSRAD', _Nq, _Ib),
    (0xf72, 'PSRAD', _Udq, _Ib),
    (0xf72, 'PSLLD', _Nq, _Ib),
    (0xf72, 'PSLLD', _Udq, _Ib),
    (0xf73, 'PSRLQ', _Nq, _Ib),
    (0xf73, 'PSRLQ', _Udq, _Ib),
    (0xf73, 'PSRLDQ', _Udq, _Ib),
    (0xf73, 'PSLLQ', _Nq, _Ib),
    (0xf73, 'PSLLQ', _Udq, _Ib),
    (0xf73, 'PSLLDQ', _Udq, _Ib),
    (0xf74, 'PCMPEQB', _Pq, _Qq),
    (0xf74, 'PCMPEQB', _Vdq, _Wdq),
    (0xf75, 'PCMPEQW', _Pq, _Qq),
    (0xf75, 'PCMPEQW', _Vdq, _Wdq),
    (0xf76, 'PCMPEQD', _Pq, _Qq),
    (0xf76, 'PCMPEQD', _Vdq, _Wdq),
    (0xf77, 'EMMS'),
    (0xf78, 'VMREAD', _Ed, _Gd),
    (0xf78, 'VMREAD', _Eq, _Gq),
    (0xf79, 'VMWRITE', _Gd),
    (0xf79, 'VMWRITE', _Gq),
    (0xf7c, 'HADDPD', _Vpd, _Wpd),
    (0xf7c, 'HADDPS', _Vps, _Wps),
    (0xf7d, 'HSUBPD', _Vpd, _Wpd),
    (0xf7d, 'HSUBPS', _Vps, _Wps),
    (0xf7e, 'MOVD', _Ed, _Pq),
    (0xf7e, 'MOVD', _Ed, _Pq),
    (0xf7e, 'MOVQ', _Eqp, _Pq),
    (0xf7e, 'MOVD', _Ed, _Vdq),
    (0xf7e, 'MOVD', _Ed, _Vdq),
    (0xf7e, 'MOVQ', _Eqp, _Edq),
    (0xf7e, 'MOVQ', _Vq, _Wq),
    (0xf7f, 'MOVQ', _Qq, _Pq),
    (0xf7f, 'MOVDQA', _Wdq, _Vdq),
    (0xf7f, 'MOVDQU', _Wdq, _Vdq),
    (0xf80, 'JO', _Jvds),
    (0xf81, 'JNO', _Jvds),
    (0xf82, 'JB', _Jvds),
    (0xf82, 'JNAE', _Jvds),
    (0xf82, 'JC', _Jvds),
    (0xf83, 'JNB', _Jvds),
    (0xf83, 'JAE', _Jvds),
    (0xf83, 'JNC', _Jvds),
    (0xf84, 'JZ', _Jvds),
    (0xf84, 'JE', _Jvds),
    (0xf85, 'JNZ', _Jvds),
    (0xf85, 'JNE', _Jvds),
    (0xf86, 'JBE', _Jvds),
    (0xf86, 'JNA', _Jvds),
    (0xf87, 'JNBE', _Jvds),
    (0xf87, 'JA', _Jvds),
    (0xf88, 'JS', _Jvds),
    (0xf89, 'JNS', _Jvds),
    (0xf8a, 'JP', _Jvds),
    (0xf8a, 'JPE', _Jvds),
    (0xf8b, 'JNP', _Jvds),
    (0xf8b, 'JPO', _Jvds),
    (0xf8c, 'JL', _Jvds),
    (0xf8c, 'JNGE', _Jvds),
    (0xf8d, 'JNL', _Jvds),
    (0xf8d, 'JGE', _Jvds),
    (0xf8e, 'JLE', _Jvds),
    (0xf8e, 'JNG', _Jvds),
    (0xf8f, 'JNLE', _Jvds),
    (0xf8f, 'JG', _Jvds),
    (0xf90, 'SETO', _Eb),
    (0xf91, 'SETNO', _Eb),
    (0xf92, 'SETB', _Eb),
    (0xf92, 'SETNAE', _Eb),
    (0xf92, 'SETC', _Eb),
    (0xf93, 'SETNB', _Eb),
    (0xf93, 'SETAE', _Eb),
    (0xf93, 'SETNC', _Eb),
    (0xf94, 'SETZ', _Eb),
    (0xf94, 'SETE', _Eb),
    (0xf95, 'SETNZ', _Eb),
    (0xf95, 'SETNE', _Eb),
    (0xf96, 'SETBE', _Eb),
    (0xf96, 'SETNA', _Eb),
    (0xf97, 'SETNBE', _Eb),
    (0xf97, 'SETA', _Eb),
    (0xf98, 'SETS', _Eb),
    (0xf99, 'SETNS', _Eb),
    (0xf9a, 'SETP', _Eb),
    (0xf9a, 'SETPE', _Eb),
    (0xf9b, 'SETNP', _Eb),
    (0xf9b, 'SETPO', _Eb),
    (0xf9c, 'SETL', _Eb),
    (0xf9c, 'SETNGE', _Eb),
    (0xf9d, 'SETNL', _Eb),
    (0xf9d, 'SETGE', _Eb),
    (0xf9e, 'SETLE', _Eb),
    (0xf9e, 'SETNG', _Eb),
    (0xf9f, 'SETNLE', _Eb),
    (0xf9f, 'SETG', _Eb),
    (0xfa2, 'CPUID'),
    (0xfa3, 'BT', _Evqp),
    (0xfa4, 'SHLD', _Evqp, _Gvqp),
    (0xfa5, 'SHLD', _Evqp, _Gvqp),
    (0xfaa, 'RSM'),
    (0xfab, 'BTS', _Evqp, _Gvqp),
    (0xfac, 'SHRD', _Evqp, _Gvqp),
    (0xfad, 'SHRD', _Evqp, _Gvqp),
    (0xfae, 'FXSAVE', _Mstx),
    (0xfae, 'FXSAVE', _Mstx),
    (0xfae, 'FXRSTOR', _Mstx),
    (0xfae, 'FXRSTOR', _Mstx),
    (0xfae, 'LDMXCSR', _Md),
    (0xfae, 'STMXCSR', _Md),
    (0xfae, 'XSAVE', _M),
    (0xfae, 'XSAVE', _M),
    (0xfae, 'LFENCE'),
    (0xfae, 'XRSTOR', _M),
    (0xfae, 'XRSTOR', _M),
    (0xfae, 'MFENCE'),
    (0xfae, 'SFENCE'),
    (0xfae, 'CLFLUSH', _Mb),
    (0xfaf, 'IMUL', _Gvqp, _Evqp),
    (0xfb0, 'CMPXCHG', _Eb, _Gb),
    (0xfb1, 'CMPXCHG', _Evqp, _Gvqp),
    (0xfb3, 'BTR', _Evqp, _Gvqp),
    (0xfb6, 'MOVZX', _Gvqp, _Eb),
    (0xfb7, 'MOVZX', _Gvqp, _Ew),
    (0xfb8, 'JMPE'),
    (0xfb8, 'POPCNT', _Gvqp, _Evqp),
    (0xfb9, 'UD', _G),
    (0xfba, 'BT', _Evqp),
    (0xfba, 'BTS', _Evqp, _Ib),
    (0xfba, 'BTR', _Evqp, _Ib),
    (0xfba, 'BTC', _Evqp, _Ib),
    (0xfbb, 'BTC', _Evqp, _Gvqp),
    (0xfbc, 'BSF', _Gvqp, _Evqp),
    (0xfbd, 'BSR', _Gvqp, _Evqp),
    (0xfbe, 'MOVSX', _Gvqp, _Eb),
    (0xfbf, 'MOVSX', _Gvqp, _Ew),
    (0xfc0, 'XADD', _Eb),
    (0xfc1, 'XADD', _Evqp),
    (0xfc2, 'CMPPS', _Vps, _Wps),
    (0xfc2, 'CMPSS', _Vss, _Wss),
    (0xfc2, 'CMPPD', _Vpd, _Wpd),
    (0xfc2, 'CMPSD', _Vsd, _Wsd),
    (0xfc3, 'MOVNTI', _Mdqp, _Gdqp),
    (0xfc4, 'PINSRW', _Pq, _Rdqp),
    (0xfc4, 'PINSRW', _Pq, _Mw),
    (0xfc4, 'PINSRW', _Vdq, _Rdqp),
    (0xfc4, 'PINSRW', _Vdq, _Mw),
    (0xfc5, 'PEXTRW', _Gdqp, _Nq),
    (0xfc5, 'PEXTRW', _Gdqp, _Udq),
    (0xfc6, 'SHUFPS', _Vps, _Wps),
    (0xfc6, 'SHUFPD', _Vpd, _Wpd),
    (0xfc7, 'CMPXCHG8B', _Mq),
    (0xfc7, 'CMPXCHG8B', _Mq),
    (0xfc7, 'CMPXCHG16B', _Mdq),
    (0xfc7, 'VMPTRLD', _Mq),
    (0xfc7, 'VMCLEAR', _Mq),
    (0xfc7, 'VMXON', _Mq),
    (0xfc7, 'VMPTRST', _Mq),
    (0xfc8, 'BSWAP', _Zvqp),
    (0xfd0, 'ADDSUBPD', _Vpd, _Wpd),
    (0xfd0, 'ADDSUBPS', _Vps, _Wps),
    (0xfd1, 'PSRLW', _Pq, _Qq),
    (0xfd1, 'PSRLW', _Vdq, _Wdq),
    (0xfd2, 'PSRLD', _Pq, _Qq),
    (0xfd2, 'PSRLD', _Vdq, _Wdq),
    (0xfd3, 'PSRLQ', _Pq, _Qq),
    (0xfd3, 'PSRLQ', _Vdq, _Wdq),
    (0xfd4, 'PADDQ', _Pq, _Qq),
    (0xfd4, 'PADDQ', _Vdq, _Wdq),
    (0xfd5, 'PMULLW', _Pq, _Qq),
    (0xfd5, 'PMULLW', _Vdq, _Wdq),
    (0xfd6, 'MOVQ', _Wq, _Vq),
    (0xfd6, 'MOVQ2DQ', _Vdq, _Nq),
    (0xfd6, 'MOVDQ2Q', _Pq, _Uq),
    (0xfd7, 'PMOVMSKB', _Gdqp, _Nq),
    (0xfd7, 'PMOVMSKB', _Gdqp, _Udq),
    (0xfd8, 'PSUBUSB', _Pq, _Qq),
    (0xfd8, 'PSUBUSB', _Vdq, _Wdq),
    (0xfd9, 'PSUBUSW', _Pq, _Qq),
    (0xfd9, 'PSUBUSW', _Vdq, _Wdq),
    (0xfda, 'PMINUB', _Pq, _Qq),
    (0xfda, 'PMINUB', _Vdq, _Wdq),
    (0xfdb, 'PAND', _Pq, _Qd),
    (0xfdb, 'PAND', _Vdq, _Wdq),
    (0xfdc, 'PADDUSB', _Pq, _Qq),
    (0xfdc, 'PADDUSB', _Vdq, _Wdq),
    (0xfdd, 'PADDUSW', _Pq, _Qq),
    (0xfdd, 'PADDUSW', _Vdq, _Wdq),
    (0xfde, 'PMAXUB', _Pq, _Qq),
    (0xfde, 'PMAXUB', _Vdq, _Wdq),
    (0xfdf, 'PANDN', _Pq, _Qq),
    (0xfdf, 'PANDN', _Vdq, _Wdq),
    (0xfe0, 'PAVGB', _Pq, _Qq),
    (0xfe0, 'PAVGB', _Vdq, _Wdq),
    (0xfe1, 'PSRAW', _Pq, _Qq),
    (0xfe1, 'PSRAW', _Vdq, _Wdq),
    (0xfe2, 'PSRAD', _Pq, _Qq),
    (0xfe2, 'PSRAD', _Vdq, _Wdq),
    (0xfe3, 'PAVGW', _Pq, _Qq),
    (0xfe3, 'PAVGW', _Vdq, _Wdq),
    (0xfe4, 'PMULHUW', _Pq, _Qq),
    (0xfe4, 'PMULHUW', _Vdq, _Wdq),
    (0xfe5, 'PMULHW', _Pq, _Qq),
    (0xfe5, 'PMULHW', _Vdq, _Wdq),
    (0xfe6, 'CVTPD2DQ', _Vdq, _Wpd),
    (0xfe6, 'CVTTPD2DQ', _Vdq, _Wpd),
    (0xfe6, 'CVTDQ2PD', _Vpd, _Wdq),
    (0xfe7, 'MOVNTQ', _Mq, _Pq),
    (0xfe7, 'MOVNTDQ', _Mdq, _Vdq),
    (0xfe8, 'PSUBSB', _Pq, _Qq),
    (0xfe8, 'PSUBSB', _Vdq, _Wdq),
    (0xfe9, 'PSUBSW', _Pq, _Qq),
    (0xfe9, 'PSUBSW', _Vdq, _Wdq),
    (0xfea, 'PMINSW', _Pq, _Qq),
    (0xfea, 'PMINSW', _Vdq, _Wdq),
    (0xfeb, 'POR', _Pq, _Qq),
    (0xfeb, 'POR', _Vdq, _Wdq),
    (0xfec, 'PADDSB', _Pq, _Qq),
    (0xfec, 'PADDSB', _Vdq, _Wdq),
    (0xfed, 'PADDSW', _Pq, _Qq),
    (0xfed, 'PADDSW', _Vdq, _Wdq),
    (0xfee, 'PMAXSW', _Pq, _Qq),
    (0xfee, 'PMAXSW', _Vdq, _Wdq),
    (0xfef, 'PXOR', _Pq, _Qq),
    (0xfef, 'PXOR', _Vdq, _Wdq),
    (0xff0, 'LDDQU', _Vdq, _Mdq),
    (0xff1, 'PSLLW', _Pq, _Qq),
    (0xff1, 'PSLLW', _Vdq, _Wdq),
    (0xff2, 'PSLLD', _Pq, _Qq),
    (0xff2, 'PSLLD', _Vdq, _Wdq),
    (0xff3, 'PSLLQ', _Pq, _Qq),
    (0xff3, 'PSLLQ', _Vdq, _Wdq),
    (0xff4, 'PMULUDQ', _Pq, _Qq),
    (0xff4, 'PMULUDQ', _Vdq, _Wdq),
    (0xff5, 'PMADDWD', _Pq, _Qd),
    (0xff5, 'PMADDWD', _Vdq, _Wdq),
    (0xff6, 'PSADBW', _Pq, _Qq),
    (0xff6, 'PSADBW', _Vdq, _Wdq),
    (0xff7, 'MASKMOVQ', _Nq),
    (0xff7, 'MASKMOVDQU', _Vdq),
    (0xff8, 'PSUBB', _Pq, _Qq),
    (0xff8, 'PSUBB', _Vdq, _Wdq),
    (0xff9, 'PSUBW', _Pq, _Qq),
    (0xff9, 'PSUBW', _Vdq, _Wdq),
    (0xffa, 'PSUBD', _Pq, _Qq),
    (0xffa, 'PSUBD', _Vdq, _Wdq),
    (0xffb, 'PSUBQ', _Pq, _Qq),
    (0xffb, 'PSUBQ', _Vdq, _Wdq),
    (0xffc, 'PADDB', _Pq, _Qq),
    (0xffc, 'PADDB', _Vdq, _Wdq),
    (0xffd, 'PADDW', _Pq, _Qq),
    (0xffd, 'PADDW', _Vdq, _Wdq),
    (0xffe, 'PADDD', _Pq, _Qq),
    (0xffe, 'PADDD', _Vdq, _Wdq)
)

OPCODES_IMPLICIT_32 = ('STOSD', 'LODSD')


class X86OpCode:

    def __init__(self, assembler, name, base, args):
        self.assembler = assembler
        self.name = name
        self.conditions = [(base, args)]

    def add_condition(self, base, args):
        self.conditions.append((base, args))

    def __call__(self, instr):
        for base, args in self.conditions:
            modrm = {}
            if not args:
                if instr.tokens[0].upper() in OPCODES_IMPLICIT_32:
                    if self.assembler.bits == 16:
                        return pack_byte(0x66, base)
                if instr.tokens[0].upper().startswith('REP'):
                    new_instr = Instruction(
                        instr.tokens[1:], instr.line, instr.context)
                    return pack_byte(base) + self.assembler.instructions[new_instr.tokens[0].upper()](new_instr)
                if len(instr.tokens) == 1:
                    return pack_byte(base)
                raise InvalidOpCodeArguments(instr)
            if len(instr.tokens) < 2:
                continue
            index = 1
            skip = False
            full_blob = b''
            if base > 0xFF:
                new_base = [base >> 8, base & 0xff]
            else:
                new_base = [base]
            for arg in args:
                delta_base_and_blob = arg(
                    instr, new_base, self.assembler, index, modrm)
                if not delta_base_and_blob or len(delta_base_and_blob) != 3:
                    skip = True
                    break
                else:
                    new_index, new_base, new_blob = delta_base_and_blob
                    index += new_index
                    full_blob += new_blob
            if not skip:
                return pack_byte(*new_base) + full_blob


class AssemblerX86(Assembler):

    hex_prefixes = ('0x', '0h', '$0')
    hex_suffixes = ('h',)

    dec_prefixes = ('0d',)
    dec_suffixes = ('d',)

    bin_prefixes = ('0b', '0y')
    bin_suffixes = ('b', 'y')

    oct_prefixes = ('0o', '0q')
    oct_suffixes = ('o', 'q')

    bits = 64

    @directive('bits')
    def directive_bits(self, instr):
        value = self.parse_integer(instr.tokens[1], 8, False)
        if value is None or value not in (16, 32, 64):
            raise InvalidArgumentsForDirective
        self.bits = value

    def register_instructions(self):
        for item in OPCODES_TABLE:
            if item[1].upper() in self.instructions:
                self.instructions[item[1].upper()].add_condition(
                    item[0], item[2:])
            else:
                x86_opcode = X86OpCode(
                    self, item[1], item[0], item[2:])
                self.register_instruction(item[1], x86_opcode)


if __name__ == '__main__':
    AssemblerX86.main()
