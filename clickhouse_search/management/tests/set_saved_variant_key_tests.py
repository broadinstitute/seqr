from django.core.management import call_command
import mock

from seqr.models import Project, SavedVariant
from seqr.views.utils.test_utils import AnvilAuthenticationTestCase

class SetSavedVariantKeyTest(AnvilAuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'report_variants', 'clickhouse_saved_variants']

    SKIP_RESET_VARIANT_JSON = True

    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_command(self, mock_subprocess):
        Project.objects.filter(id=3).update(genome_version='38')
        SavedVariant.objects.update(key=None)

        mock_subprocess.return_value.stdout = [
            b'chr\tstart\tend\tname\tsample\tsample_fix\tsvtype\tGT\tCN\tNP\tQA\tQS\tQSE\tQSS\tploidy\tstrand\tvariant_name\tID\trmsstd\tdefragmented\tvaf\tvac\tlt100_raw_calls\tlt10_highQS_rare_calls\tPASS_SAMPLE\tPASS_FREQ\tPASS_QS\tHIGH_QUALITY\tgenes_any_overlap\tgenes_any_overlap_exonsPerGene\tgenes_any_overlap_totalExons\tgenes_strict_overlap\tgenes_strict_overlap_exonsPerGene\tgenes_strict_overlap_totalExons\tgenes_CG\tgenes_LOF\tgenes_any_overlap_Ensemble_ID\tidentical\tpartial_ovl\tany_ovl\tno_ovl\tsource',
            b'chr10\t122599967\t122600191\tCASE_7_Y_cnv_57308\tC1933_010-001_v1_Exome_GCP\t010-001_v1_Exome_C1933\tDEL\t1\t1\t1\t7\t7\t7\t72-\tsuffix_44766\t326536\t0\tFALSE\t0.05066805\t1077\tTRUE\tTRUE\tTRUE\tFALSE\tFALSE\tFALSE\tDMBT1\t1\t1\tNA\t0\t0\tNA\tDMBT1\tENSG00000187908.19\tcluster_10_CASE_cnv_46117\tcluster_10_CASE_cnv_46117\tcluster_10_CASE_cnv_46117\tFALSE\tround2',
        ]

        call_command('set_saved_variant_key')
        self.assert_json_logs(user=None, expected=[
            ('Updated genotypes for 8 variants', None),
            ('Finding keys for 1 MITO (GRCh38) variant ids', None),
            ('Found 1 keys', None),
            ('Updated keys for 1 MITO (GRCh38) variants', None),
            ('Finding keys for 1 SNV_INDEL (GRCh38) variant ids', None),
            ('Found 1 keys', None),
            ('Updated keys for 2 SNV_INDEL (GRCh38) variants', None),
            ('Finding keys for 2 SV_WGS (GRCh38) variant ids', None),
            ('Found 0 keys', None),
            ('Finding keys for 2 SV_WES (GRCh38) variant ids', None),
            ('Found 1 keys', None),
            ('Updated keys for 1 SV_WES (GRCh38) variants', None),
            ('No key found for 1 variants', None),
            ('1 SV variants have no key, 0 of which have no search data, 0 of which are known to have dropped out of the callset.', None),
            ('==> gsutil cat gs://seqr-datasets-gcnv/GRCh38/RDG_WES_Broad_Internal/v4/CMG_gCNV_2022_annotated.ensembl.round2_3.strvctvre.tsv.gz | gunzip -c -q - ', None),
            ('Mapping reloaded SV_WGS IDs to latest version', None),
            ('Finding keys for 1 SV_WGS (GRCh38) variant ids', None),
            ('Found 1 keys', None),
            ('Updated keys for 1 SV_WGS (GRCh38) variants', None),
            ('Finding keys for 7 SNV_INDEL (GRCh37) variant ids', None),
            ('Found 1 keys', None),
            ('Updated keys for 1 SNV_INDEL (GRCh37) variants', None),
            ('No key found for 6 variants', None),
            ('6 variants have no key, 0 of which have no search data, 6 of which are absent from the hail backend.', None),
            ('Cleared saved json for 6 variants with keys', None),
            ('Done', None),
        ])

        saved_variants = list(SavedVariant.objects.order_by('guid').values('guid', 'key', 'dataset_type', 'genotypes', 'saved_variant_json'))
        self.assertListEqual(saved_variants, [
            {'guid': 'SV0000001_2103343353_r0390_100', 'key': None, 'dataset_type': None, 'genotypes': mock.ANY, 'saved_variant_json': mock.ANY},
            {'guid': 'SV0000002_1248367227_r0390_100', 'key': 100, 'dataset_type': 'SNV_INDEL', 'genotypes': {'I000004_hg00731': {'numAlt': 2}, 'I000005_hg00732': {'numAlt': 1}}, 'saved_variant_json': {}},
            {'guid': 'SV0000006_1248367227_r0003_tes', 'key': 100, 'dataset_type': 'SNV_INDEL', 'genotypes': {'I000002_na19675': mock.ANY, 'I000017_na20889': mock.ANY}, 'saved_variant_json': {}},
            {'guid': 'SV0000006_1248367227_r0004_non', 'key': 100, 'dataset_type': 'SNV_INDEL', 'genotypes': {'I000018_na21234': {'sampleId': 'NA20885', 'ab': 0.0, 'gq': 99.0, 'numAlt': 1}}, 'saved_variant_json': {}},
            {'guid': 'SV0000007_prefix_19107_DEL_r00', 'key': 111, 'dataset_type': 'SV_WES', 'genotypes': {'I000017_na20889': { 'cn': 1, 'sampleId': 'NA20885', 'numAlt': -1,  'defragged': False, 'qs': 33, 'numExon': 2}}, 'saved_variant_json': {}},
            {'guid': 'SV0000009_25000014783_r0004_no', 'key': 100, 'dataset_type': 'MITO', 'genotypes': {'I000018_na21234': mock.ANY}, 'saved_variant_json': {}},
            {'guid': 'SV0000013_prefix_19107_DEL_r00', 'key': 111, 'dataset_type': 'SV_WGS', 'genotypes': {'I000017_na20889': mock.ANY}, 'saved_variant_json': {}},
            {'guid': 'SV0027166_191912634_r0384_rare', 'key': None, 'dataset_type': None, 'genotypes': mock.ANY, 'saved_variant_json': mock.ANY},
            {'guid': 'SV0027167_191912633_r0384_rare', 'key': None, 'dataset_type': None, 'genotypes': mock.ANY, 'saved_variant_json': mock.ANY},
            {'guid': 'SV0027168_191912632_r0384_rare', 'key': None, 'dataset_type': None, 'genotypes': mock.ANY, 'saved_variant_json': mock.ANY},
            {'guid': 'SV0059956_11560662_f019313_1', 'key': None, 'dataset_type': None, 'genotypes': mock.ANY, 'saved_variant_json': mock.ANY},
            {'guid': 'SV0059957_11562437_f019313_1', 'key': None, 'dataset_type': None, 'genotypes': mock.ANY, 'saved_variant_json': mock.ANY},
        ])
        self.assertTrue(all(v['genotypes'] == v['saved_variant_json']['genotypes'] for v in saved_variants[:1] + saved_variants[7:]))