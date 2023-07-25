from datetime import datetime
from django.urls.base import reverse
import json
import mock
from requests import HTTPError
import responses

from seqr.views.apis.data_manager_api import elasticsearch_status, upload_qc_pipeline_output, delete_index, \
    update_rna_seq, load_rna_seq_sample_data, load_phenotype_prioritization_data, write_pedigree, validate_callset, \
    get_loaded_projects, load_data
from seqr.views.utils.orm_to_json_utils import _get_json_for_models
from seqr.views.utils.test_utils import AuthenticationTestCase, AirflowTestCase
from seqr.utils.search.elasticsearch.es_utils_tests import urllib3_responses
from seqr.models import Individual, RnaSeqOutlier, RnaSeqTpm, RnaSeqSpliceOutlier, Sample, Project, PhenotypePrioritization
from settings import SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL


PROJECT_GUID = 'R0001_1kg'

ES_CAT_ALLOCATION=[{
    'node': 'node-1',
    'shards': '113',
    'disk.used': '67.2gb',
    'disk.avail': '188.6gb',
    'disk.percent': '26'
},
    {'node': 'UNASSIGNED',
     'shards': '2',
     'disk.used': None,
     'disk.avail': None,
     'disk.percent': None
     }]

ES_CAT_NODES=[{
    'name': 'node-1',
    'heap.percent': '57',
},
    {'name': 'no-disk-node',
     'heap.percent': '83',
     }]

EXPECTED_DISK_ALLOCATION = [{
    'node': 'node-1',
    'shards': '113',
    'diskUsed': '67.2gb',
    'diskAvail': '188.6gb',
    'diskPercent': '26',
    'heapPercent': '57',
},
    {'node': 'UNASSIGNED',
     'shards': '2',
     'diskUsed': None,
     'diskAvail': None,
     'diskPercent': None
     }]

EXPECTED_NODE_STATS = [{'name': 'no-disk-node', 'heapPercent': '83'}]

ES_CAT_INDICES = [{
    "index": "test_index",
    "docs.count": "122674997",
    "store.size": "14.9gb",
    "creation.date.string": "2019-11-04T19:33:47.522Z"
},
    {
        "index": "test_index_alias_1",
        "docs.count": "672312",
        "store.size": "233.4mb",
        "creation.date.string": "2019-10-03T19:53:53.846Z"
    },
    {
        "index": "test_index_alias_2",
        "docs.count": "672312",
        "store.size": "233.4mb",
        "creation.date.string": "2019-10-03T19:53:53.846Z"
    },
    {
        "index": "test_index_no_project",
        "docs.count": "672312",
        "store.size": "233.4mb",
        "creation.date.string": "2019-10-03T19:53:53.846Z"
    },
    {
        "index": "test_index_sv",
        "docs.count": "672312",
        "store.size": "233.4mb",
        "creation.date.string": "2019-10-03T19:53:53.846Z"
    },
    {
        "index": "test_index_sv_wgs",
        "docs.count": "672312",
        "store.size": "233.4mb",
        "creation.date.string": "2019-10-03T19:53:53.846Z"
    },
]

ES_CAT_ALIAS = [
    {
        "alias": "test_index_second",
        "index": "test_index_alias_1"
    },
    {
        "alias": "test_index_second",
        "index": "test_index_alias_2"
    }]

ES_INDEX_MAPPING = {
    "test_index": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "25",
                "genomeVersion": "38",
                "sampleType": "WES",
                "sourceFilePath": "test_index_file_path",
            },
            "_all": {
                "enabled": False
            }
        }
    },
    "test_index_alias_1": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "25",
                "hail_version": "0.2.24",
                "genomeVersion": "37",
                "sampleType": "WGS",
                "sourceFilePath": "test_index_alias_1_path",
            },
            "_all": {
                "enabled": False
            },
        }
    },
    "test_index_alias_2": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "19",
                "genomeVersion": "37",
                "sampleType": "WES",
                "datasetType": "VARIANTS",
                "sourceFilePath": "test_index_alias_2_path"
            },
            "_all": {
                "enabled": False
            },
        }
    },
    "test_index_no_project": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "19",
                "genomeVersion": "37",
                "sampleType": "WGS",
                "datasetType": "VARIANTS",
                "sourceFilePath": "test_index_no_project_path"
            },
            "_all": {
                "enabled": False
            },
        }
    },
    "test_index_sv": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "29",
                "genomeVersion": "38",
                "sampleType": "WES",
                "datasetType": "SV",
                "sourceFilePath": "test_sv_index_path"
            },
        }
    },
    "test_index_sv_wgs": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "29",
                "genomeVersion": "38",
                "sampleType": "WGS",
                "datasetType": "SV",
                "sourceFilePath": "test_sv_wgs_index_path"
            },
        }
    },
}

TEST_INDEX_EXPECTED_DICT = {
    "index": "test_index",
    "sampleType": "WES",
    "genomeVersion": "38",
    "sourceFilePath": "test_index_file_path",
    "docsCount": "122674997",
    "storeSize": "14.9gb",
    "creationDateString": "2019-11-04T19:33:47.522Z",
    "gencodeVersion": "25",
    "projects": [{'projectName': '1kg project n\xe5me with uni\xe7\xf8de', 'projectGuid': 'R0001_1kg'}]
}

TEST_SV_INDEX_EXPECTED_DICT = {
    "index": "test_index_sv",
    "sampleType": "WES",
    "genomeVersion": "38",
    "sourceFilePath": "test_sv_index_path",
    "docsCount": "672312",
    "storeSize": "233.4mb",
    "creationDateString": "2019-10-03T19:53:53.846Z",
    "gencodeVersion": "29",
    "datasetType": "SV",
    "projects": [{'projectName': '1kg project n\xe5me with uni\xe7\xf8de', 'projectGuid': 'R0001_1kg'}]
}

TEST_INDEX_NO_PROJECT_EXPECTED_DICT = {
    "index": "test_index_no_project",
    "sampleType": "WGS",
    "genomeVersion": "37",
    "sourceFilePath": "test_index_no_project_path",
    "docsCount": "672312",
    "storeSize": "233.4mb",
    "creationDateString": "2019-10-03T19:53:53.846Z",
    "datasetType": "VARIANTS",
    "gencodeVersion": "19",
    "projects": []
}

EXPECTED_ERRORS = [
    'test_index_old does not exist and is used by project(s) 1kg project n\xe5me with uni\xe7\xf8de (1 samples)',
    'test_index_mito_wgs does not exist and is used by project(s) 1kg project n\xe5me with uni\xe7\xf8de (1 samples)'
]

SAMPLE_QC_DATA = [
    b'PCT_CONTAMINATION	AL_PCT_CHIMERAS	HS_PCT_TARGET_BASES_20X	seqr_id	data_type	filter_flags	qc_platform	qc_pop	pop_PC1	pop_PC2	pop_PC3	pop_PC4	pop_PC5	pop_PC6	qc_metrics_filters	sample_qc.call_rate	sample_qc.n_called	sample_qc.n_not_called	sample_qc.n_filtered	sample_qc.n_hom_ref	sample_qc.n_het	sample_qc.n_hom_var	sample_qc.n_non_ref	sample_qc.n_singleton	sample_qc.n_snp	sample_qc.n_insertion	sample_qc.n_deletion	sample_qc.n_transition	sample_qc.n_transversion	sample_qc.n_star	sample_qc.r_ti_tv	sample_qc.r_het_hom_var	sample_qc.r_insertion_deletion	sample_qc.f_inbreeding.f_stat	sample_qc.f_inbreeding.n_called	sample_qc.f_inbreeding.expected_homs	sample_qc.f_inbreeding.observed_homs\n',
    b'1.6E-01	5.567E-01	9.2619E+01	MANZ_1169_DNA	WES	[]	WES-010230 Standard Germline Exome	nfe	6.0654E-02	6.0452E-02	-6.2635E-03	-4.3252E-03	-2.1807E-02	-1.948E-02	["n_snp"]	7.1223E-01	14660344	5923237	0	14485322	114532	60490	175022	585	195114	18516	21882	133675	61439	0	2.1757E+00	1.8934E+00	8.4617E-01	5.3509E-01	14660344	1.4414E+07	14545812\n',
    b'NA	NA	NA	NA	WES	[]	Unknown	nfe	4.6581E-02	5.7881E-02	-5.6011E-03	3.5992E-03	-2.9438E-02	-9.6098E-03	["r_insertion_deletion"]	6.2631E-01	12891805	7691776	0	12743977	97831	49997	147828	237	165267	15474	17084	114154	51113	0	2.2334E+00	1.9567E+00	9.0576E-01	5.4467E-01	12891805	1.2677E+07	12793974\n',
    b'NA	NA	NA	NA19675_1	WES	[]	Unknown	amr	2.2367E-02	-1.9772E-02	6.3769E-02	2.5774E-03	-1.6655E-02	2.0457E-03	["r_ti_tv","n_deletion","n_snp","r_insertion_deletion","n_insertion"]	1.9959E-01	4108373	16475208	0	3998257	67927	42189	110116	18572	127706	13701	10898	82568	45138	0	1.8292E+00	1.6101E+00	1.2572E+00	5.3586E-02	4108373	4.0366E+06	4040446\n',
    b'5.6E-01	3.273E-01	8.1446E+01	NA19678	WES	["coverage"]	Standard Exome Sequencing v4	sas	2.4039E-02	-6.9517E-02	-4.1485E-02	1.421E-01	7.5583E-02	-2.0986E-02	["n_insertion"]	4.6084E-01	9485820	11097761	0	9379951	59871	45998	105869	736	136529	6857	8481	95247	41282	0	2.3072E+00	1.3016E+00	8.0851E-01	5.2126E-01	9485820	9.3608E+06	9425949\n',
    b'5.4E-01	5.0841E+00	8.7288E+01	HG00732	WES	["chimera"]	Standard Germline Exome v5	nfe	5.2785E-02	5.547E-02	-5.82E-03	2.7961E-02	-4.2259E-02	3.0271E-02	["n_insertion","r_insertion_deletion"]	6.8762E-01	14153622	6429959	0	13964844	123884	64894	188778	1719	202194	29507	21971	138470	63724	0	2.173E+00	1.909E+00	1.343E+00	4.924E-01	14153622	1.391E+07	14029738\n',
    b'2.79E+00	1.8996E+01	7.352E+01	HG00733	WES	["contamination","not_real_flag"]	Standard Germline Exome v5	oth	-1.5417E-01	2.8868E-02	-1.3819E-02	4.1915E-02	-4.0001E-02	7.6392E-02	["n_insertion","r_insertion_deletion", "not_real_filter"]	6.1147E-01	12586314	7997267	0	12383958	140784	61572	202356	8751	204812	38051	21065	140282	64530	0	2.1739E+00	2.2865E+00	1.8064E+00	3.6592E-01	12586314	1.2364E+07	12445530\n',
]

SAMPLE_QC_DATA_NO_DATA_TYPE = [
    b'seqr_id	data_type	filter_flags	qc_platform	qc_pop	qc_metrics_filters\n',
    b'03133B_2	n/a	[]	Standard Germline Exome v5	nfe	[]\n',
]

SAMPLE_QC_DATA_MORE_DATA_TYPE = [
    b'seqr_id	data_type	filter_flags	qc_platform	qc_pop	qc_metrics_filters\n',
    b'03133B_2	WES	[]	Standard Germline Exome v5	nfe	[]\n',
    b'03133B_3	WGS	[]	Standard Germline Exome v5	nfe	[]\n',
]


SAMPLE_QC_DATA_UNEXPECTED_DATA_TYPE = [
    b'seqr_id	data_type	filter_flags	qc_platform	qc_pop	qc_metrics_filters\n',
    b'03133B_2	UNKNOWN	[]	Standard Germline Exome v5	nfe	[]\n',
]

SAMPLE_SV_WES_QC_DATA = [
    b'sample	lt100_raw_calls	lt10_highQS_rare_calls\n',
    b'RP-123_MANZ_1169_DNA_v1_Exome_GCP	FALSE	TRUE\n',
    b'RP-123_NA_v1_Exome_GCP	TRUE	FALSE\n',
    b'RP-123_NA19675_1_v1_Exome_GCP	TRUE	TRUE\n',
    b'RP-123_NA19678_v1_Exome_GCP	TRUE	FALSE\n',
    b'RP-123_HG00732_v1_Exome_GCP	FALSE	TRUE\n',
    b'RP-123_HG00733_v1_Exome_GCP	FALSE	FALSE\n',
]

SAMPLE_SV_WGS_QC_DATA = [
    b'sample	expected_num_calls\n',
    b'NA21234	FALSE\n',
    b'NA19678	FALSE\n',
]

RNA_SAMPLE_GUID = 'S000150_na19675_d2'
RNA_TPM_SAMPLE_GUID = 'S000152_na19675_d2'
RNA_SPLICE_SAMPLE_GUID = 'S000151_na19675_1'
PLACEHOLDER_GUID = 'S0000100'
RNA_FILE_ID = 'gs://rna_data/new_muscle_samples.tsv.gz'
SAMPLE_GENE_OUTLIER_DATA = {
    'ENSG00000240361': {'gene_id': 'ENSG00000240361', 'p_value': '0.01', 'p_adjust': '0.13', 'z_score': '-3.1'},
    'ENSG00000233750': {'gene_id': 'ENSG00000233750', 'p_value': '0.064', 'p_adjust': '0.0000057', 'z_score': '7.8'},
}
SAMPLE_GENE_TPM_DATA = {
    'ENSG00000240361': {'gene_id': 'ENSG00000240361', 'tpm': '7.8'},
    'ENSG00000233750': {'gene_id': 'ENSG00000233750', 'tpm': '0.0'},
}
SAMPLE_GENE_SPLICE_DATA = {
    'ENSG00000233750-2-167254166-167258349-*-psi3': {
        'chrom': '2', 'start': 167254166, 'end': 167258349, 'strand': '*', 'type': 'psi3',
        'p_value': 1.56e-25, 'z_score': -4.9, 'delta_psi': -0.46, 'read_count': 166, 'gene_id': 'ENSG00000233750',
        'rare_disease_samples_with_junction': 1, 'rare_disease_samples_total': 20, 'rank': 1,
    },
    'ENSG00000240361-7-132885746-132975168-*-psi5': {
        'chrom': '7', 'start': 132885746, 'end': 132975168, 'strand': '*', 'type': 'psi5',
        'p_value': 1.08e-56, 'z_score': -6.53, 'delta_psi': -0.85, 'read_count': 231, 'gene_id': 'ENSG00000240361',
        'rare_disease_samples_with_junction': 1, 'rare_disease_samples_total': 20, 'rank': 0,
    },
}
SAMPLE_GENE_SPLICE_DATA2 = {
    'ENSG00000233750-2-167258096-167258349-*-psi3': {
        'chrom': '2', 'start': 167258096, 'end': 167258349, 'strand': '*', 'type': 'psi3',
        'p_value': 1.56e-25, 'z_score': 6.33, 'delta_psi': 0.45, 'read_count': 143, 'gene_id': 'ENSG00000233750',
        'rare_disease_samples_with_junction': 1, 'rare_disease_samples_total': 20, 'rank': 0,
    }
}
RNA_OUTLIER_SAMPLE_DATA = [
    f'{RNA_SAMPLE_GUID}\t\t{json.dumps(SAMPLE_GENE_OUTLIER_DATA)}\n',
    f"{PLACEHOLDER_GUID}\t\t{json.dumps({'ENSG00000240361': {'gene_id': 'ENSG00000240361', 'p_value': '0.04', 'p_adjust': '0.112', 'z_score': '1.9'}})}\n",
]
RNA_TPM_SAMPLE_DATA = [
    f'{RNA_TPM_SAMPLE_GUID}\t\t{json.dumps(SAMPLE_GENE_TPM_DATA)}\n',
    f"{PLACEHOLDER_GUID}\t\t{json.dumps({'ENSG00000240361': {'gene_id': 'ENSG00000240361', 'tpm': '0.112'}})}\n",
]
RNA_SPLICE_SAMPLE_DATA = [
    f'{RNA_SPLICE_SAMPLE_GUID}\t\t{json.dumps(SAMPLE_GENE_SPLICE_DATA)}\n',
    f'{PLACEHOLDER_GUID}\t\t{json.dumps(SAMPLE_GENE_SPLICE_DATA2)}\n',
]
RNA_FILENAME_TEMPLATE = 'rna_sample_data__{}__2020-04-15T00:00:00.json.gz'

PHENOTYPE_PRIORITIZATION_HEADER = [['tool', 'project', 'sampleId', 'rank', 'geneId', 'diseaseId', 'diseaseName',
                                   'scoreName1', 'score1', 'scoreName2', 'score2', 'scoreName3', 'score3']]
PHENOTYPE_PRIORITIZATION_MISS_HEADER = [['tool', 'sampleId', 'rank', 'geneId', 'diseaseName', 'scoreName1', 'score1',
                                        'scoreName2', 'score2', 'scoreName3', 'score3']]
LIRICAL_NO_PROJECT_DATA = [['lirical']]
LIRICAL_PROJECT_NOT_EXIST_DATA = [
    ['lirical', 'CMG_Beggs_WGS', 'NA19678', '1', 'ENSG00000105357', 'OMIM:618460', 'Khan-Khan-Katsanis syndrome',
     'post_test_probability', '0', 'compositeLR', '0.066'],
]
LIRICAL_NO_EXIST_INDV_DATA = [
    ['lirical', '1kg project nåme with uniçøde', 'NA19678x', '1', 'ENSG00000105357', 'OMIM:618460',
     'Khan-Khan-Katsanis syndrome', 'post_test_probability', '0', 'compositeLR', '0.066'],
    ['lirical', '1kg project nåme with uniçøde', 'NA19679x', '1', 'ENSG00000105357', 'OMIM:618460',
     'Khan-Khan-Katsanis syndrome', 'post_test_probability', '0', 'compositeLR', '0.066'],
]
LIRICAL_DATA = [
    ['lirical', '1kg project nåme with uniçøde', 'NA19678', '1', 'ENSG00000105357', 'OMIM:618460',
     'Khan-Khan-Katsanis syndrome', 'post_test_probability', '0', 'compositeLR', '0.066'],
    ['lirical', 'Test Reprocessed Project', 'NA20885', '2', 'ENSG00000105357', 'OMIM:219800',
     '"Cystinosis, nephropathic"', 'post_test_probability', '0', 'compositeLR', '', '', ''],
]
EXOMISER_DATA = [
    ['exomiser', 'CMG_Beggs_WGS', 'BEG_1230-1_01', '1', 'ENSG00000105357', 'ORPHA:2131',
     'Alternating hemiplegia of childhood', 'exomiser_score', '0.977923765', 'phenotype_score', '0.603998205',
     'variant_score', '1'],
    ['exomiser', 'CMG_Beggs_WGS', 'BEG_1230-1_01', '3', 'ENSG00000105357', 'ORPHA:71517',
     'Rapid-onset dystonia-parkinsonism', 'exomiser_score', '0.977923765', 'phenotype_score', '0.551578222',
     'variant_score', '1']
]
UPDATE_LIRICAL_DATA = [
    ['lirical', '1kg project nåme with uniçøde', 'NA19678', '3', 'ENSG00000105357', 'OMIM:618460',
     'Khan-Khan-Katsanis syndrome', 'post_test_probability', '0', 'compositeLR', '0.066'],
    ['lirical', '1kg project nåme with uniçøde', 'NA19678', '4', 'ENSG00000105357', 'OMIM:219800',
     '"Cystinosis, nephropathic"', 'post_test_probability', '0', 'compositeLR', '0.003', '', ''],
]

EXPECTED_LIRICAL_DATA = [
    {'diseaseId': 'OMIM:219801', 'geneId': 'ENSG00000268904', 'diseaseName': 'Cystinosis, no syndrome',
     'scores': {'compositeLR': 0.003, 'post_test_probability': 0.1},
     'tool': 'lirical', 'rank': 11, 'individualGuid': 'I000001_na19675'},  # record from the fixture
    {'diseaseId': 'OMIM:618460', 'geneId': 'ENSG00000105357', 'diseaseName': 'Khan-Khan-Katsanis syndrome',
     'scores': {'compositeLR': 0.066, 'postTestProbability': 0.0},
     'tool': 'lirical', 'rank': 1, 'individualGuid': 'I000002_na19678'},
    {'diseaseId': 'OMIM:219800', 'geneId': 'ENSG00000105357', 'diseaseName': 'Cystinosis, nephropathic',
     'scores': {'postTestProbability': 0.0},
     'tool': 'lirical', 'rank': 2, 'individualGuid': 'I000015_na20885'}
]
EXPECTED_UPDATED_LIRICAL_DATA = [
    {'diseaseId': 'OMIM:219801', 'geneId': 'ENSG00000268904', 'diseaseName': 'Cystinosis, no syndrome',
     'scores': {'compositeLR': 0.003, 'post_test_probability': 0.1},
     'tool': 'lirical', 'rank': 11, 'individualGuid': 'I000001_na19675'},  # record from the fixture
    {'diseaseId': 'OMIM:219800', 'geneId': 'ENSG00000105357', 'diseaseName': 'Cystinosis, nephropathic',
     'scores': {'postTestProbability': 0.0},
     'tool': 'lirical', 'rank': 2, 'individualGuid': 'I000015_na20885'},
    {'diseaseId': 'OMIM:618460', 'geneId': 'ENSG00000105357', 'diseaseName': 'Khan-Khan-Katsanis syndrome',
     'scores': {'compositeLR': 0.066, 'postTestProbability': 0.0},
     'tool': 'lirical', 'rank': 3, 'individualGuid': 'I000002_na19678'},
    {'diseaseId': 'OMIM:219800', 'geneId': 'ENSG00000105357', 'diseaseName': 'Cystinosis, nephropathic',
     'scores': {'compositeLR': 0.003, 'postTestProbability': 0.0},
     'tool': 'lirical', 'rank': 4, 'individualGuid': 'I000002_na19678'},
]


class DataManagerAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'reference_data']

    @mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', 'testhost')
    @urllib3_responses.activate
    def test_elasticsearch_status(self):
        url = reverse(elasticsearch_status)
        self.check_data_manager_login(url)

        urllib3_responses.add_json(
            '/_cat/allocation?format=json&h=node,shards,disk.avail,disk.used,disk.percent', ES_CAT_ALLOCATION)
        urllib3_responses.add_json(
            '/_cat/nodes?format=json&h=name,heap.percent', ES_CAT_NODES)
        urllib3_responses.add_json(
           '/_cat/indices?format=json&h=index,docs.count,store.size,creation.date.string', ES_CAT_INDICES)
        urllib3_responses.add_json('/_cat/aliases?format=json&h=alias,index', ES_CAT_ALIAS)
        urllib3_responses.add_json('/_all/_mapping', ES_INDEX_MAPPING)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'indices', 'errors', 'diskStats', 'nodeStats'})

        self.assertEqual(len(response_json['indices']), 6)
        self.assertDictEqual(response_json['indices'][0], TEST_INDEX_EXPECTED_DICT)
        self.assertDictEqual(response_json['indices'][3], TEST_INDEX_NO_PROJECT_EXPECTED_DICT)
        self.assertDictEqual(response_json['indices'][4], TEST_SV_INDEX_EXPECTED_DICT)

        self.assertListEqual(response_json['errors'], EXPECTED_ERRORS)

        self.assertListEqual(response_json['diskStats'], EXPECTED_DISK_ALLOCATION)
        self.assertListEqual(response_json['nodeStats'], EXPECTED_NODE_STATS)

        with mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', ''):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error'], 'Elasticsearch is disabled')

    @mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', 'testhost')
    @urllib3_responses.activate
    def test_delete_index(self):
        url = reverse(delete_index)
        self.check_data_manager_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({'index': 'test_index'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'], '"test_index" is still used by: 1kg project n\xe5me with uni\xe7\xf8de')
        self.assertEqual(len(urllib3_responses.calls), 0)

        urllib3_responses.add_json(
            '/_cat/indices?format=json&h=index,docs.count,store.size,creation.date.string', ES_CAT_INDICES)
        urllib3_responses.add_json('/_cat/aliases?format=json&h=alias,index', ES_CAT_ALIAS)
        urllib3_responses.add_json('/_all/_mapping', ES_INDEX_MAPPING)
        urllib3_responses.add(urllib3_responses.DELETE, '/unused_index')

        response = self.client.post(url, content_type='application/json', data=json.dumps({'index': 'unused_index'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'indices'})
        self.assertEqual(len(response_json['indices']), 6)
        self.assertDictEqual(response_json['indices'][0], TEST_INDEX_EXPECTED_DICT)
        self.assertDictEqual(response_json['indices'][3], TEST_INDEX_NO_PROJECT_EXPECTED_DICT)
        self.assertDictEqual(response_json['indices'][4], TEST_SV_INDEX_EXPECTED_DICT)

        self.assertEqual(urllib3_responses.calls[0].request.method, 'DELETE')

        with mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', ''):
            response = self.client.post(url, content_type='application/json', data=json.dumps({'index': 'unused_index'}))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error'], 'Deleting indices is disabled for the hail backend')

    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_upload_qc_pipeline_output(self, mock_subprocess):
        url = reverse(upload_qc_pipeline_output,)
        self.check_data_manager_login(url)

        request_data =json.dumps({
            'file': ' gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/final_output/seqr_sample_qc.tsv'
        })

        # Test missing file
        self.reset_logs()
        mock_does_file_exist = mock.MagicMock()
        mock_subprocess.side_effect = [mock_does_file_exist]
        mock_does_file_exist.wait.return_value = 1
        mock_does_file_exist.stdout = [b'BucketNotFoundException: 404 gs://seqr-datsets bucket does not exist.']
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(
            response.json()['errors'],
            ['File not found: gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/final_output/seqr_sample_qc.tsv'])
        self.assert_json_logs(self.data_manager_user, [
            ('==> gsutil ls gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/final_output/seqr_sample_qc.tsv', None),
            ('BucketNotFoundException: 404 gs://seqr-datsets bucket does not exist.', None),
        ])

        # Test missing columns
        mock_does_file_exist.wait.return_value = 0
        mock_file_iter = mock.MagicMock()
        mock_file_iter.stdout = [b'', b'']
        mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.reason_phrase,
            'The following required columns are missing: seqr_id, data_type, filter_flags, qc_metrics_filters, qc_pop')

        # Test no data type error
        mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
        mock_file_iter.stdout = SAMPLE_QC_DATA_NO_DATA_TYPE
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'No data type detected')

        # Test multiple data types error
        mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
        mock_file_iter.stdout = SAMPLE_QC_DATA_MORE_DATA_TYPE
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Multiple data types detected: wes ,wgs')

        # Test unexpected data type error
        mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
        mock_file_iter.stdout = SAMPLE_QC_DATA_UNEXPECTED_DATA_TYPE
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Unexpected data type detected: "unknown" (should be "exome" or "genome")')

        # Test normal functions
        mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
        mock_file_iter.stdout = SAMPLE_QC_DATA
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'info', 'errors', 'warnings'})
        self.assertListEqual(response_json['info'], [
            'Parsed 6 exome samples',
            'Found and updated matching seqr individuals for 4 samples'
        ])
        self.assertListEqual(response_json['warnings'], [
            'The following 1 samples were added to multiple individuals: NA19678 (2)',
            'The following 2 samples were skipped: MANZ_1169_DNA, NA',
            'The following filter flags have no known corresponding value and were not saved: not_real_flag',
            'The following population platform filters have no known corresponding value and were not saved: not_real_filter'
        ])

        indiv = Individual.objects.get(id = 1)
        self.assertIsNone(indiv.filter_flags)
        self.assertDictEqual(indiv.pop_platform_filters, {'n_deletion': '10898', 'n_snp': '127706', 'r_insertion_deletion': '1.2572E+00', 'r_ti_tv': '1.8292E+00', 'n_insertion': '13701'})
        self.assertEqual(indiv.population, 'AMR')

        indiv = Individual.objects.get(id = 2)
        self.assertDictEqual(indiv.filter_flags, {'coverage_exome': '8.1446E+01'})
        self.assertDictEqual(indiv.pop_platform_filters, {'n_insertion': '6857'})
        self.assertEqual(indiv.population, 'SAS')

        indiv = Individual.objects.get(id=12)
        self.assertDictEqual(indiv.filter_flags, {'coverage_exome': '8.1446E+01'})
        self.assertDictEqual(indiv.pop_platform_filters, {'n_insertion': '6857'})
        self.assertEqual(indiv.population, 'SAS')

        indiv = Individual.objects.get(id = 5)
        self.assertDictEqual(indiv.filter_flags, {'chimera': '5.0841E+00'})
        self.assertDictEqual(indiv.pop_platform_filters, {'n_insertion': '29507', 'r_insertion_deletion': '1.343E+00'})
        self.assertEqual(indiv.population, 'NFE')

        indiv = Individual.objects.get(id = 6)
        self.assertDictEqual(indiv.filter_flags, {'contamination': '2.79E+00'})
        self.assertDictEqual(indiv.pop_platform_filters, {'n_insertion': '38051', 'r_insertion_deletion': '1.8064E+00'})
        self.assertEqual(indiv.population, 'OTH')

    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_upload_sv_qc(self, mock_subprocess):
        url = reverse(upload_qc_pipeline_output, )
        self.check_data_manager_login(url)

        request_data = json.dumps({
            'file': 'gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/sv/sv_sample_metadata.tsv'
        })

        mock_does_file_exist = mock.MagicMock()
        mock_does_file_exist.wait.return_value = 0
        mock_file_iter = mock.MagicMock()
        mock_file_iter.stdout = SAMPLE_SV_WES_QC_DATA
        mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'info', 'errors', 'warnings'})
        self.assertListEqual(response_json['info'], [
            'Parsed 6 SV samples',
            'Found and updated matching seqr individuals for 4 samples'
        ])
        self.assertListEqual(response_json['warnings'], ['The following 2 samples were skipped: MANZ_1169_DNA, NA'])

        self.assertIsNone(Individual.objects.get(individual_id='NA19675_1').sv_flags)
        self.assertListEqual(Individual.objects.get(individual_id='NA19678').sv_flags, ['high_QS_rare_calls:_>10'])
        self.assertListEqual(Individual.objects.get(individual_id='HG00732').sv_flags, ['raw_calls:_>100'])
        self.assertListEqual(
            Individual.objects.get(individual_id='HG00733').sv_flags,
            ['high_QS_rare_calls:_>10', 'raw_calls:_>100'])

        # Test genome data
        mock_file_iter.stdout = SAMPLE_SV_WGS_QC_DATA
        mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'info', 'errors', 'warnings'})
        self.assertListEqual(response_json['info'], [
            'Parsed 2 SV samples',
            'Found and updated matching seqr individuals for 1 samples'
        ])
        self.assertListEqual(response_json['warnings'], ['The following 1 samples were skipped: NA19678'])
        self.assertListEqual(Individual.objects.get(individual_id='NA21234').sv_flags, ['outlier_num._calls'])
        # Should not overwrite existing QC flags
        self.assertListEqual(Individual.objects.get(individual_id='NA19678').sv_flags, ['high_QS_rare_calls:_>10'])

    @mock.patch('seqr.views.apis.data_manager_api.KIBANA_ELASTICSEARCH_PASSWORD', 'abc123')
    @responses.activate
    def test_kibana_proxy(self):
        url = '/api/kibana/random/path'
        self.check_data_manager_login(url)

        response_args = {
            'stream': True,
            'body': 'Test response',
            'content_type': 'text/custom',
            'headers': {'x-test-header': 'test', 'keep-alive': 'true'},
        }
        proxy_url = 'http://localhost:5601{}'.format(url)
        responses.add(responses.GET, proxy_url, status=200, **response_args)
        responses.add(responses.POST, proxy_url, status=201, **response_args)
        responses.add(responses.GET, '{}/bad_response'.format(proxy_url), body=HTTPError())

        response = self.client.get(url, HTTP_TEST_HEADER='some/value')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'Test response')
        self.assertEqual(response.get('content-type'), 'text/custom')
        self.assertEqual(response.get('x-test-header'), 'test')
        self.assertIsNone(response.get('keep-alive'))

        data = json.dumps([{'content': 'Test Body'}])
        response = self.client.post(url, content_type='application/json', data=data)
        self.assertEqual(response.status_code, 201)

        self.assertEqual(len(responses.calls), 2)

        get_request = responses.calls[0].request
        self.assertEqual(get_request.headers['Host'], 'localhost:5601')
        self.assertEqual(get_request.headers['Authorization'], 'Basic a2liYW5hOmFiYzEyMw==')
        self.assertEqual(get_request.headers['Test-Header'], 'some/value')

        post_request = responses.calls[1].request
        self.assertEqual(post_request.headers['Host'], 'localhost:5601')
        self.assertEqual(get_request.headers['Authorization'], 'Basic a2liYW5hOmFiYzEyMw==')
        self.assertEqual(post_request.headers['Content-Type'], 'application/json')
        self.assertEqual(post_request.headers['Content-Length'], '26')
        self.assertEqual(post_request.body, data.encode('utf-8'))

        # Test with error response
        response = self.client.get('{}/bad_response'.format(url))
        self.assertEqual(response.status_code, 500)

        # Test with connection error
        response = self.client.get('{}/bad_path'.format(url))
        self.assertContains(response, 'Error: Unable to connect to Kibana', status_code=400)

    RNA_DATA_TYPE_PARAMS = {
        'outlier': {
            'model_cls': RnaSeqOutlier,
            'message_data_type': 'Expression Outlier',
            'header': ['sampleID', 'project', 'geneID', 'detail', 'pValue', 'padjust', 'zScore'],
            'optional_headers': ['detail'],
            'loaded_data_row': ['NA19675_D2', '1kg project nåme with uniçøde', 'ENSG00000240361', 'detail1', 0.01, 0.001, -3.1],
            'no_existing_data': ['NA19678', '1kg project nåme with uniçøde', 'ENSG00000233750', 'detail1', 0.064, '0.0000057', 7.8],
            'duplicated_indiv_id_data': [
                ['NA20870', 'Test Reprocessed Project', 'ENSG00000233750', 'detail1', 0.064, '0.0000057', 7.8],
                ['NA20870', '1kg project nåme with uniçøde', 'ENSG00000240361', 'detail2', 0.01, 0.13, -3.1],
            ],
            'write_data': {
                'NA20870\t\t{"ENSG00000233750": {"gene_id": "ENSG00000233750", "p_value": "0.064", "p_adjust": "0.0000057", "z_score": "7.8"}}\n',
                'NA20870\t\t{"ENSG00000240361": {"gene_id": "ENSG00000240361", "p_value": "0.01", "p_adjust": "0.13", "z_score": "-3.1"}}\n'
            },
            'new_data': [
                ['NA19675_D2', '1kg project nåme with uniçøde', 'ENSG00000240361', 'detail1', 0.01, 0.13, -3.1],
                ['NA19675_D2', '1kg project nåme with uniçøde', 'ENSG00000240361', 'detail2', 0.01, 0.13, -3.1],
                ['NA19675_D2', '1kg project nåme with uniçøde', 'ENSG00000233750', 'detail1', 0.064, '0.0000057', 7.8],
                ['NA19675_D3', 'Test Reprocessed Project', 'ENSG00000233750', 'detail1', 0.064, '0.0000057', 7.8],
                ['NA20888', 'Test Reprocessed Project', 'ENSG00000240361', '', 0.04, 0.112, 1.9],
            ],
            'skipped_samples': 'NA19675_D3',
            'num_parsed_samples': 3,
            'initial_model_count': 3,
            'parsed_file_data': RNA_OUTLIER_SAMPLE_DATA,
            'get_models_json': lambda models: list(models.values_list('gene_id', 'p_adjust', 'p_value', 'z_score')),
            'expected_models_json': [
                ('ENSG00000240361', 0.13, 0.01, -3.1), ('ENSG00000233750', 0.0000057, 0.064, 7.8),
            ],
            'sample_guid': RNA_SAMPLE_GUID,
        },
        'tpm': {
            'model_cls': RnaSeqTpm,
            'message_data_type': 'Expression',
            'header': ['sample_id', 'project', 'gene_id', 'individual_id', 'tissue', 'TPM'],
            'optional_headers': ['individual_id'],
            'loaded_data_row': ['NA19675_D2', '1kg project nåme with uniçøde', 'ENSG00000135953', 'NA19675_D3', 'muscle', 1.34],
            'no_existing_data': ['NA19678', '1kg project nåme with uniçøde', 'ENSG00000233750', 'NA19678', 'muscle', 0.064],
            'duplicated_indiv_id_data': [
                ['NA20870', 'Test Reprocessed Project', 'ENSG00000240361', 'NA20870', 'muscle', 7.8],
                ['NA20870', '1kg project nåme with uniçøde', 'ENSG00000233750', 'NA20870', 'fibroblasts', 0.0],
            ],
            'write_data': {'NA20870\t\t{"ENSG00000240361": {"gene_id": "ENSG00000240361", "tpm": "7.8"}}\n',
                           'NA20870\t\t{"ENSG00000233750": {"gene_id": "ENSG00000233750", "tpm": "0.0"}}\n'},
            'new_data': [
                # existing sample NA19675_D2
                ['NA19675_D2', '1kg project nåme with uniçøde', 'ENSG00000240361', 'NA19675_D2', 'muscle', 7.8],
                ['NA19675_D2', '1kg project nåme with uniçøde', 'ENSG00000233750', 'NA19675_D2', 'muscle', 0.0],
                # no matched individual NA19675_D3
                ['NA19675_D3', '1kg project nåme with uniçøde', 'ENSG00000233750', 'NA19675_D3', 'fibroblasts', 0.064],
                # skip GTEX samples
                ['GTEX_001', '1kg project nåme with uniçøde', 'ENSG00000233750', 'NA19675_D3', 'whole_blood', 1.95],
                # a different project sample NA20888
                ['NA20888', 'Test Reprocessed Project', 'ENSG00000240361', 'NA20888', 'muscle', 0.112],
                # a project mismatched sample NA20878
                ['NA20878', 'Test Reprocessed Project', 'ENSG00000233750', 'NA20878', 'fibroblasts', 0.064],
                # conflict tissue types samples
                ['NA19678', '1kg project nåme with uniçøde', 'ENSG00000233750', 'NA19678', 'muscle', 1.34],
                ['NA19678', '1kg project nåme with uniçøde', 'ENSG00000135954', 'NA19678', 'fibroblasts', 0.05],
            ],
            'skipped_samples': 'NA19675_D3, NA20878',
            'sample_tissue_type': 'M',
            'num_parsed_samples': 4,
            'initial_model_count': 4,
            'deleted_count': 1,
            'extra_warnings': [
                'Skipped data loading for the following 1 sample(s) due to mismatched tissue type: NA19678 (fibroblasts, muscle)',
            ],
            'parsed_file_data': RNA_TPM_SAMPLE_DATA,
            'get_models_json': lambda models: list(models.values_list('gene_id', 'tpm')),
            'expected_models_json': [('ENSG00000240361', 7.8), ('ENSG00000233750', 0.0)],
            'sample_guid': RNA_TPM_SAMPLE_GUID,
        },
        'splice_outlier': {
            'model_cls': RnaSeqSpliceOutlier,
            'message_data_type': 'Splice Outlier',
            'header': ['individualId', 'project', 'geneId', 'chrom', 'start', 'end', 'strand', 'geneName', 'type', 'pValue', 'zScore',
                       'deltaPsi', 'readCount', 'tissue', 'dotSize', 'rareDiseaseSamplesWithJunction',
                       'rareDiseaseSamplesTotal'],
            'optional_headers': ['geneName', 'dotSize'],
            'loaded_data_row': ['NA19675_1', '1kg project nåme with uniçøde', 'ENSG00000240361', 'chr7', 132885746, 132886973, '*', 'CHCHD3',
                                'psi5', 1.08E-56, 12.34, 0.85, 1297, 'fibroblasts', 0.53953638, 1, 20],
            'no_existing_data': ['NA19678', '1kg project nåme with uniçøde', 'ENSG00000240361', 'chr7', 132885746, 132886973, '*', 'CHCHD3',
                                'psi5', 1.08E-56, 12.34, 0.85, 1297, 'fibroblasts', 0.53953638, 1, 20],
            'duplicated_indiv_id_data': [
                ['NA20870', 'Test Reprocessed Project', 'ENSG00000233750', 'chr2', 167258096, 167258349, '*', 'XIRP2',
                 'psi3', 1.56E-25, 6.33, 0.45, 143, 'fibroblasts', 0.03454739, 1, 20],
                ['NA20870', '1kg project nåme with uniçøde', 'ENSG00000135953', 'chr2', 167258096, 167258349, '*', 'XIRP2',
                 'psi3', 1.56E-25, 6.33, 0.45, 143, 'muscle', 0.03454739, 1, 20],
            ],
            'write_data': {'NA20870\t\t{"ENSG00000233750-2-167258096-167258349-*-psi3": {"chrom": "2", "start": 167258096,'
                           ' "end": 167258349, "strand": "*", "type": "psi3", "p_value": 1.56e-25, "z_score": 6.33,'
                           ' "delta_psi": 0.45, "read_count": 143, "gene_id": "ENSG00000233750",'
                           ' "rare_disease_samples_with_junction": 1, "rare_disease_samples_total": 20, "rank": 0}}\n',
                           'NA20870\t\t{"ENSG00000135953-2-167258096-167258349-*-psi3": {"chrom": "2", "start": 167258096,'
                           ' "end": 167258349, "strand": "*", "type": "psi3", "p_value": 1.56e-25, "z_score": 6.33,'
                           ' "delta_psi": 0.45, "read_count": 143, "gene_id": "ENSG00000135953",'
                           ' "rare_disease_samples_with_junction": 1, "rare_disease_samples_total": 20, "rank": 0}}\n',
            },
            'new_data': [
                # existing sample NA19675_1
                ['NA19675_1', '1kg project nåme with uniçøde', 'ENSG00000233750', 'chr2', 167254166, 167258349, '*', 'XIRP2', 'psi3',
                 1.56E-25, -4.9, -0.46, 166, 'fibroblasts', 0.03850364, 1, 20],
                ['NA19675_1', '1kg project nåme with uniçøde', 'ENSG00000240361', 'chr7', 132885746, 132975168, '*', 'CHCHD3', 'psi5',
                 1.08E-56, -6.53, -0.85, 231, 'fibroblasts', 0.53953638, 1, 20],
                # no matched individual NA19675_D3
                ['NA19675_D3', '1kg project nåme with uniçøde', 'ENSG00000233750', 'chr2', 167258096, 167258349, '*', 'XIRP2',
                 'psi3', 1.56E-25, 6.33, 0.45, 143, 'muscle', 0.03454739, 1, 20],
                # a new sample NA20888
                ['NA20888', 'Test Reprocessed Project', 'ENSG00000233750', 'chr2', 167258096, 167258349, '*', 'XIRP2',
                 'psi3', 1.56E-25, 6.33, 0.45, 143, 'fibroblasts', 0.03454739, 1, 20],
                # a project mismatched sample NA20878
                ['NA20878', 'Test Reprocessed Project', 'ENSG00000233750', 'chr2', 167258096, 167258349, '*', 'XIRP2', 'psi3',
                 1.56E-25, 6.33, 0.45, 143, 'fibroblasts', 0.03454739, 1, 20],
            ],
            'skipped_samples': 'NA19675_D3, NA20878',
            'sample_tissue_type': 'F',
            'num_parsed_samples': 4,
            'initial_model_count': 7,
            'deleted_count': 4,
            'parsed_file_data': RNA_SPLICE_SAMPLE_DATA,
            'get_models_json': lambda models: list(
                models.values_list('gene_id', 'chrom', 'start', 'end', 'strand', 'type', 'p_value', 'z_score', 'delta_psi',
                                   'read_count', 'rare_disease_samples_with_junction', 'rare_disease_samples_total')),
            'expected_models_json': [
                ('ENSG00000233750', '2', 167254166, 167258349, '*', 'psi3', 1.56e-25, -4.9, -0.46, 166, 1, 20),
                ('ENSG00000240361', '7', 132885746, 132975168, '*', 'psi5', 1.08e-56, -6.53, -0.85, 231, 1, 20)
            ],
            'sample_guid': RNA_SPLICE_SAMPLE_GUID,
            'row_id': 'ENSG00000240361-7-132885746-132886973-*-psi5',
        },
    }

    def _has_expected_file_loading_logs(self, file, info=None, warnings=None, additional_logs=None, additional_logs_offset=None):
        expected_logs = [
            (f'==> gsutil ls {file}', None),
            (f'==> gsutil cat {file} | gunzip -c -q - ', None),
        ] + [(info_log, None) for info_log in info or []] + [
            (warn_log, {'severity': 'WARNING'}) for warn_log in warnings or []
        ]
        if additional_logs:
            if additional_logs_offset:
                for log in reversed(additional_logs):
                    expected_logs.insert(additional_logs_offset, log)
            else:
                expected_logs += additional_logs

        self.assert_json_logs(self.data_manager_user, expected_logs)

    def _check_rna_sample_model(self, individual_id, data_source, tissue_type):
        rna_samples = Sample.objects.filter(individual_id=individual_id, sample_type='RNA', tissue_type=tissue_type)
        self.assertEqual(len(rna_samples), 1)
        sample = rna_samples.first()
        self.assertTrue(sample.is_active)
        self.assertIsNone(sample.elasticsearch_index)
        self.assertEqual(sample.sample_type, 'RNA')
        self.assertEqual(sample.tissue_type, tissue_type)
        self.assertEqual(sample.data_source, data_source)
        return sample.guid

    @mock.patch('seqr.views.utils.dataset_utils.BASE_URL', 'https://test-seqr.org/')
    @mock.patch('seqr.views.utils.dataset_utils.SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL', 'seqr-data-loading')
    @mock.patch('seqr.views.utils.dataset_utils.safe_post_to_slack')
    @mock.patch('seqr.views.apis.data_manager_api.datetime')
    @mock.patch('seqr.views.apis.data_manager_api.os')
    @mock.patch('seqr.views.apis.data_manager_api.load_uploaded_file')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    @mock.patch('seqr.views.apis.data_manager_api.gzip.open')
    def test_update_rna_seq(self, mock_open, mock_subprocess, mock_load_uploaded_file,
                            mock_os, mock_datetime, mock_send_slack):
        url = reverse(update_rna_seq)
        self.check_data_manager_login(url)

        for data_type, params in self.RNA_DATA_TYPE_PARAMS.items():
            with self.subTest(data_type):
                model_cls = params['model_cls']
                header = params['header']
                loaded_data_row = params['loaded_data_row']

                # Test errors
                body = {'dataType': data_type, 'file': 'gs://rna_data/muscle_samples.tsv.gz'}
                mock_datetime.now.return_value = datetime(2020, 4, 15)
                mock_os.path.join.side_effect = lambda *args: '/'.join(args[1:])
                mock_load_uploaded_file.return_value = [['a']]
                mock_does_file_exist = mock.MagicMock()
                mock_does_file_exist.wait.return_value = 1
                mock_subprocess.side_effect = [mock_does_file_exist]
                response = self.client.post(url, content_type='application/json', data=json.dumps(body))
                self.assertEqual(response.status_code, 400)
                self.assertDictEqual(response.json(), {'error': 'File not found: gs://rna_data/muscle_samples.tsv.gz'})

                mock_does_file_exist.wait.return_value = 0
                mock_file_iter = mock.MagicMock()
                def _set_file_iter_stdout(rows):
                    mock_file_iter.stdout = [('\t'.join([str(col) for col in row]) + '\n').encode() for row in rows]
                    mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]

                _set_file_iter_stdout([['']])
                response = self.client.post(url, content_type='application/json', data=json.dumps(body))
                self.assertEqual(response.status_code, 400)
                self.assertDictEqual(response.json(), {
                    'error': f'Invalid file: missing column(s): '
                             f'{", ".join(sorted([col for col in header if col not in params["optional_headers"]]))}',
                })

                mismatch_row = loaded_data_row[:-1] + [loaded_data_row[-1] - 2]
                _set_file_iter_stdout([header, loaded_data_row, loaded_data_row, mismatch_row])
                response = self.client.post(url, content_type='application/json', data=json.dumps(body))
                self.assertEqual(response.status_code, 400)
                response_json = response.json()
                self.assertTrue('errors' in response_json.keys())
                self.assertEqual(len(response_json['errors']), 1)
                self.assertTrue(response_json['errors'][0].startswith(
                    f'Error in {loaded_data_row[0]} data for {params.get("row_id", mismatch_row[2])}: mismatched entries '))

                missing_sample_row = ['NA19675_D3'] + loaded_data_row[1:]
                _set_file_iter_stdout([header, loaded_data_row, missing_sample_row])
                response = self.client.post(url, content_type='application/json', data=json.dumps(body))
                self.assertEqual(response.status_code, 400)
                self.assertDictEqual(response.json(), {'error': 'Unable to find matches for the following samples: NA19675_D3'})

                unknown_gene_id_row1 = loaded_data_row[:2] + ['NOT_A_GENE_ID1'] + loaded_data_row[3:]
                unknown_gene_id_row2 = loaded_data_row[:2] + ['NOT_A_GENE_ID2'] + loaded_data_row[3:]
                _set_file_iter_stdout([header, unknown_gene_id_row1, unknown_gene_id_row2])
                response = self.client.post(url, content_type='application/json', data=json.dumps(body))
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()['errors'][0], 'Unknown Gene IDs: NOT_A_GENE_ID1, NOT_A_GENE_ID2')

                mapping_body = {'mappingFile': {'uploadedFileId': 'map.tsv'}}
                mapping_body.update(body)
                mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
                response = self.client.post(url, content_type='application/json', data=json.dumps(mapping_body))
                self.assertEqual(response.status_code, 400)
                self.assertDictEqual(response.json(), {'error': 'Must contain 2 columns: a'})

                # Test already loaded data
                mock_send_slack.reset_mock()
                self.reset_logs()
                _set_file_iter_stdout([header, loaded_data_row])
                response = self.client.post(url, content_type='application/json', data=json.dumps(body))
                self.assertEqual(response.status_code, 200)
                info = [
                    'Parsed 1 RNA-seq samples',
                    'Attempted data loading for 0 RNA-seq samples in the following 0 projects: ',
                ]
                warnings = ['Skipped loading for 1 samples already loaded from this file']
                self.assertDictEqual(response.json(), {'info': info, 'warnings': warnings, 'sampleGuids': [], 'fileName': mock.ANY})
                self._has_expected_file_loading_logs('gs://rna_data/muscle_samples.tsv.gz', info=info, warnings=warnings)
                self.assertEqual(model_cls.objects.count(), params['initial_model_count'])
                mock_send_slack.assert_not_called()

                def _test_basic_data_loading(data, num_parsed_samples, num_loaded_samples, new_sample_individual_id, body,
                                             project_names, num_created_samples=1, warnings=None, additional_logs=None):
                    self.reset_logs()
                    _set_file_iter_stdout([header] + data)
                    response = self.client.post(url, content_type='application/json', data=json.dumps(body))
                    self.assertEqual(response.status_code, 200)
                    num_projects = len(project_names.split(','))
                    info = [
                        f'Parsed {num_parsed_samples} RNA-seq samples',
                        f'Attempted data loading for {num_loaded_samples} RNA-seq samples in the following {num_projects}'
                        f' projects: {project_names}'
                    ]
                    file_name = RNA_FILENAME_TEMPLATE.format(data_type)
                    response_json = response.json()
                    self.assertDictEqual(response_json, {'info': info, 'warnings': warnings or [], 'sampleGuids': mock.ANY,
                                                         'fileName': file_name})
                    new_sample_guid = self._check_rna_sample_model(
                        individual_id=new_sample_individual_id, data_source='new_muscle_samples.tsv.gz',
                        tissue_type=params.get('sample_tissue_type'),
                    )
                    self.assertTrue(new_sample_guid in response_json['sampleGuids'])
                    additional_logs = [(f'create {num_created_samples} Samples', {'dbUpdate': {
                        'dbEntity': 'Sample', 'updateType': 'bulk_create',
                        'entityIds': response_json['sampleGuids'] if num_created_samples > 1 else [response_json['sampleGuids'][-1]],
                    }})] + (additional_logs or [])
                    self._has_expected_file_loading_logs(
                        'gs://rna_data/new_muscle_samples.tsv.gz', info=info, warnings=warnings,
                        additional_logs=additional_logs, additional_logs_offset=3)

                    return response_json, new_sample_guid

                # Test loading new data
                mock_open.reset_mock()
                self.reset_logs()
                mock_load_uploaded_file.return_value = [['NA19675_D2', 'NA19675_1']]
                mock_writes = []
                def mock_write(content):
                    mock_writes.append(content)
                mock_open.return_value.__enter__.return_value.write.side_effect = mock_write
                body.update({'ignoreExtraSamples': True, 'mappingFile': {'uploadedFileId': 'map.tsv'}, 'file': RNA_FILE_ID})
                warnings = [
                    f'Skipped loading for the following {len(params["skipped_samples"].split(","))} '
                    f'unmatched samples: {params["skipped_samples"]}']
                if params.get('extra_warnings'):
                    warnings = params['extra_warnings'] + warnings
                deleted_count = params.get('deleted_count', params['initial_model_count'])
                response_json, new_sample_guid = _test_basic_data_loading(
                    params['new_data'], params["num_parsed_samples"], 2, 16, body,
                    '1kg project nåme with uniçøde, Test Reprocessed Project', warnings=warnings,
                    additional_logs=[
                        (f'delete {model_cls.__name__}s', {'dbUpdate': {
                            'dbEntity': model_cls.__name__, 'numEntities': deleted_count,
                           'parentEntityIds': [params['sample_guid']], 'updateType': 'bulk_delete'}}),
                        ('update 1 Samples', {'dbUpdate': {
                            'dbEntity': 'Sample', 'entityIds': [params['sample_guid']],
                            'updateType': 'bulk_update', 'updateFields': ['data_source']}}),
                    ])
                self.assertTrue(params['sample_guid'] in response_json['sampleGuids'])
                self.assertEqual(mock_send_slack.call_count, 2)
                mock_send_slack.assert_has_calls([
                    mock.call(
                        'seqr-data-loading',
                        f'0 new RNA {params["message_data_type"]} samples are loaded in <https://test-seqr.org/project/R0001_1kg/project_page|1kg project nåme with uniçøde>\n``````',
                    ), mock.call(
                        'seqr-data-loading',
                        f'1 new RNA {params["message_data_type"]} samples are loaded in <https://test-seqr.org/project/'
                        f'R0003_test/project_page|Test Reprocessed Project>\n```NA20888```',
                    ),
                ])

                # test database models are correct
                self.assertEqual(model_cls.objects.count(), params['initial_model_count'] - deleted_count)
                sample_guid = self._check_rna_sample_model(individual_id=1, data_source='new_muscle_samples.tsv.gz',
                                                           tissue_type=params.get('sample_tissue_type'))
                self.assertSetEqual(set(response_json['sampleGuids']), {sample_guid, new_sample_guid})

                # test correct file interactions
                mock_subprocess.assert_called_with(f'gsutil cat {RNA_FILE_ID} | gunzip -c -q - ', stdout=-1, stderr=-2, shell=True)
                mock_open.assert_called_with(RNA_FILENAME_TEMPLATE.format(data_type), 'wt')
                self.assertListEqual(mock_writes, [row.replace(PLACEHOLDER_GUID, new_sample_guid) for row in params['parsed_file_data']])

                # test loading new data without deleting existing data
                data = [params['no_existing_data']]
                body.pop('mappingFile')
                _test_basic_data_loading(data, 1, 1, 2, body, '1kg project nåme with uniçøde')

                # Test loading data when where are duplicated individual ids in different projects.
                data = params['duplicated_indiv_id_data']
                mock_writes = []
                _test_basic_data_loading(data, 2, 2, 20, body, '1kg project nåme with uniçøde, Test Reprocessed Project',
                                         num_created_samples=2)
                self.assertSetEqual(set([s.split('_', 1)[1] for s in mock_writes]), params['write_data'])

    @mock.patch('seqr.views.apis.data_manager_api.os')
    @mock.patch('seqr.views.apis.data_manager_api.gzip.open')
    def test_load_rna_seq_sample_data(self, mock_open, mock_os):
        mock_os.path.join.side_effect = lambda *args: '/'.join(args[1:])

        url = reverse(load_rna_seq_sample_data, args=[RNA_SAMPLE_GUID])
        self.check_data_manager_login(url)

        for data_type, params in self.RNA_DATA_TYPE_PARAMS.items():
            with self.subTest(data_type):
                sample_guid = params['sample_guid']
                url = reverse(load_rna_seq_sample_data, args=[sample_guid])
                model_cls = params['model_cls']
                model_cls.objects.all().delete()
                self.reset_logs()
                mock_open.return_value.__enter__.return_value.__iter__.return_value = params['parsed_file_data']
                file_name = RNA_FILENAME_TEMPLATE.format(data_type)

                response = self.client.post(url, content_type='application/json', data=json.dumps({
                    'fileName': file_name, 'dataType': data_type,
                }))
                self.assertEqual(response.status_code, 200)
                self.assertDictEqual(response.json(), {'success': True})

                models = model_cls.objects.all()
                self.assertEqual(models.count(), 2)
                self.assertSetEqual({model.sample.guid for model in models}, {sample_guid})

                mock_open.assert_called_with(file_name, 'rt')

                self.assert_json_logs(self.data_manager_user, [
                    (f'Loading outlier data for {params["loaded_data_row"][0]}', None),
                    (f'create {model_cls.__name__}s', {'dbUpdate': {
                        'dbEntity': model_cls.__name__, 'numEntities': 2, 'parentEntityIds': [sample_guid],
                        'updateType': 'bulk_create',
                    }}),
                ])

                self.assertListEqual(list(params['get_models_json'](models)), params['expected_models_json'])

    @classmethod
    def _join_data(cls, data):
        return ['\t'.join(line).encode('utf-8') for line in data]

    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_load_phenotype_prioritization_data(self, mock_subprocess):
        url = reverse(load_phenotype_prioritization_data)
        self.check_data_manager_login(url)

        request_body = {'file': 'gs://seqr_data/lirical_data.tsv.gz'}
        mock_subprocess.return_value.wait.return_value = 1
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'File not found: gs://seqr_data/lirical_data.tsv.gz')
        mock_subprocess.assert_called_with('gsutil ls gs://seqr_data/lirical_data.tsv.gz', stdout=-1, stderr=-2, shell=True)

        mock_subprocess.reset_mock()
        mock_subprocess.return_value.wait.return_value = 0
        mock_subprocess.return_value.stdout = self._join_data(PHENOTYPE_PRIORITIZATION_MISS_HEADER)
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Invalid file: missing column(s) project, diseaseId')
        mock_subprocess.assert_called_with('gsutil cat gs://seqr_data/lirical_data.tsv.gz | gunzip -c -q - ', stdout=-1, stderr=-2, shell=True)

        mock_subprocess.reset_mock()
        mock_subprocess.return_value.stdout = self._join_data(PHENOTYPE_PRIORITIZATION_HEADER + LIRICAL_NO_PROJECT_DATA)
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Both sample ID and project fields are required.')
        mock_subprocess.assert_called_with('gsutil cat gs://seqr_data/lirical_data.tsv.gz | gunzip -c -q - ', stdout=-1, stderr=-2, shell=True)

        mock_subprocess.return_value.stdout = self._join_data(PHENOTYPE_PRIORITIZATION_HEADER + LIRICAL_DATA + EXOMISER_DATA)
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Multiple tools found lirical and exomiser. Only one in a file is supported.')

        mock_subprocess.return_value.stdout = self._join_data(PHENOTYPE_PRIORITIZATION_HEADER + LIRICAL_PROJECT_NOT_EXIST_DATA)
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Project CMG_Beggs_WGS not found. ')

        project = Project.objects.create(created_by=self.data_manager_user,
                                         name='1kg project nåme with uniçøde', workspace_namespace='my-seqr-billing')
        mock_subprocess.return_value.stdout = self._join_data(
            PHENOTYPE_PRIORITIZATION_HEADER + LIRICAL_DATA + LIRICAL_PROJECT_NOT_EXIST_DATA)
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Project CMG_Beggs_WGS not found. Projects with conflict name(s) 1kg project nåme with uniçøde.')
        project.delete()

        mock_subprocess.return_value.stdout = self._join_data(PHENOTYPE_PRIORITIZATION_HEADER + LIRICAL_NO_EXIST_INDV_DATA)
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], "Can't find individuals NA19678x, NA19679x")

        # Test a successful operation
        mock_subprocess.reset_mock()
        mock_subprocess.return_value.stdout = self._join_data(PHENOTYPE_PRIORITIZATION_HEADER + LIRICAL_DATA)
        self.reset_logs()
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        info = [
            'Loaded Lirical data from gs://seqr_data/lirical_data.tsv.gz',
            'Project 1kg project nåme with uniçøde: deleted 1 record(s), loaded 1 record(s)',
            'Project Test Reprocessed Project: loaded 1 record(s)'
        ]
        self.assertEqual(response.json()['info'], info)
        self._has_expected_file_loading_logs('gs://seqr_data/lirical_data.tsv.gz', additional_logs=[
            ('delete PhenotypePrioritizations', {'dbUpdate': {
                'dbEntity': 'PhenotypePrioritization', 'numEntities': 1, 'updateType': 'bulk_delete',
                'parentEntityIds': ['I000002_na19678'],
            }}),
            ('create PhenotypePrioritizations', {'dbUpdate': {
                'dbEntity': 'PhenotypePrioritization', 'numEntities': 2, 'updateType': 'bulk_create',
                'parentEntityIds': ['I000002_na19678', 'I000015_na20885'],
            }}),
        ])
        saved_data = _get_json_for_models(PhenotypePrioritization.objects.filter(tool='lirical').order_by('id'),
                                          nested_fields=[{'fields': ('individual', 'guid'), 'key': 'individualGuid'}])
        self.assertListEqual(saved_data, EXPECTED_LIRICAL_DATA)
        mock_subprocess.assert_called_with('gsutil cat gs://seqr_data/lirical_data.tsv.gz | gunzip -c -q - ', stdout=-1, stderr=-2, shell=True)

        # Test uploading new data
        self.reset_logs()
        mock_subprocess.return_value.stdout = self._join_data(PHENOTYPE_PRIORITIZATION_HEADER + UPDATE_LIRICAL_DATA)
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        info = [
            'Loaded Lirical data from gs://seqr_data/lirical_data.tsv.gz',
            'Project 1kg project nåme with uniçøde: deleted 1 record(s), loaded 2 record(s)'
        ]
        self.assertEqual(response.json()['info'], info)
        self._has_expected_file_loading_logs('gs://seqr_data/lirical_data.tsv.gz', additional_logs=[
            ('delete PhenotypePrioritizations', {'dbUpdate': {
                'dbEntity': 'PhenotypePrioritization', 'numEntities': 1, 'updateType': 'bulk_delete',
                'parentEntityIds': ['I000002_na19678'],
            }}),
            ('create PhenotypePrioritizations', {'dbUpdate': {
                'dbEntity': 'PhenotypePrioritization', 'numEntities': 2, 'updateType': 'bulk_create',
                'parentEntityIds': ['I000002_na19678'],
            }}),
        ])
        saved_data = _get_json_for_models(PhenotypePrioritization.objects.filter(tool='lirical'),
                                          nested_fields=[{'fields': ('individual', 'guid'), 'key': 'individualGuid'}])
        self.assertListEqual(saved_data, EXPECTED_UPDATED_LIRICAL_DATA)

    @staticmethod
    def _ls_subprocess_calls(file, is_error=True):
        calls = [
            mock.call(f'gsutil ls {file}',stdout=-1, stderr=-2, shell=True),
            mock.call().wait(),
        ]
        if is_error:
            calls.append(mock.call().stdout.__iter__())
        return calls

    @mock.patch('seqr.views.utils.export_utils.open')
    @mock.patch('seqr.views.utils.export_utils.TemporaryDirectory')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_write_pedigree(self, mock_subprocess, mock_temp_dir, mock_open):
        mock_temp_dir.return_value.__enter__.return_value = '/mock/tmp'
        mock_subprocess.return_value.wait.return_value = 1

        url = reverse(write_pedigree, args=[PROJECT_GUID])
        self.check_data_manager_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], f'No gs://seqr-datasets/v02 project directory found for {PROJECT_GUID}')
        mock_subprocess.assert_has_calls(
            self._ls_subprocess_calls('gs://seqr-datasets/v02/GRCh37/RDG_WGS_Broad_Internal/base/projects/R0001_1kg') +
            self._ls_subprocess_calls('gs://seqr-datasets/v02/GRCh37/RDG_WES_Broad_Internal/base/projects/R0001_1kg') +
            self._ls_subprocess_calls('gs://seqr-datasets/v02/GRCh37/RDG_WGS_Broad_External/base/projects/R0001_1kg') +
            self._ls_subprocess_calls('gs://seqr-datasets/v02/GRCh37/RDG_WES_Broad_External/base/projects/R0001_1kg')
        )

        # Test success
        mock_subprocess.reset_mock()
        mock_subprocess.return_value.wait.side_effect = [1, 0, 0]
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': True})

        mock_open.assert_called_with(f'/mock/tmp/{PROJECT_GUID}_pedigree.tsv', 'w')
        write_call = mock_open.return_value.__enter__.return_value.write.call_args.args[0]
        file = [row.split('\t') for row in write_call.split('\n')]
        self.assertEqual(len(file), 15)
        self.assertListEqual(file[:5], [
            ['Project_GUID', 'Family_GUID', 'Family_ID', 'Individual_ID', 'Paternal_ID', 'Maternal_ID', 'Sex'],
            ['R0001_1kg', 'F000001_1', '1', 'NA19675_1', 'NA19678', 'NA19679', 'M'],
            ['R0001_1kg', 'F000001_1', '1', 'NA19678', '', '', 'M'],
            ['R0001_1kg', 'F000001_1', '1', 'NA19679', '', '', 'F'],
            ['R0001_1kg', 'F000002_2', '2', 'HG00731', 'HG00732', 'HG00733', 'F'],
         ])

        mock_subprocess.assert_has_calls(
            self._ls_subprocess_calls('gs://seqr-datasets/v02/GRCh37/RDG_WGS_Broad_Internal/base/projects/R0001_1kg') +
            self._ls_subprocess_calls(
                'gs://seqr-datasets/v02/GRCh37/RDG_WES_Broad_Internal/base/projects/R0001_1kg', is_error=False,
            ) + [
            mock.call('gsutil mv /mock/tmp/* gs://seqr-datasets/v02/GRCh37/RDG_WES_Broad_Internal/base/projects/R0001_1kg', stdout=-1, stderr=-2, shell=True),
            mock.call().wait(),
        ])

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_validate_callset(self, mock_subprocess):
        url = reverse(validate_callset)
        self.check_pm_login(url)

        mock_subprocess.return_value.wait.return_value = -1
        mock_subprocess.return_value.stdout = [b'File not found']
        body = {'filePath': 'gs://test_bucket/mito_callset.mt', 'datasetType': 'SV'}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [
            'Invalid VCF file format - file path must end with .bed or .vcf or .vcf.gz or .vcf.bgz',
        ])

        body['datasetType'] = 'MITO'
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Data file or path gs://test_bucket/mito_callset.mt is not found.'])

        mock_subprocess.return_value.wait.return_value = 0
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': True})

        # test data manager access
        self.login_data_manager_user()
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
    def test_get_loaded_projects(self):
        url = reverse(get_loaded_projects, args=['WGS', 'SV'])
        self.check_pm_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'projects': [
            {'dataTypeLastLoaded': None, 'name': '1kg project nåme with uniçøde', 'projectGuid': 'R0001_1kg'},
            {'dataTypeLastLoaded': '2018-02-05T06:42:55.397Z', 'name': 'Non-Analyst Project', 'projectGuid': 'R0004_non_analyst_project'},
        ]})

        # test data manager access
        self.login_data_manager_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class LoadDataAPITest(AirflowTestCase):
    fixtures = ['users', 'social_auth', '1kg_project']

    DAG_NAME = 'RDG_WGS_Broad_Internal_MITO'
    LOADING_PROJECT_GUID = 'R0004_non_analyst_project'

    def _get_expected_dag_variables(self, *args, **kwargs):
        variables = super(LoadDataAPITest, self)._get_expected_dag_variables()
        variables.update({
            'vcf_path': 'gs://test_bucket/mito_callset.mt',
            'version_path': 'gs://seqr-datasets/v02/GRCh38/RDG_WGS_Broad_Internal_MITO/v01',
        })
        return variables

    @responses.activate
    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_load_data(self, mock_subprocess):
        url = reverse(load_data)
        self.check_pm_login(url)

        responses.replace(responses.GET, f'{self.dag_url}/dagRuns', json={'dag_runs': []})
        mock_subprocess.return_value.communicate.return_value = b'', b'File not found'
        body = {'filePath': 'gs://test_bucket/mito_callset.mt', 'datasetType': 'MITO', 'sampleType': 'WGS', 'projects': [
            'R0001_1kg', 'R0004_non_analyst_project',
        ]}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': True})

        self.assert_airflow_calls()
        mock_subprocess.assert_called_with(
            'gsutil ls gs://seqr-datasets/v02/GRCh38/RDG_WGS_Broad_Internal_MITO', stdout=-1, stderr=-1, shell=True)  # nosec

        slack_message = """*test_pm_user@test.com* triggered loading internal WGS MITO data for 2 projects

        DAG seqr_vcf_to_es_RDG_WGS_Broad_Internal_MITO_v0.0.1 is triggered with following:
        ```{
    "active_projects": [
        "R0001_1kg",
        "R0004_non_analyst_project"
    ],
    "projects_to_run": [
        "R0001_1kg",
        "R0004_non_analyst_project"
    ],
    "vcf_path": "gs://test_bucket/mito_callset.mt",
    "version_path": "gs://seqr-datasets/v02/GRCh38/RDG_WGS_Broad_Internal_MITO/v01"
}```
    """

        self.mock_slack.assert_called_once_with(SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, slack_message)

        # Test loading trigger error
        self.mock_slack.reset_mock()
        responses.calls.reset()
        mock_subprocess.return_value.communicate.return_value = b'gs://seqr-datasets/v02/GRCh38/RDG_WGS_Broad_Internal_SV/\ngs://seqr-datasets/v02/GRCh38/RDG_WGS_Broad_Internal_SV/v01/\ngs://seqr-datasets/v02/GRCh38/RDG_WGS_Broad_Internal_SV/v02/', b''

        body.update({'datasetType': 'SV', 'filePath': 'gs://test_bucket/sv_callset.vcf'})
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': True})

        self.assert_airflow_calls(trigger_error=True, dag_name='RDG_WGS_Broad_Internal_SV')

        mock_subprocess.assert_called_with(
            'gsutil ls gs://seqr-datasets/v02/GRCh38/RDG_WGS_Broad_Internal_SV', stdout=-1, stderr=-1, shell=True)  # nosec
        self.mock_airflow_logger.warning.assert_not_called()
        self.mock_airflow_logger.error.assert_called_with(mock.ANY, self.pm_user)
        error = self.mock_airflow_logger.error.call_args.args[0]
        self.assertRegex(error, 'Connection refused by Responses')

        error_message = f"""ERROR triggering internal WGS SV loading: {error}
        
        DAG seqr_vcf_to_es_RDG_WGS_Broad_Internal_SV_v0.0.1 should be triggered with following: 
        ```{{
    "active_projects": [
        "R0001_1kg",
        "R0004_non_analyst_project"
    ],
    "projects_to_run": [
        "R0001_1kg",
        "R0004_non_analyst_project"
    ],
    "vcf_path": "gs://test_bucket/sv_callset.vcf",
    "version_path": "gs://seqr-datasets/v02/GRCh38/RDG_WGS_Broad_Internal_SV/v03"
}}```
        """
        self.mock_slack.assert_called_once_with(SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, error_message)
