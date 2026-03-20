from django.core.management import call_command
import mock

from seqr.models import Project, Sample, SavedVariant
from seqr.views.utils.test_utils import AnvilAuthenticationTestCase

MOCK_GCNV_DATA = [
    b'chr\tstart\tend\tname\tsample\tsample_fix\tsvtype\tGT\tCN\tNP\tQA\tQS\tQSE\tQSS\tploidy\tstrand\tvariant_name\tID\trmsstd\tdefragmented\tvaf\tvac\tlt100_raw_calls\tlt10_highQS_rare_calls\tPASS_SAMPLE\tPASS_FREQ\tPASS_QS\tHIGH_QUALITY\tgenes_any_overlap\tgenes_any_overlap_exonsPerGene\tgenes_any_overlap_totalExons\tgenes_strict_overlap\tgenes_strict_overlap_exonsPerGene\tgenes_strict_overlap_totalExons\tgenes_CG\tgenes_LOF\tgenes_any_overlap_Ensemble_ID\tidentical\tpartial_ovl\tany_ovl\tno_ovl\tsource',
    b'chr10\t122599967\t122600191\tCASE_7_Y_cnv_57308\tC1933_010-001_v1_Exome_GCP\t010-001_v1_Exome_C1933\tDEL\t1\t1\t1\t7\t7\t7\t72\t\t-\tprefix_70191\t326536\t0\tFALSE\t0.05066805\t1077\tTRUE\tTRUE\tTRUE\tFALSE\tFALSE\tFALSE\tDMBT1\t1\t1\tNA\t0\t0\tNA\tDMBT1\tENSG00000187908.19\tcluster_10_CASE_cnv_46117\tcluster_10_CASE_cnv_46117\tcluster_10_CASE_cnv_46117;prefix_19107\tFALSE\tround2',
]


class SetSavedVariantKeyTest(AnvilAuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'report_variants', 'clickhouse_saved_variants']

    MOCK_GCNV_DATA = MOCK_GCNV_DATA

    @classmethod
    def setUpTestData(cls):
        Project.objects.filter(id=3).update(genome_version='38')
        Sample.objects.filter(guid='S000154_na20889').update(dataset_type='SV', is_active=True)
        for sv in SavedVariant.objects.filter(key__isnull=False):
            sv.saved_variant_json = {
                'genotypes': sv.genotypes, 'populations': {'gnomad': {'af': 0.01}},
            }
            if sv.guid == 'SV0000009_25000014783_r0004_no':
                sv.saved_variant_json['populations']['seqr'] = {'af': 0.019480518996715546, 'ac': 3, 'an': 154}
            sv.save()
        SavedVariant.objects.update(key=None)

    @mock.patch('clickhouse_search.management.commands.set_saved_variant_key.BATCH_SIZE', 2)
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_command(self, mock_subprocess):
        mock_subprocess.return_value.stdout = self.MOCK_GCNV_DATA
        mock_subprocess.return_value.wait.return_value = 0

        call_command('set_saved_variant_key')
        self.assert_json_logs(user=None, expected=[
            ('Finding keys for 1 MITO (GRCh38) variant ids', None),
            ('Found 1 keys', None),
            ('Updated batch of 1', None),
            ('Updated keys for 1 MITO (GRCh38) variants', None),
            ('Finding keys for 1 SNV_INDEL (GRCh38) variant ids', None),
            ('Found 1 keys', None),
            ('Updated batch of 2', None),
            ('Updated keys for 2 SNV_INDEL (GRCh38) variants', None),
            ('Finding keys for 2 SV_WGS (GRCh38) variant ids', None),
            ('Found 1 keys', None),
            ('Updated batch of 1', None),
            ('Updated keys for 1 SV_WGS (GRCh38) variants', None),
            ('No key found for 1 variants', None),
            ('Finding keys for 1 SV_WES (GRCh38) variant ids', None),
            ('Found 1 keys', None),
            ('Updated batch of 1', None),
            ('Updated keys for 1 SV_WES (GRCh38) variants', None),
            ('Finding keys for 7 SNV_INDEL (GRCh37) variant ids', None),
            ('Found 1 keys', None),
            ('Updated batch of 1', None),
            ('Updated keys for 1 SNV_INDEL (GRCh37) variants', None),
            ('No key found for 6 variants', None),
            ('6 variants have no key, 0 of which have no search data, 6 of which are absent from the hail backend.', None),
            ('Cleared saved json for 6 variants with keys', None),
            ('Done', None),
        ])

        saved_variants = list(SavedVariant.objects.order_by('guid').values('guid', 'key', 'variant_id', 'saved_variant_json'))
        expected_saved_variants = [
            {'guid': 'SV0000001_2103343353_r0390_100', 'key': None, 'variant_id': '21-3343353-GAGA-G', 'saved_variant_json': mock.ANY},
            {'guid': 'SV0000002_1248367227_r0390_100', 'key': 100, 'variant_id': '1-248367227-TC-T', 'saved_variant_json': {}},
            {'guid': 'SV0000006_1248367227_r0003_tes', 'key': 100, 'variant_id': '1-248367227-TC-T', 'saved_variant_json': {}},
            {'guid': 'SV0000006_1248367227_r0004_non', 'key': 100, 'variant_id': '1-248367227-TC-T', 'saved_variant_json': {}},
            {'guid': 'SV0000007_prefix_19107_DEL_r00', 'key': 111, 'variant_id': 'prefix_19107_DEL', 'saved_variant_json': {}},
            {'guid': 'SV0000009_25000014783_r0004_no', 'key': 100, 'variant_id': 'M-14783-T-C', 'saved_variant_json': {}},
            {'guid': 'SV0000013_prefix_19107_DEL_r00', 'key': 101, 'variant_id': 'suffix_19107_DEL_013746', 'saved_variant_json': {}},
            {'guid': 'SV0027166_191912634_r0384_rare', 'key': None, 'variant_id': '19-1912634-C-T', 'saved_variant_json': mock.ANY},
            {'guid': 'SV0027167_191912633_r0384_rare', 'key': None, 'variant_id': '19-1912633-G-T', 'saved_variant_json': mock.ANY},
            {'guid': 'SV0027168_191912632_r0384_rare', 'key': None, 'variant_id': '19-1912632-G-C', 'saved_variant_json': mock.ANY},
            {'guid': 'SV0059956_11560662_f019313_1', 'key': None, 'variant_id': '1-46859832-G-A', 'saved_variant_json': mock.ANY},
            {'guid': 'SV0059957_11562437_f019313_1', 'key': None, 'variant_id': '1-1562437-G-CA', 'saved_variant_json': mock.ANY},
        ]
        self.assertListEqual(saved_variants, expected_saved_variants)

        # Reloading is a no-op
        self.reset_logs()
        call_command('set_saved_variant_key')
        self.assert_json_logs(user=None, expected=[
            ('Finding keys for 6 SNV_INDEL (GRCh37) variant ids', None),
            ('Found 0 keys', None),
            ('6 variants have no key, 0 of which have no search data, 6 of which are absent from the hail backend.', None),
            ('Cleared saved json for 0 variants with keys', None),
            ('Done', None),
        ])
        self.assertListEqual(
            list(SavedVariant.objects.order_by('guid').values('guid', 'key', 'variant_id', 'saved_variant_json')),
            expected_saved_variants,
        )

class SetSavedVariantKeyFailedMappingTest(SetSavedVariantKeyTest):
    fixtures = ['users', '1kg_project', 'report_variants']

    MOCK_GCNV_DATA = MOCK_GCNV_DATA[:1]

    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_command(self, mock_subprocess):
        mock_subprocess.return_value.stdout = self.MOCK_GCNV_DATA
        mock_subprocess.return_value.wait.return_value = 0

        call_command('set_saved_variant_key')
        self.assert_json_logs(user=None, expected=[
            ('Finding keys for 1 MITO (GRCh38) variant ids', None),
            ('Found 0 keys', None),
            ('Finding keys for 2 SNV_INDEL (GRCh38) variant ids', None),
            ('Found 0 keys', None),
            ('3 variants have no key, 1 of which have no search data, 1 of which are absent from the hail backend.', None),
            ('1 remaining variants: M-14783-T-C - fam14', None),
            ('Finding keys for 2 SV_WGS (GRCh38) variant ids', None),
            ('Found 0 keys', None),
            ('Finding keys for 2 SV_WES (GRCh38) variant ids', None),
            ('Found 0 keys', None),
            ('2 SV variants have no key, 0 of which have no search data, 0 of which are known to have dropped out of the callset.', None),
            ('1 remaining SV WES variants prefix_19107_DEL - 12', None),
            ('1 remaining SV WGS variants suffix_19107_DEL_013746 - fam14', None),
            ('Finding keys for 7 SNV_INDEL (GRCh37) variant ids', None),
            ('Found 0 keys', None),
            ('7 variants have no key, 0 of which have no search data, 7 of which are absent from the hail backend.', None),
            ('Cleared saved json for 0 variants with keys', None),
            ('Done', None),
        ])

