import unittest

import hail as hl

from loading_pipeline.lib.methods.relatedness import call_relatedness

TEST_SEX_AND_RELATEDNESS_CALLSET_MT = (
    'loading_pipeline/var/test/callsets/sex_and_relatedness_1.mt'
)


class RelatednessTest(unittest.TestCase):
    def test_call_relatedness(self):
        mt = hl.read_matrix_table(TEST_SEX_AND_RELATEDNESS_CALLSET_MT)
        ht = call_relatedness(
            mt,
            None,
        )
        self.assertCountEqual(
            ht.collect(),
            [
                hl.Struct(
                    i='ROS_006_18Y03226_D1',
                    j='ROS_007_19Y05939_D1',
                    ibd0=0.0,
                    ibd1=1.0,
                    ibd2=0.0,
                    pi_hat=0.5,
                ),
                hl.Struct(
                    i='ROS_007_19Y05939_D1',
                    j='ROS_007_19Y05987_D1',
                    ibd0=0.0,
                    ibd1=1.0,
                    ibd2=0.0,
                    pi_hat=0.5,
                ),
            ],
        )
