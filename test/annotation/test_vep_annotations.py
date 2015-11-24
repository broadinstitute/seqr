import unittest

from xbrowse.annotation.vep_annotations import get_worst_vep_annotation
from xbrowse.annotation.vep_annotations import get_worst_vep_annotation_index


class VepAnnotationsTests(unittest.TestCase):

    def test_get_worst_vep_annotation_index(self):
        annotations = [
            {'Feature_type': 'Transcript', 'GMAF': '', 'Feature': 'ENST00000479049', 'Consequence': 'non_coding_transcript_exon_variant', 'Protein_position': '', 'Gene': 'ENSG00000135636', 'STRAND': '1', 'CANONICAL': ''},
            {'Feature_type': 'Transcript', 'GMAF': '', 'Feature': 'ENST00000258104', 'Consequence': 'stop_gained', 'Protein_position': '1968', 'Gene': 'ENSG00000135636', 'STRAND': '1', 'CANONICAL': ''},
            {'Feature_type': 'Transcript', 'GMAF': '', 'Feature': 'ENST00000394120', 'Consequence': 'stop_gained', 'Protein_position': '1969', 'Gene': 'ENSG00000135636', 'STRAND': '1', 'CANONICAL': ''},
            {'Feature_type': 'Transcript', 'GMAF': '', 'Feature': 'ENST00000409366', 'Consequence': 'stop_gained', 'Protein_position': '1990', 'Gene': 'ENSG00000135636', 'STRAND': '1', 'CANONICAL': ''},
            {'Feature_type': 'Transcript', 'GMAF': '', 'Feature': 'ENST00000409582', 'Consequence': 'stop_gained', 'Protein_position': '2006', 'Gene': 'ENSG00000135636', 'STRAND': '1', 'CANONICAL': ''},
            {'Feature_type': 'Transcript', 'GMAF': '', 'Feature': 'ENST00000409651', 'Consequence': 'stop_gained', 'Protein_position': '2000', 'Gene': 'ENSG00000135636', 'STRAND': '1', 'CANONICAL': ''},
            {'Feature_type': 'Transcript', 'GMAF': '', 'Feature': 'ENST00000409744', 'Consequence': 'stop_gained', 'Protein_position': '1976', 'Gene': 'ENSG00000135636', 'STRAND': '1', 'CANONICAL': ''},
            {'Feature_type': 'Transcript', 'GMAF': '', 'Feature': 'ENST00000409762', 'Consequence': 'stop_gained', 'Protein_position': '1985', 'Gene': 'ENSG00000135636', 'STRAND': '1', 'CANONICAL': ''},
            {'Feature_type': 'Transcript', 'GMAF': '', 'Feature': 'ENST00000410020', 'Consequence': 'stop_gained', 'Protein_position': '2007', 'Gene': 'ENSG00000135636', 'STRAND': '1', 'CANONICAL': 'YES'},
            {'Feature_type': 'Transcript', 'GMAF': '', 'Feature': 'ENST00000410041', 'Consequence': 'stop_gained', 'Protein_position': '1986', 'Gene': 'ENSG00000135636', 'STRAND': '1', 'CANONICAL': ''},
            {'Feature_type': 'Transcript', 'GMAF': '', 'Feature': 'ENST00000413539', 'Consequence': 'stop_gained', 'Protein_position': '1999', 'Gene': 'ENSG00000135636', 'STRAND': '1', 'CANONICAL': ''},
            {'Feature_type': 'Transcript', 'GMAF': '', 'Feature': 'ENST00000429174', 'Consequence': 'stop_gained', 'Protein_position': '1989', 'Gene': 'ENSG00000135636', 'STRAND': '1', 'CANONICAL': ''},
        ]

        # convert keys to lower case
        for annot_dict in annotations:
            for key, value in annot_dict.items():
                annot_dict[key.lower()] = value
            annot_dict['is_nc'] = False
            annot_dict['is_nmd'] = False

        # test basic case
        self.assertEqual(get_worst_vep_annotation_index(annotations), 8)

        # test 2 annotations being canonical - choose the worst one
        annotations[0]['canonical'] = 'YES'
        self.assertEqual(get_worst_vep_annotation_index(annotations), 8)

        # test 0 annotations being canonical - choose the worst one
        annotations[0]['canonical'] = ''
        annotations[8]['canonical'] = ''
        i = get_worst_vep_annotation_index(annotations)
        self.assertTrue(annotations[i]['consequence'], 'stop_gained')
        self.assertEqual(annotations[i]['feature'], 'ENST00000258104')

        # test where worst-affected transcript is not the canonical one
        annotations[1]['consequence'] = 'splice_donor_variant'
        self.assertEqual(get_worst_vep_annotation_index(annotations), 1)
        self.assertFalse(annotations[1]['canonical'])

        # test the gene_id arg
        annotations[8]['canonical'] = 'YES'
        annotations[1]['gene'] = 'OTHER_GENE1'
        annotations[2]['gene'] = 'OTHER_GENE2'
        self.assertEqual(get_worst_vep_annotation_index(annotations, gene_id='OTHER_GENE1'), 1)
        self.assertEqual(get_worst_vep_annotation_index(annotations, gene_id='OTHER_GENE2'), 2)

    def test_get_worst_vep_annotation(self):
        self.assertEqual(
            get_worst_vep_annotation(["intron_variant", "non_coding_transcript_variant"]), 'intron_variant')
        self.assertEqual(
            get_worst_vep_annotation(["feature_elongation", "5_prime_UTR_variant", "stop_lost"]), 'stop_lost')
        self.assertRaisesRegexp(
            ValueError, "Unexpected", lambda: get_worst_vep_annotation(["some weird annotation"]))

if __name__ == '__main__':
    unittest.main()