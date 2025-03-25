from django.core.management import call_command

from reference_data.models import MGI, dbNSFPGene
from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase


class UpdateMgiTest(ReferenceDataCommandTestCase):
    URL = 'https://storage.googleapis.com/seqr-reference-data/mgi/HMD_HumanPhenotype.rpt.txt'
    DATA = [
        'A1BG	  1	11167	  MGI:2152878		\n',
        'A1CF	  29974	16363	  MGI:1917115	  MP:0005367 MP:0005370 MP:0005385 MP:0010768 MP:0005369 MP:0005376 MP:0005384 MP:0005378\n',
        'A2M	  2	37248	  MGI:2449119\n',
        'A3GALT2	  127550	16326	  MGI:2685279\n',
    ]

    def test_update_mgi_command(self):
        self._test_update_command('update_mgi', 'MGI', existing_records=0, created_records=2, skipped_records=2)

        self.assertEqual(MGI.objects.all().count(), 2)
        record = MGI.objects.get(gene__gene_id = 'ENSG00000223972')
        self.assertEqual(record.marker_id, 'MGI:2152878')

        # Test exception with no dbNSFPGene records
        dbNSFPGene.objects.all().delete()
        with self.assertRaises(ValueError) as e:
            call_command('update_mgi')
        self.assertEqual(str(e.exception),'Related data is missing to load MGI: entrez_id_to_gene')
