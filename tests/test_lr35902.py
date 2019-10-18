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
