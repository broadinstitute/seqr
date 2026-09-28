import unittest

import hail as hl

from loading_pipeline.lib.tasks.exports.misc import (
    sorted_hl_struct,
)


class MiscTest(unittest.TestCase):
    def test_sorted_hl_struct(self) -> None:
        struct = hl.Struct(
            z=5,
            y=hl.Struct(b=2, a=hl.Struct(d=4, c=3)),
            x=hl.Struct(k=9),
        )
        self.assertEqual(
            sorted_hl_struct(struct),
            hl.Struct(x=hl.Struct(k=9), y=hl.Struct(a=hl.Struct(c=3, d=4), b=2), z=5),
        )
