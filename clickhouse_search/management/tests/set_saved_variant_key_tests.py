from django.core.management import call_command
import mock

from seqr.models import Project, Sample, SavedVariant
from seqr.views.utils.test_utils import AnvilAuthenticationTestCase

MOCK_GCNV_DATA = [
    b'chr\tstart\tend\tname\tsample\tsample_fix\tsvtype\tGT\tCN\tNP\tQA\tQS\tQSE\tQSS\tploidy\tstrand\tvariant_name\tID\trmsstd\tdefragmented\tvaf\tvac\tlt100_raw_calls\tlt10_highQS_rare_calls\tPASS_SAMPLE\tPASS_FREQ\tPASS_QS\tHIGH_QUALITY\tgenes_any_overlap\tgenes_any_overlap_exonsPerGene\tgenes_any_overlap_totalExons\tgenes_strict_overlap\tgenes_strict_overlap_exonsPerGene\tgenes_strict_overlap_totalExons\tgenes_CG\tgenes_LOF\tgenes_any_overlap_Ensemble_ID\tidentical\tpartial_ovl\tany_ovl\tno_ovl\tsource',
    b'chr10\t122599967\t122600191\tCASE_7_Y_cnv_57308\tC1933_010-001_v1_Exome_GCP\t010-001_v1_Exome_C1933\tDEL\t1\t1\t1\t7\t7\t7\t72\t\t-\tprefix_70191\t326536\t0\tFALSE\t0.05066805\t1077\tTRUE\tTRUE\tTRUE\tFALSE\tFALSE\tFALSE\tDMBT1\t1\t1\tNA\t0\t0\tNA\tDMBT1\tENSG00000187908.19\tcluster_10_CASE_cnv_46117\tcluster_10_CASE_cnv_46117\tcluster_10_CASE_cnv_46117;prefix_19107\tFALSE\tround2',
]
#
# SAVED_VARIANT_JSON = {
#     'SV0000002_1248367227_r0390_100': {
#             "clinvar": {
#                 "pathogenicity": "Uncertain_significance",
#                 "alleleId": 12345,
#                 "assertions": null,
#                 "conditions": null,
#                 "conflictingPathogenicities": null,
#                 "submitters": null,
#                 "goldStars": null
#             },
#             "liftedOverGenomeVersion": "38",
#             "familyGuids": [
#                 "F000001_1"
#             ],
#             "liftedOverPos": "",
#             "populations": {
#                 "callset": {
#                     "ac": null,
#                     "an": null,
#                     "af": null
#                 },
#                 "g1k": {
#                     "ac": null,
#                     "an": null,
#                     "af": 0.0
#                 },
#                 "gnomad_genomes": {
#                     "hemi": null,
#                     "ac": null,
#                     "an": null,
#                     "hom": null,
#                     "af": 0.00012925741614425127
#                 },
#                 "gnomad_exomes": {
#                     "hemi": null,
#                     "ac": null,
#                     "an": null,
#                     "hom": null,
#                     "af": 6.505916317651364e-05
#                 },
#                 "exac": {
#                     "hemi": null,
#                     "ac": null,
#                     "an": null,
#                     "hom": null,
#                     "af": 0.0006726888333653661
#                 },
#                 "topmed": {
#                     "ac": null,
#                     "an": null,
#                     "af": null
#                 }
#             },
#             "genomeVersion": "37",
#             "pos": 248367227,
#             "predictions": {
#                 "eigen": null,
#                 "revel": null,
#                 "sift": null,
#                 "cadd": "27.2",
#                 "metasvm": "",
#                 "mpc": null,
#                 "splice_ai": null,
#                 "phastcons_100_vert": null,
#                 "mut_taster": null,
#                 "fathmm": null,
#                 "polyphen": null,
#                 "dann": null,
#                 "primate_ai": null,
#                 "gerp_rs": null
#             },
#             "hgmd": {
#                 "accession": null,
#                 "class": null
#             },
#             "rsid": null,
#             "liftedOverChrom": "",
#             "transcripts": {
#                 "ENSG00000135953": [
#                     {"transcriptId": "ENST00000371839", "biotype": "protein_coding", "geneId": "ENSG00000135953"}
#                 ],
#                 "ENSG00000240361": []
#             },
#             "chrom": "1",
#             "genotypes": {
#                 "I000004_hg00731": {
#                     "numAlt": 2
#                 },
#                 "I000005_hg00732": {
#                     "numAlt": 1
#                 }
#             },
#             "CAID": "CA1501729"
#         },
#     'SV0000006_1248367227_r0003_tes': {
#             "clinvar": {
#                 "pathogenicity": "Uncertain_significance",
#                 "alleleId": 12345,
#                 "assertions": null,
#                 "conditions": null,
#                 "conflictingPathogenicities": null,
#                 "submitters": null,
#                 "goldStars": null
#             },
#             "liftedOverGenomeVersion": "38",  "liftedOverPos": "",
#             "populations": {"callset": {"ac": null, "an": null, "af": null}, "g1k": {"ac": null, "an": null, "af": 0.0},
#                 "gnomad_genomes": {"hemi": null, "ac": null, "an": null, "hom": null, "af": 0.00012925741614425127},
#                 "gnomad_exomes": {"hemi": null, "ac": null, "an": null, "hom": null, "af": 6.505916317651364e-05},
#                 "exac": {"hemi": null, "ac": null, "an": null, "hom": null, "af": 0.0006726888333653661},
#                 "topmed": {"ac": null, "an": null, "af": null}},
#             "genomeVersion": "37", "pos": 248367227, "predictions": {
#                 "eigen": null, "revel": null, "sift": null, "cadd": "27.2", "metasvm": "", "mpc": null,
#                 "splice_ai": null, "phastcons_100_vert": null, "mut_taster": null, "fathmm": null, "polyphen": null,
#                 "dann": null, "primate_ai": null, "gerp_rs": null},
#             "hgmd": {"accession": null, "class": null}, "rsid": null, "liftedOverChrom": "",
#              "mainTranscriptId": "ENST00000505820", "transcripts": {
#                 "ENSG00000135953": [
#                     {"transcriptId": "ENST00000371839", "biotype": "protein_coding", "geneId": "ENSG00000228198"}
#                 ],
#                 "ENSG00000240361": [
#                     {"transcriptId": "ENST00000505820", "lofFilter": "", "biotype": "protein_coding",
#                         "geneSymbol": "MIB2", "majorConsequence": "intron_variant", "canonical": 1,
#                         "hgvsp": "ENST00000505820.2:c.1586-17C>G", "lof": "", "lofFlags": "", "codons": "Gtg/Atg",
#                         "hgvsc": "ENST00000262738.3:c.3955G>A", "transcriptRank": 0, "geneId": "ENSG00000240361",
#                         "aminoAcids": "V/M", "cdnaPosition": "3955"}
#                 ]
#             }, "chrom": "1", "genotypes": {
#                 "I000002_na19675": {"sampleId": "NA19675", "ab": 0.5555556, "ad": null, "gq": 99, "dp": 9, "pl": null, "numAlt": 1},
#                 "I000017_na20889": {"sampleId": "NA20885", "ab": 0.0, "ad": "71,0", "gq": 99.0, "dp": "71", "pl": "0,213,1918", "numAlt": 1}
#             },
#             "CAID": "CA1501729"
#         },
#     'SV0000006_1248367227_r0004_non': {
#             "liftedOverGenomeVersion": "37",  "liftedOverPos": "", "genomeVersion": "38", "pos": 248367227,
#             "transcripts": {}, "chrom": "1", "genotypes": {
#                 "I000018_na21234": {"sampleId": "NA20885", "ab": 0.0, "gq": 99.0, "numAlt": 1}
#             },
#             "CAID": "CA1501729"
#         },
#     'SV0000009_25000014783_r0004_no': {
#             "variantId": "M-14783-T-C", "chrom": "M", "pos": 14783, "ref": "T", "alt": "C", "xpos": 25000014783,
#             "genomeVersion": "38", "liftedOverGenomeVersion": "37", "liftedOverChrom": "MT", "liftedOverPos": 14783,
#             "rsid": "rs193302982", "familyGuids": ["F000002_2"], "genotypes": {
#                 "I000018_na21234": {"sampleId": "NA20885", "numAlt": 2, "dp": 3943, "hl": 1.0, "mitoCn": 214, "contamination": 0.0, "filters": ["artifact_prone_site"]}
#             }, "populations": {"seqr": {"af": 0.019480518996715546, "ac": 3, "an": 154}, "seqr_heteroplasmy": {"af": 0.006493506487458944, "ac": 1, "an": 154},
#                 "gnomad_mito": {"af": 0.05534649267792702, "ac": 3118, "an": 56336}, "gnomad_mito_heteroplasmy": {"af": 5.3251918870955706e-05, "ac": 3, "an": 56336, "max_hl": 1.0},
#                 "helix": {"af": 0.04884607344865799, "ac": 9573, "an": 195983}, "helix_heteroplasmy": {"af": 9.184470400214195e-05, "ac": 18, "an": 195983, "max_hl": 0.962689995765686}},
#             "predictions": {"apogee": null, "haplogroup_defining": "Y", "hmtvar": null, "mitotip": null, "mut_taster": null, "sift": null, "mlc": 0.7514},
#             "commonLowHeteroplasmy": true, "mitomapPathogenic": true, "clinvar": null, "transcripts": {
#                 "ENSG00000198727": [{"aminoAcids": "L", "canonical": 1, "codons": "Tta/Cta", "geneId": "ENSG00000198727", "hgvsc": "ENST00000361789.2:c.37T>C", "hgvsp": "ENSP00000354554.2:p.Leu13=", "transcriptId": "ENST00000361789", "isLofNagnag": null, "transcriptRank": 0, "biotype": "protein_coding", "lofFilters": null, "majorConsequence": "synonymous_variant", "consequenceTerms": ["synonymous_variant"]}]},
#             "mainTranscriptId": "ENST00000361789", "selectedMainTranscriptId": null
#         },
#     'SV0000013_prefix_19107_DEL_r00': {
#             "liftedOverGenomeVersion": null,
#             "pos": 249045487,
#             "end": 249045898,
#             "xpos": 1249045487,
#             "predictions": {"strvctvre": 0.374},
#             "alt": null,
#             "numExon": 2,
#             "genotypeFilters": [],
#             "ref": null,
#             "genotypes": {
#                 "I000018_na21234": { "cn": 1, "sampleId": "NA20885", "numAlt": -1,  "defragged": false, "qs": 33, "numExon": 2}
#             },
#             "liftedOverPos": null,
#             "liftedOverChrom": null,
#             "svType": "DEL",
#             "variantId": "suffix_19107_DEL",
#             "chrom": "1",
#             "endChrom": "1",
#             "genomeVersion": "37",
#             "populations": {"sv_callset":  {}},
#             "transcripts": {"ENSG00000240361": [], "ENSG00000135953": [], "ENSG00000223972":  []}
#         }
# }

class SetSavedVariantKeyTest(AnvilAuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'report_variants', 'clickhouse_saved_variants']

    MOCK_GCNV_DATA = MOCK_GCNV_DATA

    @classmethod
    def setUpTestData(cls):
        Project.objects.filter(id=3).update(genome_version='38')
        Sample.objects.filter(guid='S000154_na20889').update(dataset_type='SV', is_active=True)
        SavedVariant.objects.update(key=None)

    @mock.patch('clickhouse_search.management.commands.set_saved_variant_key.BATCH_SIZE', 2)
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_command(self, mock_subprocess):
        mock_subprocess.return_value.stdout = self.MOCK_GCNV_DATA
        mock_subprocess.return_value.wait.return_value = 0

        call_command('set_saved_variant_key')
        self.assert_json_logs(user=None, expected=[
            ('Updated genotypes for 7 variants', None),
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

        saved_variants = list(SavedVariant.objects.order_by('guid').values('guid', 'key', 'variant_id', 'dataset_type', 'genotypes', 'saved_variant_json'))
        expected_saved_variants = [
            {'guid': 'SV0000001_2103343353_r0390_100', 'key': None, 'variant_id': '21-3343353-GAGA-G', 'dataset_type': None, 'genotypes': mock.ANY, 'saved_variant_json': mock.ANY},
            {'guid': 'SV0000002_1248367227_r0390_100', 'key': 100, 'variant_id': '1-248367227-TC-T', 'dataset_type': 'SNV_INDEL', 'genotypes': {'I000004_hg00731': {'numAlt': 2}, 'I000005_hg00732': {'numAlt': 1}}, 'saved_variant_json': {}},
            {'guid': 'SV0000006_1248367227_r0003_tes', 'key': 100, 'variant_id': '1-248367227-TC-T', 'dataset_type': 'SNV_INDEL', 'genotypes': {'I000002_na19675': mock.ANY, 'I000017_na20889': mock.ANY}, 'saved_variant_json': {}},
            {'guid': 'SV0000006_1248367227_r0004_non', 'key': 100, 'variant_id': '1-248367227-TC-T', 'dataset_type': 'SNV_INDEL', 'genotypes': {'I000018_na21234': {'sampleId': 'NA20885', 'ab': 0.0, 'gq': 99.0, 'numAlt': 1}}, 'saved_variant_json': {}},
            {'guid': 'SV0000007_prefix_19107_DEL_r00', 'key': 111, 'variant_id': 'prefix_19107_DEL', 'dataset_type': 'SV_WES', 'genotypes': {'I000017_na20889': { 'cn': 1, 'sampleId': 'NA20885', 'numAlt': -1,  'defragged': False, 'qs': 33, 'numExon': 2}}, 'saved_variant_json': {}},
            {'guid': 'SV0000009_25000014783_r0004_no', 'key': 100, 'variant_id': 'M-14783-T-C', 'dataset_type': 'MITO', 'genotypes': {'I000018_na21234': mock.ANY}, 'saved_variant_json': {}},
            {'guid': 'SV0000013_prefix_19107_DEL_r00', 'key': 101, 'variant_id': 'suffix_19107_DEL_013746', 'dataset_type': 'SV_WGS', 'genotypes': {'I000018_na21234': mock.ANY}, 'saved_variant_json': {}},
            {'guid': 'SV0027166_191912634_r0384_rare', 'key': None, 'variant_id': '19-1912634-C-T', 'dataset_type': None, 'genotypes': mock.ANY, 'saved_variant_json': mock.ANY},
            {'guid': 'SV0027167_191912633_r0384_rare', 'key': None, 'variant_id': '19-1912633-G-T', 'dataset_type': None, 'genotypes': mock.ANY, 'saved_variant_json': mock.ANY},
            {'guid': 'SV0027168_191912632_r0384_rare', 'key': None, 'variant_id': '19-1912632-G-C', 'dataset_type': None, 'genotypes': mock.ANY, 'saved_variant_json': mock.ANY},
            {'guid': 'SV0059956_11560662_f019313_1', 'key': None, 'variant_id': '1-46859832-G-A', 'dataset_type': None, 'genotypes': mock.ANY, 'saved_variant_json': mock.ANY},
            {'guid': 'SV0059957_11562437_f019313_1', 'key': None, 'variant_id': '1-1562437-G-CA', 'dataset_type': None, 'genotypes': mock.ANY, 'saved_variant_json': mock.ANY},
        ]
        self.assertListEqual(saved_variants, expected_saved_variants)
        self.assertTrue(all(v['genotypes'] == v['saved_variant_json']['genotypes'] for v in saved_variants[:1] + saved_variants[7:]))

        # Reloading is a no-op
        self.reset_logs()
        call_command('set_saved_variant_key')
        self.assert_json_logs(user=None, expected=[
            ('Updated genotypes for 0 variants', None),
            ('Finding keys for 6 SNV_INDEL (GRCh37) variant ids', None),
            ('Found 0 keys', None),
            ('6 variants have no key, 0 of which have no search data, 6 of which are absent from the hail backend.', None),
            ('Cleared saved json for 0 variants with keys', None),
            ('Done', None),
        ])
        self.assertListEqual(
            list(SavedVariant.objects.order_by('guid').values('guid', 'key', 'variant_id', 'dataset_type', 'genotypes', 'saved_variant_json')),
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
            ('Updated genotypes for 7 variants', None),
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

