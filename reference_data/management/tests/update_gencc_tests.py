import mock

from reference_data.models import GenCC
from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase


class UpdateGeneCCTest(ReferenceDataCommandTestCase):
    URL = 'https://search.thegencc.org/download/action/submissions-export-csv'
    DATA = '\r\n'.join([
        '"uuid","gene_curie","gene_symbol","disease_title","classification_title","moi_title","submitter_title","submitted_as_date","submitted_run_date"',
        '"GENCC_000101-HGNC_10896-OMIM_182212-HP_0000006-GENCC_100001","HGNC:10896","MED13","Shprintzen-Goldberg syndrome","Moderate","Autosomal dominant","Ambry Genetics","3/30/18 13:31","12/24/20"',
        '"GENCC_000101-HGNC_17217-MONDO_0005258-HP_0000006-GENCC_100004","HGNC:17217","OR4F5","autism spectrum disorder","Limited","Autosomal dominant","Ambry Genetics","7/29/19 19:04","9/28/21"',
        '"GENCC_000101-HGNC_16636-OMIM_171300-HP_0000006-GENCC_100003","HGNC:16636","WASH7P","phaeochromocytoma","Moderate","Autosomal dominant","Orphanet","12/4/19 13:30","12/24/20"',
        '"GENCC_000101-HGNC_3039-MONDO_0005258-HP_0000006-GENCC_100003","HGNC:17217","OR4F5","autism spectrum disorder","Definitive","Autosomal dominant","Genomics England PanelApp","1/7/19 19:04","9/28/21"',
    ])

    def setUp(self):
        super().setUp()
        self.mock_get_file_last_modified_patcher.stop()
        patcher = mock.patch('reference_data.models.Omim.get_current_version')
        patcher.start().return_value = self.mock_get_file_last_modified.return_value
        self.addCleanup(patcher.stop)

    def test_update_gencc_command(self):
        last_modified = 'Fri, 28 Mar 2025 11:00:00 GMT'
        self._test_update_command('GenCC', last_modified, created_records=2, head_response={
            'headers': {'Last-Modified': last_modified}
        })

        self.assertEqual(GenCC.objects.count(), 2)
        record = GenCC.objects.get(gene__gene_id='ENSG00000186092')
        self.assertEqual(record.hgnc_id, 'HGNC:17217')
        self.assertListEqual(record.classifications, [
            {'disease': 'autism spectrum disorder','classification': 'Limited', 'moi': 'Autosomal dominant',
             'submitter': 'Ambry Genetics', 'date': '7/29/19 19:04',},
            {'disease': 'autism spectrum disorder', 'classification': 'Definitive', 'moi': 'Autosomal dominant',
             'submitter': 'Genomics England PanelApp', 'date': '1/7/19 19:04', },
        ])
