import unittest
from necroassembler.cpu.lr35902 import AssemblerLR35902


class TestGameboy(unittest.TestCase):

    def setUp(self):
        self.asm = AssemblerLR35902()

    def test_ld_a_hl_plus(self):
        self.asm.assemble('LD A,(HL+)')
        self.assertEqual(self.asm.assembled_bytes, b'\x2A')

    def test_ld_line0(self):
        self.asm.assemble(
            'NOP\nloop: LD BC, $17\nLD (BC),A\nLD B,$22\nLD (loop),SP\nLD A,(BC)\nLD C,$30')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x00\x01\x17\x00\x02\x06\x22\x08\x01\x00\x0A\x0E\x30')

    def test_inc_line0(self):
        self.asm.assemble('INC BC\nINC B\nINC C')
        self.assertEqual(self.asm.assembled_bytes, b'\x03\x04\x0C')

    def test_ld_ff_ind_a(self):
        self.asm.assemble('LD [$FF40], A')
        self.assertEqual(self.asm.assembled_bytes, b'\xEA\x40\xFF')

    def test_jr(self):
        self.asm.assemble('JR NZ,-1')
        self.assertEqual(self.asm.assembled_bytes, b'\x20\xff')

    def test_jr_label(self):
        self.asm.assemble('start:NOP\nJR NZ,start')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\x00\x20\xfd')

    def test_line0_0_7(self):
        self.asm.assemble('NOP')
        self.asm.assemble('LD BC,$17')
        self.asm.assemble('LD (BC), A')
        self.asm.assemble('INC BC')
        self.asm.assemble('INC B')
        self.asm.assemble('DEC B')
        self.asm.assemble('LD B, $22')
        self.asm.assemble('RLCA')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x00' +
                         b'\x01\x17\x00' +
                         b'\x02\x03\x04\x05' +
                         b'\x06\x22' +
                         b'\x07')

    def test_line0_8_f(self):
        self.asm.assemble('LD ($30), SP')
        self.asm.assemble('ADD HL,BC')
        self.asm.assemble('LD A,(BC)')
        self.asm.assemble('DEC BC')
        self.asm.assemble('INC C')
        self.asm.assemble('DEC C')
        self.asm.assemble('LD C, $17')
        self.asm.assemble('RRCA')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x08\x30\x00' +
                         b'\x09\x0A\x0B\x0C\x0D' +
                         b'\x0E\x17' +
                         b'\x0F')

    def test_line1_0_7(self):
        self.asm.assemble('STOP')
        self.asm.assemble('LD DE,$17')
        self.asm.assemble('LD (DE), A')
        self.asm.assemble('INC DE')
        self.asm.assemble('INC D')
        self.asm.assemble('DEC D')
        self.asm.assemble('LD D, $22')
        self.asm.assemble('RLA')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x10\x00' +
                         b'\x11\x17\x00' +
                         b'\x12\x13\x14\x15' +
                         b'\x16\x22' +
                         b'\x17')

    def test_line1_8_f(self):
        self.asm.assemble('JR $30')
        self.asm.assemble('ADD HL,DE')
        self.asm.assemble('LD A,(DE)')
        self.asm.assemble('DEC DE')
        self.asm.assemble('INC E')
        self.asm.assemble('DEC E')
        self.asm.assemble('LD E, $17')
        self.asm.assemble('RRA')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x18\x30' +
                         b'\x19\x1A\x1B\x1C\x1D' +
                         b'\x1E\x17' +
                         b'\x1F')

    def test_jp(self):
        self.asm.assemble('JP NZ, $1234')
        self.asm.assemble('JP $1234')
        self.asm.assemble('JP Z, $1234')
        self.asm.assemble('JP NC, $1234')
        self.asm.assemble('JP C, $1234')
        self.asm.assemble('JP (HL)')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xC2\x34\x12' +
                         b'\xC3\x34\x12' +
                         b'\xCA\x34\x12' +
                         b'\xD2\x34\x12' +
                         b'\xDA\x34\x12' +
                         b'\xE9')

    def test_line2_0_7(self):
        self.asm.assemble('JR NZ,-1')
        self.asm.assemble('LD HL,$17')
        self.asm.assemble('LD (HL+), A')
        self.asm.assemble('INC HL')
        self.asm.assemble('INC H')
        self.asm.assemble('DEC H')
        self.asm.assemble('LD H, $22')
        self.asm.assemble('DAA')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x20\xFF' +
                         b'\x21\x17\x00' +
                         b'\x22\x23\x24\x25' +
                         b'\x26\x22' +
                         b'\x27')

    def test_line2_8_f(self):
        self.asm.assemble('JR Z,-2')
        self.asm.assemble('ADD HL,HL')
        self.asm.assemble('LD A,(HL+)')
        self.asm.assemble('DEC HL')
        self.asm.assemble('INC L')
        self.asm.assemble('DEC L')
        self.asm.assemble('LD L, $17')
        self.asm.assemble('CPL')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x28\xFE' +
                         b'\x29\x2A\x2B\x2C\x2D' +
                         b'\x2E\x17' +
                         b'\x2F')

    def test_line3_0_7(self):
        self.asm.assemble('JR NC,-1')
        self.asm.assemble('LD SP,$17')
        self.asm.assemble('LD (HL-), A')
        self.asm.assemble('INC SP')
        self.asm.assemble('INC (HL)')
        self.asm.assemble('DEC (HL)')
        self.asm.assemble('LD (HL), $22')
        self.asm.assemble('SCF')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x30\xFF' +
                         b'\x31\x17\x00' +
                         b'\x32\x33\x34\x35' +
                         b'\x36\x22' +
                         b'\x37')

    def test_line3_8_f(self):
        self.asm.assemble('JR C,-2')
        self.asm.assemble('ADD HL,SP')
        self.asm.assemble('LD A,(HL-)')
        self.asm.assemble('DEC SP')
        self.asm.assemble('INC A')
        self.asm.assemble('DEC A')
        self.asm.assemble('LD A, $17')
        self.asm.assemble('CCF')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x38\xFE' +
                         b'\x39\x3A\x3B\x3C\x3D' +
                         b'\x3E\x17' +
                         b'\x3F')

    def test_line4_0_7(self):
        self.asm.assemble('LD B,B')
        self.asm.assemble('LD B,C')
        self.asm.assemble('LD B,D')
        self.asm.assemble('LD B,E')
        self.asm.assemble('LD B,H')
        self.asm.assemble('LD B,L')
        self.asm.assemble('LD B, (HL)')
        self.asm.assemble('LD B,A')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x40\x41\x42\x43\x44\x45\x46\x47')

    def test_line4_8_f(self):
        self.asm.assemble('LD C,B')
        self.asm.assemble('LD C,C')
        self.asm.assemble('LD C,D')
        self.asm.assemble('LD C,E')
        self.asm.assemble('LD C,H')
        self.asm.assemble('LD C,L')
        self.asm.assemble('LD C,(HL)')
        self.asm.assemble('LD C,A')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x48\x49\x4A\x4B\x4C\x4D\x4E\x4F')

    def test_line5_0_7(self):
        self.asm.assemble('LD D,B')
        self.asm.assemble('LD D,C')
        self.asm.assemble('LD D,D')
        self.asm.assemble('LD D,E')
        self.asm.assemble('LD D,H')
        self.asm.assemble('LD D,L')
        self.asm.assemble('LD D, (HL)')
        self.asm.assemble('LD D,A')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x50\x51\x52\x53\x54\x55\x56\x57')

    def test_line5_8_f(self):
        self.asm.assemble('LD E,B')
        self.asm.assemble('LD E,C')
        self.asm.assemble('LD E,D')
        self.asm.assemble('LD E,E')
        self.asm.assemble('LD E,H')
        self.asm.assemble('LD E,L')
        self.asm.assemble('LD E,(HL)')
        self.asm.assemble('LD E,A')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x58\x59\x5A\x5B\x5C\x5D\x5E\x5F')

    def test_line6_0_7(self):
        self.asm.assemble('LD H,B')
        self.asm.assemble('LD H,C')
        self.asm.assemble('LD H,D')
        self.asm.assemble('LD H,E')
        self.asm.assemble('LD H,H')
        self.asm.assemble('LD H,L')
        self.asm.assemble('LD H, (HL)')
        self.asm.assemble('LD H,A')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x60\x61\x62\x63\x64\x65\x66\x67')

    def test_line6_8_f(self):
        self.asm.assemble('LD L,B')
        self.asm.assemble('LD L,C')
        self.asm.assemble('LD L,D')
        self.asm.assemble('LD L,E')
        self.asm.assemble('LD L,H')
        self.asm.assemble('LD L,L')
        self.asm.assemble('LD L,(HL)')
        self.asm.assemble('LD L,A')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x68\x69\x6A\x6B\x6C\x6D\x6E\x6F')

    def test_line7_0_7(self):
        self.asm.assemble('LD (HL),B')
        self.asm.assemble('LD (HL),C')
        self.asm.assemble('LD (HL),D')
        self.asm.assemble('LD (HL),E')
        self.asm.assemble('LD (HL),H')
        self.asm.assemble('LD (HL),L')
        self.asm.assemble('HALT')
        self.asm.assemble('LD (HL),A')

        self.assertEqual(self.asm.assembled_bytes,
                         b'\x70\x71\x72\x73\x74\x75\x76\x77')

    def test_line7_8_f(self):
        self.asm.assemble('LD A,B')
        self.asm.assemble('LD A,C')
        self.asm.assemble('LD A,D')
        self.asm.assemble('LD A,E')
        self.asm.assemble('LD A,H')
        self.asm.assemble('LD A,L')
        self.asm.assemble('LD A,(HL)')
        self.asm.assemble('LD A,A')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x78\x79\x7A\x7B\x7C\x7D\x7E\x7F')

    def test_line8_0_7(self):
        self.asm.assemble('ADD A,B')
        self.asm.assemble('ADD A,C')
        self.asm.assemble('ADD A,D')
        self.asm.assemble('ADD A,E')
        self.asm.assemble('ADD A,H')
        self.asm.assemble('ADD A,L')
        self.asm.assemble('ADD A,(HL)')
        self.asm.assemble('ADD A,A')

        self.assertEqual(self.asm.assembled_bytes,
                         b'\x80\x81\x82\x83\x84\x85\x86\x87')

    def test_line8_8_f(self):
        self.asm.assemble('ADC A,B')
        self.asm.assemble('ADC A,C')
        self.asm.assemble('ADC A,D')
        self.asm.assemble('ADC A,E')
        self.asm.assemble('ADC A,H')
        self.asm.assemble('ADC A,L')
        self.asm.assemble('ADC A,(HL)')
        self.asm.assemble('ADC A,A')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x88\x89\x8A\x8B\x8C\x8D\x8E\x8F')

    def test_line9_0_7(self):
        self.asm.assemble('SUB B')
        self.asm.assemble('SUB C')
        self.asm.assemble('SUB D')
        self.asm.assemble('SUB E')
        self.asm.assemble('SUB H')
        self.asm.assemble('SUB L')
        self.asm.assemble('SUB (HL)')
        self.asm.assemble('SUB A')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x90\x91\x92\x93\x94\x95\x96\x97')

    def test_line9_8_f(self):
        self.asm.assemble('SBC A,B')
        self.asm.assemble('SBC A,C')
        self.asm.assemble('SBC A,D')
        self.asm.assemble('SBC A,E')
        self.asm.assemble('SBC A,H')
        self.asm.assemble('SBC A,L')
        self.asm.assemble('SBC A,(HL)')
        self.asm.assemble('SBC A,A')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\x98\x99\x9A\x9B\x9C\x9D\x9E\x9F')

    def test_lineA_0_7(self):
        self.asm.assemble('AND B')
        self.asm.assemble('AND C')
        self.asm.assemble('AND D')
        self.asm.assemble('AND E')
        self.asm.assemble('AND H')
        self.asm.assemble('AND L')
        self.asm.assemble('AND (HL)')
        self.asm.assemble('AND A')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xA0\xA1\xA2\xA3\xA4\xA5\xA6\xA7')

    def test_lineA_8_f(self):
        self.asm.assemble('XOR B')
        self.asm.assemble('XOR C')
        self.asm.assemble('XOR D')
        self.asm.assemble('XOR E')
        self.asm.assemble('XOR H')
        self.asm.assemble('XOR L')
        self.asm.assemble('XOR (HL)')
        self.asm.assemble('XOR A')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xA8\xA9\xAA\xAB\xAC\xAD\xAE\xAF')

    def test_lineB_0_7(self):
        self.asm.assemble('OR B')
        self.asm.assemble('OR C')
        self.asm.assemble('OR D')
        self.asm.assemble('OR E')
        self.asm.assemble('OR H')
        self.asm.assemble('OR L')
        self.asm.assemble('OR (HL)')
        self.asm.assemble('OR A')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xB0\xB1\xB2\xB3\xB4\xB5\xB6\xB7')

    def test_lineB_8_f(self):
        self.asm.assemble('CP B')
        self.asm.assemble('CP C')
        self.asm.assemble('CP D')
        self.asm.assemble('CP E')
        self.asm.assemble('CP H')
        self.asm.assemble('CP L')
        self.asm.assemble('CP (HL)')
        self.asm.assemble('CP A')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xB8\xB9\xBA\xBB\xBC\xBD\xBE\xBF')

    def test_lineC_0_7(self):
        self.asm.assemble('RET NZ')
        self.asm.assemble('POP BC')
        self.asm.assemble('JP NZ, $1234')
        self.asm.assemble('JP $5678')
        self.asm.assemble('CALL NZ, $1122')
        self.asm.assemble('PUSH BC')
        self.asm.assemble('ADD A, -1')
        self.asm.assemble('RST 00H')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xC0\xC1\xC2\x34\x12\xC3\x78\x56\xC4\x22\x11\xC5\xC6\xFF\xC7')

    def test_lineC_8_f(self):
        self.asm.assemble('RET Z')
        self.asm.assemble('RET')
        self.asm.assemble('JP Z,$1234')
        self.asm.assemble('CALL Z, $5678')
        self.asm.assemble('CALL $1111')
        self.asm.assemble('ADC A, -2')
        self.asm.assemble('RST 08H')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xC8\xC9\xCA\x34\x12\xCC\x78\x56\xCD\x11\x11\xCE\xFE\xCF')

    def test_lineD_0_7(self):
        self.asm.assemble('RET NC')
        self.asm.assemble('POP DE')
        self.asm.assemble('JP NC, $1234')
        self.asm.assemble('CALL NC, $1122')
        self.asm.assemble('PUSH DE')
        self.asm.assemble('SUB A, -1')
        self.asm.assemble('RST 10H')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xD0\xD1\xD2\x34\x12\xD4\x22\x11\xD5\xD6\xFF\xD7')

    def test_lineD_8_f(self):
        self.asm.assemble('RET C')
        self.asm.assemble('RETI')
        self.asm.assemble('JP C,$1234')
        self.asm.assemble('CALL C, $5678')
        self.asm.assemble('SBC A, -3')
        self.asm.assemble('RST 18H')
        self.assertEqual(self.asm.assembled_bytes,
                         b'\xD8\xD9\xDA\x34\x12\xDC\x78\x56\xDE\xFD\xDF')
