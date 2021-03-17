from django.core.management import call_command

from reference_data.models import MGI, dbNSFPGene
from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase
from django.core.management.base import CommandError


class UpdateMgiTest(ReferenceDataCommandTestCase):
    URL = 'http://www.informatics.jax.org/downloads/reports/HMD_HumanPhenotype.rpt'
    DATA = [
        'A1BG	  1	11167	yes	A1bg	  MGI:2152878		\n',
        'A1CF	  29974	16363	yes	A1cf	  MGI:1917115	  MP:0005367 MP:0005370 MP:0005385 MP:0010768 MP:0005369 MP:0005376 MP:0005384 MP:0005378\n',
        'A2M	  2	37248	yes	A2m	  MGI:2449119\n',
        'A3GALT2	  127550	16326	yes	A3galt2	  MGI:2685279\n',
    ]

    def test_update_mgi_command(self):
        self._test_update_command('update_mgi', 'MGI', existing_records=0, created_records=2, skipped_records=2)

        self.assertEqual(MGI.objects.all().count(), 2)
        record = MGI.objects.get(gene__gene_id = 'ENSG00000223972')
        self.assertEqual(record.marker_id, 'MGI:2152878')

        # Test exception with no dbNSFPGene records
        dbNSFPGene.objects.all().delete()
        with self.assertRaises(CommandError) as ce:
            call_command('update_mgi')
        self.assertEqual(str(ce.exception), 'dbNSFPGene table is empty. Run \'./manage.py update_dbnsfp_gene\' before running this command.')
