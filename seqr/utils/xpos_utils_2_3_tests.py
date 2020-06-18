from __future__ import unicode_literals

from unittest import TestCase
from seqr.utils.xpos_utils import get_chrom_pos, get_xpos


class XposUtilsTest(TestCase):

    def test_get_xpos(self):
        self.assertRaises(ValueError, lambda: get_xpos('chrUnknown', 1))
        self.assertRaises(ValueError, lambda: get_xpos('chr22', 0))
        self.assertRaises(ValueError, lambda: get_xpos('chr22', 1e9))

        self.assertEqual(get_xpos('1', 10), 1e9 + 10)
        self.assertEqual(get_xpos('chr1', 10), 1e9 + 10)
        self.assertEqual(get_xpos('22', 10), 22*1e9 + 10)
        self.assertEqual(get_xpos('X', 10), 23*1e9 + 10)
        self.assertEqual(get_xpos('chrX', 10), 23*1e9 + 10)
        self.assertEqual(get_xpos('Y', 10), 24*1e9 + 10)
        self.assertEqual(get_xpos('chrY', 10), 24*1e9 + 10)
        self.assertEqual(get_xpos('M', 10), 25*1e9 + 10)
        self.assertEqual(get_xpos('chrM', 10), 25*1e9 + 10)

    def test_chrom_pos(self):
        self.assertRaises(ValueError, lambda: get_chrom_pos(0))
        self.assertRaises(ValueError, lambda: get_chrom_pos(30*1e9))

        self.assertEqual(get_chrom_pos(1e9 + 12345), ('1', 12345))
        self.assertEqual(get_chrom_pos(22*1e9 + 12345), ('22', 12345))
        self.assertEqual(get_chrom_pos(23*1e9 + 12345), ('X', 12345))
        self.assertEqual(get_chrom_pos(24*1e9 + 12345), ('Y', 12345))
        self.assertEqual(get_chrom_pos(25*1e9 + 12345), ('M', 12345))
