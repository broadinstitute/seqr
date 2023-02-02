from reference_data.models import RefseqTranscript
from reference_data.management.tests.test_utils import ReferenceDataCommandTestCase


class UpdateRefseqTest(ReferenceDataCommandTestCase):
    URL = 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_39/gencode.v39.metadata.RefSeq.gz'
    DATA = [
        'ENST00000258436.1	NR_026874.2	\n',
        'ENST00000258436.1	NR_122045.1	\n',
        'ENST00000342066.8	NM_152486.3	NP_689699.2\n',
        'ENST00000624735.7	NM_015658.4	NP_056473.3\n',
    ]

    def test_update_refseq_command(self):
        self._test_update_command(
            'update_refseq', 'RefseqTranscript', created_records=2, skipped_records=2)

        self.assertEqual(RefseqTranscript.objects.count(), 2)
        self.assertListEqual(
            list(RefseqTranscript.objects.order_by('transcript_id').values('transcript__transcript_id', 'refseq_id')), [
                {'transcript__transcript_id': 'ENST00000258436', 'refseq_id': 'NR_026874.2'},
                {'transcript__transcript_id': 'ENST00000624735', 'refseq_id': 'NM_015658.4'}
            ])
