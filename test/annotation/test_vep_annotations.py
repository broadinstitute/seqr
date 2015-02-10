import unittest

from xbrowse.annotation.vep_annotations import get_worst_vep_annotation


class VepAnnotationsTests(unittest.TestCase):

    def test_get_worst_vep_annotation(self):
        self.assertEqual(
            get_worst_vep_annotation(["intron_variant", "non_coding_transcript_variant"]), 'intron_variant')
        self.assertEqual(
            get_worst_vep_annotation(["feature_elongation", "5_prime_UTR_variant", "stop_lost"]), 'stop_lost')
        self.assertRaisesRegexp(
            ValueError, "Unexpected", lambda: get_worst_vep_annotation(["some weird annotation"]))

if __name__ == '__main__':
    unittest.main()