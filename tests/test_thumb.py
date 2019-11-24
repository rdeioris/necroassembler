import unittest
from necroassembler.cpu.thumb import AssemblerThumb
from necroassembler.exceptions import AlignmentError, NotInBitRange, NotInSignedBitRange


class TestThumb(unittest.TestCase):

    def setUp(self):
        self.asm = AssemblerThumb()

    def test_lsl(self):
        self.asm.assemble('LSL r3, r4, #31')
        self.assertEqual(self.asm.assembled_bytes, b'\xE3\x07')

    def test_lsr(self):
        self.asm.assemble('LSR r1, r2, #2')
        self.assertEqual(self.asm.assembled_bytes, b'\x91\x08')

    def test_asr(self):
        self.asm.assemble('ASR r5, r6, #3')
        self.assertEqual(self.asm.assembled_bytes, b'\xF5\x10')

    def test_asr_define(self):
        self.asm.assemble(
            '.define foo 2\nASR r5, r6, #foo')
        self.assertEqual(self.asm.assembled_bytes, b'\xB5\x10')

    def test_sub(self):
        self.asm.assemble('SUB r1, r2, r3\nSUB r4, r5, #7\nSUB r6, #5')
        self.assertEqual(self.asm.assembled_bytes, b'\xD1\x1A\xEC\x1F\x05\x3E')

    def test_cmp(self):
        self.asm.assemble('CMP r7, #0xff')
        self.assertEqual(self.asm.assembled_bytes, b'\xFF\x2F')

    def test_and(self):
        self.asm.assemble('AND r7, r6')
        self.assertEqual(self.asm.assembled_bytes, b'\x37\x40')

    def test_b_aligned_backward(self):
        self.asm.assemble('loop: b loop')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\xFE\xE7')

    def test_b_aligned_far_backward(self):
        self.asm.assemble('loop:\n.org 1024\nb loop')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\xFE\xE5')

    def test_b_aligned_far_forward(self):
        self.asm.assemble('b loop\n.org 1024\nloop:')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\xFE\xE1')

    def test_b_aligned_far_forward_unaligned(self):
        self.asm.assemble('b loop\n.org 1023\nloop:')
        self.assertRaises(AlignmentError, self.asm.link)

    def test_b_aligned_far_forward_unaligned_increment(self):
        self.asm.assemble('b loop++\n.org 1024\nloop:')
        self.assertRaises(AlignmentError, self.asm.link)

    def test_b_aligned_too_far_forward(self):
        self.asm.assemble('b loop\n.org 4096\nloop:')
        self.assertRaises(NotInSignedBitRange, self.asm.link)

    def test_b_aligned_too_far_backword(self):
        self.asm.assemble('loop:\n.org 4096\nb loop\n')
        self.assertRaises(NotInSignedBitRange, self.asm.link)

    def test_b_unaligned(self):
        self.asm.assemble('loop: b loop++')
        self.assertRaises(AlignmentError, self.asm.link)

    def test_b_add_rd_hs(self):
        self.asm.assemble('ADD r7, r15')
        self.assertEqual(self.asm.assembled_bytes, b'\x7F\x44')

    def test_ldrb_rd_rb_imm(self):
        self.asm.assemble('LDRB r0, [r1, #8]')
        self.assertEqual(self.asm.assembled_bytes, b'\x88\x78')

    def test_bl_num(self):
        self.asm.assemble('BL 0x200000')
        self.assertEqual(self.asm.assembled_bytes, b'\x00\xF2\x00\xF8')

    def test_bl_num_too_far(self):
        self.assertRaises(NotInSignedBitRange, self.asm.assemble, 'BL 0x1500000')

    def test_bl(self):
        self.asm.assemble('BL far\n.org 0x200000\nfar:')
        self.asm.link()
        self.assertEqual(self.asm.assembled_bytes, b'\xFF\xF1\xFE\xFF')

    def test_bl_too_far(self):
        self.asm.assemble('BL far\n.org 0x1000000\nfar:')
        self.assertRaises(NotInSignedBitRange, self.asm.link)

    def test_push_rlist(self):
        self.asm.assemble('PUSH {r0,r1,r2, r3-r6}')
        self.assertEqual(self.asm.assembled_bytes, b'\x7F\xB4')

    def test_push_rlist_lr(self):
        self.asm.assemble('PUSH {lr}')
        self.assertEqual(self.asm.assembled_bytes, b'\x00\xBC')

    def test_push_rlist_lr_r0(self):
        self.asm.assemble('PUSH {r0,lr}')
        self.assertEqual(self.asm.assembled_bytes, b'\x01\xBC')
