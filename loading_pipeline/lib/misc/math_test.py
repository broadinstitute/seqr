import unittest

from loading_pipeline.lib.misc.math import constrain


class TestConstrainFunction(unittest.TestCase):
    def test_constrain(self):
        self.assertEqual(constrain(5, 0, 10), 5)
        self.assertEqual(constrain(-3, 0, 10), 0)
        self.assertEqual(constrain(15, 0, 10), 10)
        with self.assertRaises(ValueError):
            constrain(5, 10, 0)
