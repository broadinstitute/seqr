from reference_data.models import ClinGen
from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase

class UpdateClinGenTest(ReferenceDataCommandTestCase):
    URL = 'https://search.clinicalgenome.org/kb/gene-dosage/download'
    DATA = '\r\n'.join([
        '"CLINGEN DOSAGE SENSITIVITY CURATIONS"',
        '"FILE CREATED: 2022-04-01"',
        '"WEBPAGE: https://search.clinicalgenome.org/kb/gene-dosage"',
        '"+++++++++++","+++++++","++++++++++++++++++","+++++++++++++++++","+++++++++++++","++++"',
        '"GENE SYMBOL","HGNC ID","HAPLOINSUFFICIENCY","TRIPLOSENSITIVITY","ONLINE REPORT","DATE"',
        '"+++++++++++","+++++++","++++++++++++++++++","+++++++++++++++++","+++++++++++++","++++"',
        '"MED13","HGNC:10896","No Evidence for Haploinsufficiency","Dosage Sensitivity Unlikely","https://dosage.clinicalgenome.org/clingen_gene.cgi?sym=MED13&subject=","2016-08-22T17:47:47Z"',
        '"OR4F5","HGNC:17217","Gene Associated with Autosomal Recessive Phenotype","No Evidence for Triplosensitivity","https://dosage.clinicalgenome.org/clingen_gene.cgi?sym=OR4F5&subject=","2014-12-11T15:51:23Z"',
        '"WASH7P","HGNC:16636","Sufficient Evidence for Haploinsufficiency","","https://dosage.clinicalgenome.org/clingen_gene.cgi?sym=WASH7P&subject=","2020-07-08T16:37:14Z"',
    ])

    def test_update_clingen_command(self):
        self.mock_clingen_version_patcher.stop()
        self._test_update_command('ClinGen', '2022-04-01', created_records=2)

        self.assertEqual(ClinGen.objects.count(), 2)
        record = ClinGen.objects.get(gene__gene_id='ENSG00000186092')
        self.assertEqual(record.haploinsufficiency, 'Gene Associated with Autosomal Recessive Phenotype')
        self.assertEqual(record.triplosensitivity, 'No Evidence')
        self.assertEqual(record.href, 'https://dosage.clinicalgenome.org/clingen_gene.cgi?sym=OR4F5&subject=')

