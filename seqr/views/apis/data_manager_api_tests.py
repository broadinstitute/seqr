from datetime import datetime
from django.urls.base import reverse
import json
import mock
from requests import HTTPError
import responses

from seqr.views.apis.data_manager_api import elasticsearch_status, upload_qc_pipeline_output, delete_index, \
    update_rna_seq, load_rna_seq_sample_data
from seqr.views.utils.orm_to_json_utils import get_json_for_rna_seq_outliers
from seqr.views.utils.test_utils import AuthenticationTestCase, urllib3_responses
from seqr.models import Individual, RnaSeqOutlier, RnaSeqTpm, Sample


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
    'test_index_old does not exist and is used by project(s) 1kg project n\xe5me with uni\xe7\xf8de (1 samples)']

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
RNA_FILE_ID = 'gs://rna_data/new_muscle_samples.tsv.gz'
SAMPLE_GENE_OUTLIER_DATA = {
    'ENSG00000240361': {'gene_id': 'ENSG00000240361', 'p_value': '0.01', 'p_adjust': '0.13', 'z_score': '-3.1'},
    'ENSG00000233750': {'gene_id': 'ENSG00000233750', 'p_value': '0.064', 'p_adjust': '0.0000057', 'z_score': '7.8'},
}
SAMPLE_GENE_TPM_DATA = {
    'ENSG00000240361': {'gene_id': 'ENSG00000240361', 'tpm': '7.8'},
    'ENSG00000233750': {'gene_id': 'ENSG00000233750', 'tpm': '0.064'},
}
RNA_OUTLIER_SAMPLE_DATA = [f'{RNA_SAMPLE_GUID}\t\t{json.dumps(SAMPLE_GENE_OUTLIER_DATA)}\n']
RNA_TPM_SAMPLE_DATA = [f'{RNA_SAMPLE_GUID}\t\t{json.dumps(SAMPLE_GENE_TPM_DATA)}\n']
RNA_FILENAME_TEMPLATE = 'rna_sample_data__{}__2020-04-15T00:00:00.json.gz'


class DataManagerAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'reference_data']

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

    @urllib3_responses.activate
    def test_delete_index(self):
        url = reverse(delete_index)
        self.check_data_manager_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({'index': 'test_index'}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(), ({'error': 'Index "test_index" is still used by: 1kg project n\xe5me with uni\xe7\xf8de'}))
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

    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_upload_qc_pipeline_output(self, mock_subprocess):
        url = reverse(upload_qc_pipeline_output,)
        self.check_data_manager_login(url)

        request_data =json.dumps({
            'file': ' gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/final_output/seqr_sample_qc.tsv'
        })

        # Test missing file
        mock_does_file_exist = mock.MagicMock()
        mock_subprocess.side_effect = [mock_does_file_exist]
        mock_does_file_exist.wait.return_value = 1
        response = self.client.post(url, content_type='application/json', data=request_data)
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(
            response.json()['errors'],
            ['File not found: gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/final_output/seqr_sample_qc.tsv'])

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
            'header': ['sampleID', 'geneID', 'detail', 'pValue', 'padjust', 'zScore'],
            'optional_headers': ['detail'],
            'loaded_data_row': ['NA19675_D2', 'ENSG00000240361', 'detail1', 0.01, 0.001, -3.1],
            'new_data': [
                ['NA19675_D2', 'ENSG00000240361', 'detail1', 0.01, 0.13, -3.1],
                ['NA19675_D2', 'ENSG00000240361', 'detail2', 0.01, 0.13, -3.1],
                ['NA19675_D2', 'ENSG00000233750', 'detail1', 0.064, '0.0000057', 7.8],
                ['NA19675_D3', 'ENSG00000233750', 'detail1', 0.064, '0.0000057', 7.8],
            ],
            'num_parsed_samples': 2,
            'initial_model_count': 3,
            'parsed_file_data': RNA_OUTLIER_SAMPLE_DATA,
            'get_models_json': get_json_for_rna_seq_outliers,
            'expected_models_json': [
                {'geneId': 'ENSG00000240361', 'pAdjust': 0.13, 'pValue': 0.01, 'zScore': -3.1, 'isSignificant': False},
                {'geneId': 'ENSG00000233750', 'pAdjust': 0.0000057, 'pValue': 0.064, 'zScore': 7.8,
                 'isSignificant': True},
            ],
        },
        'tpm': {
            'model_cls': RnaSeqTpm,
            'header': ['sample_id', 'gene_id', 'individual_id', 'tissue', 'TPM'],
            'optional_headers': ['individual_id'],
            'loaded_data_row': ['NA19675_D2', 'NA19675_D3', 'ENSG00000135953', 'muscle', 1.34],
            'new_data': [
                ['NA19675_D2', 'ENSG00000240361', 'NA19675_D2', 'muscle', 7.8],
                ['NA19675_D2', 'ENSG00000233750', 'NA19675_D2', 'muscle', 0.064],
                ['NA19675_D2', 'ENSG00000135953', 'NA19675_D2', 'muscle', '0.0'],
                ['NA20889', 'ENSG00000233750', 'NA20889', 'fibroblasts', 0.064],
                ['NA19675_D3', 'ENSG00000233750', 'NA19675_D3', 'fibroblasts', 0.064],
                ['GTEX_001', 'ENSG00000233750', 'NA19675_D3', 'whole_blood', 1.95],
            ],
            'num_parsed_samples': 3,
            'initial_model_count': 2,
            'deleted_count': 1,
            'extra_warnings': [
                'Skipped data loading for the following 1 samples due to mismatched tissue type: NA20889 (fibroblasts to muscle)'],
            'parsed_file_data': RNA_TPM_SAMPLE_DATA,
            'get_models_json': lambda models: list(models.values_list('gene_id', 'tpm')),
            'expected_models_json': [('ENSG00000240361', 7.8), ('ENSG00000233750',0.064)],
        },
    }

    @mock.patch('seqr.views.utils.dataset_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.apis.data_manager_api.datetime')
    @mock.patch('seqr.views.apis.data_manager_api.os')
    @mock.patch('seqr.views.apis.data_manager_api.load_uploaded_file')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    @mock.patch('seqr.views.apis.data_manager_api.gzip.open')
    @mock.patch('seqr.views.utils.dataset_utils.logger')
    def test_update_rna_seq(self, mock_logger, mock_open, mock_subprocess, mock_load_uploaded_file, mock_os, mock_datetime):
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
                    'error': f'Invalid file: missing column(s) {", ".join(sorted([col for col in header if col not in params["optional_headers"]]))}',
                })

                mismatch_row = loaded_data_row[:-1] + [loaded_data_row[-1] - 2]
                _set_file_iter_stdout([header, loaded_data_row, mismatch_row])
                response = self.client.post(url, content_type='application/json', data=json.dumps(body))
                self.assertEqual(response.status_code, 400)
                self.assertDictEqual(response.json(), {'error': mock.ANY})
                self.assertTrue(response.json()['error'].startswith(
                    f'Error in NA19675_D2 data for {mismatch_row[1]}: mismatched entries '))

                missing_sample_row = ['NA19675_D3'] + loaded_data_row[1:]
                _set_file_iter_stdout([header, loaded_data_row, missing_sample_row])
                response = self.client.post(url, content_type='application/json', data=json.dumps(body))
                self.assertEqual(response.status_code, 400)
                self.assertDictEqual(response.json(), {'error': 'Unable to find matches for the following samples: NA19675_D3'})

                mapping_body = {'mappingFile': {'uploadedFileId': 'map.tsv'}}
                mapping_body.update(body)
                mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
                response = self.client.post(url, content_type='application/json', data=json.dumps(mapping_body))
                self.assertEqual(response.status_code, 400)
                self.assertDictEqual(response.json(), {'error': 'Must contain 2 columns: a'})

                # Test already loaded data
                _set_file_iter_stdout([header, loaded_data_row])
                response = self.client.post(url, content_type='application/json', data=json.dumps(body))
                self.assertEqual(response.status_code, 200)
                info = [
                    'Parsed 1 RNA-seq samples',
                    'Attempted data loading for 0 RNA-seq samples in the following 0 projects: ',
                ]
                warnings = ['Skipped loading for 1 samples already loaded from this file']
                self.assertDictEqual(response.json(), {'info': info, 'warnings': warnings, 'sampleGuids': [], 'fileName': mock.ANY})
                mock_logger.info.assert_has_calls([mock.call(info_log, self.data_manager_user) for info_log in info])
                mock_logger.warning.assert_has_calls([mock.call(warn_log, self.data_manager_user) for warn_log in warnings])
                self.assertEqual(model_cls.objects.count(), params['initial_model_count'])

                # Test loading new data
                mock_open.reset_mock()
                mock_logger.reset_mock()
                _set_file_iter_stdout([header] + params['new_data'])
                mock_load_uploaded_file.return_value = [['NA19675_D2', 'NA19675_1']]
                mock_writes = []
                def mock_write(content):
                    mock_writes.append(content)
                mock_open.return_value.__enter__.return_value.write.side_effect = mock_write
                body.update({'ignoreExtraSamples': True, 'mappingFile': {'uploadedFileId': 'map.tsv'}, 'file': RNA_FILE_ID})
                response = self.client.post(url, content_type='application/json', data=json.dumps(body))
                self.assertEqual(response.status_code, 200)
                info = [
                    f'Parsed {params["num_parsed_samples"]} RNA-seq samples',
                    'Attempted data loading for 1 RNA-seq samples in the following 1 projects: 1kg project nåme with uniçøde',
                ]
                warnings = ['Skipped loading for the following 1 unmatched samples: NA19675_D3']
                if params.get('extra_warnings'):
                    warnings = params['extra_warnings'] + warnings
                file_name = RNA_FILENAME_TEMPLATE.format(data_type)
                response_json = response.json()
                self.assertDictEqual(response_json, {'info': info, 'warnings': warnings, 'sampleGuids': [mock.ANY], 'fileName': file_name})
                deleted_count = params.get('deleted_count', params['initial_model_count'])
                mock_logger.info.assert_has_calls(
                    [mock.call(info_log, self.data_manager_user) for info_log in info] + [
                        mock.call(f'delete {deleted_count} {model_cls.__name__}s', self.data_manager_user, db_update={
                            'dbEntity': model_cls.__name__, 'numEntities': deleted_count, 'parentEntityIds': mock.ANY, 'updateType': 'bulk_delete',
                        }),
                    ], any_order=True
                )
                self.assertTrue(RNA_SAMPLE_GUID in mock_logger.info.call_args_list[1].kwargs['db_update']['parentEntityIds'])
                mock_logger.warning.assert_has_calls([mock.call(warn_log, self.data_manager_user) for warn_log in warnings])

                # test database models are correct
                self.assertEqual(model_cls.objects.count(), params['initial_model_count'] - deleted_count)
                rna_samples = Sample.objects.filter(individual_id=1, sample_type='RNA')
                self.assertEqual(len(rna_samples), 1)
                sample = rna_samples.first()
                self.assertEqual(sample.guid, RNA_SAMPLE_GUID)
                self.assertTrue(sample.is_active)
                self.assertIsNone(sample.elasticsearch_index)
                self.assertEqual(sample.data_source, 'muscle_samples.tsv.gz')
                self.assertEqual(sample.sample_type, 'RNA')

                self.assertEqual(response_json['sampleGuids'][0], sample.guid)

                # test correct file interactions
                mock_subprocess.assert_called_with(f'gsutil cat {RNA_FILE_ID} | gunzip -c -q - ', stdout=-1, stderr=-2, shell=True)
                mock_open.assert_called_with(file_name, 'wt')
                self.assertListEqual(mock_writes, params['parsed_file_data'])

    @mock.patch('seqr.views.apis.data_manager_api.os')
    @mock.patch('seqr.views.apis.data_manager_api.gzip.open')
    @mock.patch('seqr.views.apis.data_manager_api.logger')
    def test_load_rna_seq_sample_data(self, mock_logger, mock_open, mock_os):
        mock_os.path.join.side_effect = lambda *args: '/'.join(args[1:])

        url = reverse(load_rna_seq_sample_data, args=[RNA_SAMPLE_GUID])
        self.check_data_manager_login(url)

        for data_type, params in self.RNA_DATA_TYPE_PARAMS.items():
            with self.subTest(data_type):
                model_cls = params['model_cls']
                model_cls.objects.all().delete()
                mock_open.return_value.__enter__.return_value.__iter__.return_value = params['parsed_file_data']
                file_name = RNA_FILENAME_TEMPLATE.format(data_type)

                response = self.client.post(url, content_type='application/json', data=json.dumps({
                    'fileName': file_name, 'dataType': data_type,
                }))
                self.assertEqual(response.status_code, 200)
                self.assertDictEqual(response.json(), {'success': True})

                models = model_cls.objects.all()
                self.assertEqual(models.count(), 2)
                self.assertSetEqual({model.sample.guid for model in models}, {RNA_SAMPLE_GUID})

                mock_open.assert_called_with(file_name, 'rt')

                mock_logger.info.assert_has_calls([
                    mock.call('Loading outlier data for NA19675_D2', self.data_manager_user),
                    mock.call(f'create 2 {model_cls.__name__}', self.data_manager_user, db_update={
                        'dbEntity':  model_cls.__name__, 'numEntities': 2, 'parentEntityIds': [RNA_SAMPLE_GUID], 'updateType': 'bulk_create',
                    }),
                ])

                self.assertListEqual(params['get_models_json'](models), params['expected_models_json'])
