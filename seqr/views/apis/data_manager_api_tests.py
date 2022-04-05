from datetime import datetime
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls.base import reverse
import json
import mock
from requests import HTTPError
import responses

from seqr.views.apis.data_manager_api import elasticsearch_status, upload_qc_pipeline_output, delete_index, \
    receive_rna_seq_table, update_rna_seq, load_rna_seq_sample_data
from seqr.views.utils.orm_to_json_utils import get_json_for_rna_seq_outliers
from seqr.views.utils.test_utils import AuthenticationTestCase, urllib3_responses
from seqr.models import Individual, RnaSeqOutlier, Sample


PROJECT_GUID = "R0001_1kg"

ES_CAT_ALLOCATION = [
    {
        "node": "node-1",
        "shards": "113",
        "disk.used": "67.2gb",
        "disk.avail": "188.6gb",
        "disk.percent": "26",
    },
    {
        "node": "UNASSIGNED",
        "shards": "2",
        "disk.used": None,
        "disk.avail": None,
        "disk.percent": None,
    },
]

ES_CAT_NODES = [
    {
        "name": "node-1",
        "heap.percent": "57",
    },
    {
        "name": "no-disk-node",
        "heap.percent": "83",
    },
]

EXPECTED_DISK_ALLOCATION = [
    {
        "node": "node-1",
        "shards": "113",
        "diskUsed": "67.2gb",
        "diskAvail": "188.6gb",
        "diskPercent": "26",
        "heapPercent": "57",
    },
    {
        "node": "UNASSIGNED",
        "shards": "2",
        "diskUsed": None,
        "diskAvail": None,
        "diskPercent": None,
    },
]

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
        "creation.date.string": "2019-10-03T19:53:53.846Z",
    },
    {
        "index": "test_index_alias_2",
        "docs.count": "672312",
        "store.size": "233.4mb",
        "creation.date.string": "2019-10-03T19:53:53.846Z",
    },
    {
        "index": "test_index_no_project",
        "docs.count": "672312",
        "store.size": "233.4mb",
        "creation.date.string": "2019-10-03T19:53:53.846Z",
    },
    {
        "index": "test_index_sv",
        "docs.count": "672312",
        "store.size": "233.4mb",
        "creation.date.string": "2019-10-03T19:53:53.846Z",
    },
    {
        "index": "test_index_sv_wgs",
        "docs.count": "672312",
        "store.size": "233.4mb",
        "creation.date.string": "2019-10-03T19:53:53.846Z"
    },
]

ES_CAT_ALIAS = [
    {"alias": "test_index_second", "index": "test_index_alias_1"},
    {"alias": "test_index_second", "index": "test_index_alias_2"},
]

ES_INDEX_MAPPING = {
    "test_index": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "25",
                "genomeVersion": "38",
                "sampleType": "WES",
                "sourceFilePath": "test_index_file_path",
            },
            "_all": {"enabled": False},
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
            "_all": {"enabled": False},
        }
    },
    "test_index_alias_2": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "19",
                "genomeVersion": "37",
                "sampleType": "WES",
                "datasetType": "VARIANTS",
                "sourceFilePath": "test_index_alias_2_path",
            },
            "_all": {"enabled": False},
        }
    },
    "test_index_no_project": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "19",
                "genomeVersion": "37",
                "sampleType": "WGS",
                "datasetType": "VARIANTS",
                "sourceFilePath": "test_index_no_project_path",
            },
            "_all": {"enabled": False},
        }
    },
    "test_index_sv": {
        "mappings": {
            "_meta": {
                "gencodeVersion": "29",
                "genomeVersion": "38",
                "sampleType": "WES",
                "datasetType": "SV",
                "sourceFilePath": "test_sv_index_path",
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
    "projects": [
        {
            "projectName": "1kg project n\xe5me with uni\xe7\xf8de",
            "projectGuid": "R0001_1kg",
        }
    ],
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
    "projects": [
        {
            "projectName": "1kg project n\xe5me with uni\xe7\xf8de",
            "projectGuid": "R0001_1kg",
        }
    ],
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
    "projects": [],
}

EXPECTED_ERRORS = [
    "test_index_old does not exist and is used by project(s) 1kg project n\xe5me with uni\xe7\xf8de (1 samples)"
]

SAMPLE_QC_DATA = [
    "PCT_CONTAMINATION	AL_PCT_CHIMERAS	HS_PCT_TARGET_BASES_20X	seqr_id	data_type	filter_flags	qc_platform	qc_pop	pop_PC1	pop_PC2	pop_PC3	pop_PC4	pop_PC5	pop_PC6	qc_metrics_filters	sample_qc.call_rate	sample_qc.n_called	sample_qc.n_not_called	sample_qc.n_filtered	sample_qc.n_hom_ref	sample_qc.n_het	sample_qc.n_hom_var	sample_qc.n_non_ref	sample_qc.n_singleton	sample_qc.n_snp	sample_qc.n_insertion	sample_qc.n_deletion	sample_qc.n_transition	sample_qc.n_transversion	sample_qc.n_star	sample_qc.r_ti_tv	sample_qc.r_het_hom_var	sample_qc.r_insertion_deletion	sample_qc.f_inbreeding.f_stat	sample_qc.f_inbreeding.n_called	sample_qc.f_inbreeding.expected_homs	sample_qc.f_inbreeding.observed_homs\n",
    '1.6E-01	5.567E-01	9.2619E+01	MANZ_1169_DNA	WES	[]	WES-010230 Standard Germline Exome	nfe	6.0654E-02	6.0452E-02	-6.2635E-03	-4.3252E-03	-2.1807E-02	-1.948E-02	["n_snp"]	7.1223E-01	14660344	5923237	0	14485322	114532	60490	175022	585	195114	18516	21882	133675	61439	0	2.1757E+00	1.8934E+00	8.4617E-01	5.3509E-01	14660344	1.4414E+07	14545812\n',
    'NA	NA	NA	NA	WES	[]	Unknown	nfe	4.6581E-02	5.7881E-02	-5.6011E-03	3.5992E-03	-2.9438E-02	-9.6098E-03	["r_insertion_deletion"]	6.2631E-01	12891805	7691776	0	12743977	97831	49997	147828	237	165267	15474	17084	114154	51113	0	2.2334E+00	1.9567E+00	9.0576E-01	5.4467E-01	12891805	1.2677E+07	12793974\n',
    'NA	NA	NA	NA19675_1	WES	[]	Unknown	amr	2.2367E-02	-1.9772E-02	6.3769E-02	2.5774E-03	-1.6655E-02	2.0457E-03	["r_ti_tv","n_deletion","n_snp","r_insertion_deletion","n_insertion"]	1.9959E-01	4108373	16475208	0	3998257	67927	42189	110116	18572	127706	13701	10898	82568	45138	0	1.8292E+00	1.6101E+00	1.2572E+00	5.3586E-02	4108373	4.0366E+06	4040446\n',
    '5.6E-01	3.273E-01	8.1446E+01	NA19678	WES	["coverage"]	Standard Exome Sequencing v4	sas	2.4039E-02	-6.9517E-02	-4.1485E-02	1.421E-01	7.5583E-02	-2.0986E-02	["n_insertion"]	4.6084E-01	9485820	11097761	0	9379951	59871	45998	105869	736	136529	6857	8481	95247	41282	0	2.3072E+00	1.3016E+00	8.0851E-01	5.2126E-01	9485820	9.3608E+06	9425949\n',
    '5.4E-01	5.0841E+00	8.7288E+01	HG00732	WES	["chimera"]	Standard Germline Exome v5	nfe	5.2785E-02	5.547E-02	-5.82E-03	2.7961E-02	-4.2259E-02	3.0271E-02	["n_insertion","r_insertion_deletion"]	6.8762E-01	14153622	6429959	0	13964844	123884	64894	188778	1719	202194	29507	21971	138470	63724	0	2.173E+00	1.909E+00	1.343E+00	4.924E-01	14153622	1.391E+07	14029738\n',
    '2.79E+00	1.8996E+01	7.352E+01	HG00733	WES	["contamination","not_real_flag"]	Standard Germline Exome v5	oth	-1.5417E-01	2.8868E-02	-1.3819E-02	4.1915E-02	-4.0001E-02	7.6392E-02	["n_insertion","r_insertion_deletion", "not_real_filter"]	6.1147E-01	12586314	7997267	0	12383958	140784	61572	202356	8751	204812	38051	21065	140282	64530	0	2.1739E+00	2.2865E+00	1.8064E+00	3.6592E-01	12586314	1.2364E+07	12445530\n',
]

SAMPLE_QC_DATA_NO_DATA_TYPE = [
    "seqr_id	data_type	filter_flags	qc_platform	qc_pop	qc_metrics_filters\n",
    "03133B_2	n/a	[]	Standard Germline Exome v5	nfe	[]\n",
]

SAMPLE_QC_DATA_MORE_DATA_TYPE = [
    "seqr_id	data_type	filter_flags	qc_platform	qc_pop	qc_metrics_filters\n",
    "03133B_2	WES	[]	Standard Germline Exome v5	nfe	[]\n",
    "03133B_3	WGS	[]	Standard Germline Exome v5	nfe	[]\n",
]


SAMPLE_QC_DATA_UNEXPECTED_DATA_TYPE = [
    "seqr_id	data_type	filter_flags	qc_platform	qc_pop	qc_metrics_filters\n",
    "03133B_2	UNKNOWN	[]	Standard Germline Exome v5	nfe	[]\n",
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
RNA_FILE_ID = 'tmp_-_2021-03-01T00:00:00_-_test_data_manager_-_new_muscle_samples.tsv.gz'
RNA_SAMPLE_DATA = json.dumps({
    'ENSG00000240361': {'gene_id': 'ENSG00000240361', 'p_value': '0.01', 'p_adjust': '0.13', 'z_score': '-3.1'},
    'ENSG00000233750': {'gene_id': 'ENSG00000233750', 'p_value': '0.064', 'p_adjust': '0.0000057', 'z_score': '7.8'},
 })

class DataManagerAPITest(AuthenticationTestCase):
    fixtures = ["users", "1kg_project", "reference_data"]

    @urllib3_responses.activate
    def test_elasticsearch_status(self):
        url = reverse(elasticsearch_status)
        self.check_data_manager_login(url)

        urllib3_responses.add_json(
            "/_cat/allocation?format=json&h=node,shards,disk.avail,disk.used,disk.percent",
            ES_CAT_ALLOCATION,
        )
        urllib3_responses.add_json(
            "/_cat/nodes?format=json&h=name,heap.percent", ES_CAT_NODES
        )
        urllib3_responses.add_json(
            "/_cat/indices?format=json&h=index,docs.count,store.size,creation.date.string",
            ES_CAT_INDICES,
        )
        urllib3_responses.add_json(
            "/_cat/aliases?format=json&h=alias,index", ES_CAT_ALIAS
        )
        urllib3_responses.add_json("/_all/_mapping", ES_INDEX_MAPPING)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json.keys()),
            {'indices', 'errors', 'diskStats', 'nodeStats'}
        )

        self.assertEqual(len(response_json['indices']), 6)
        self.assertDictEqual(response_json['indices'][0], TEST_INDEX_EXPECTED_DICT)
        self.assertDictEqual(response_json['indices'][3], TEST_INDEX_NO_PROJECT_EXPECTED_DICT)
        self.assertDictEqual(response_json['indices'][4], TEST_SV_INDEX_EXPECTED_DICT)

        self.assertListEqual(response_json["errors"], EXPECTED_ERRORS)

        self.assertListEqual(response_json['diskStats'], EXPECTED_DISK_ALLOCATION)
        self.assertListEqual(response_json['nodeStats'], EXPECTED_NODE_STATS)

    @urllib3_responses.activate
    def test_delete_index(self):
        url = reverse(delete_index)
        self.check_data_manager_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({'index': 'test_index'}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(),
            (
                {
                    "error": 'Index "test_index" is still used by: 1kg project n\xe5me with uni\xe7\xf8de'
                }
            ),
        )
        self.assertEqual(len(urllib3_responses.calls), 0)

        urllib3_responses.add_json(
            "/_cat/indices?format=json&h=index,docs.count,store.size,creation.date.string",
            ES_CAT_INDICES,
        )
        urllib3_responses.add_json(
            "/_cat/aliases?format=json&h=alias,index", ES_CAT_ALIAS
        )
        urllib3_responses.add_json("/_all/_mapping", ES_INDEX_MAPPING)
        urllib3_responses.add(urllib3_responses.DELETE, "/unused_index")

        response = self.client.post(
            url,
            content_type="application/json",
            data=json.dumps({"index": "unused_index"}),
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'indices'})
        self.assertEqual(len(response_json['indices']), 6)
        self.assertDictEqual(response_json['indices'][0], TEST_INDEX_EXPECTED_DICT)
        self.assertDictEqual(response_json['indices'][3], TEST_INDEX_NO_PROJECT_EXPECTED_DICT)
        self.assertDictEqual(response_json['indices'][4], TEST_SV_INDEX_EXPECTED_DICT)

        self.assertEqual(urllib3_responses.calls[0].request.method, "DELETE")


    # 2022-04-05 mfranklin: disabled because we don't have access to gs://seqr-datasets/
    # @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    # def test_upload_qc_pipeline_output(self, mock_subprocess):
    #     url = reverse(upload_qc_pipeline_output, )
    #     self.check_data_manager_login(url)
    #
    #     request_data = json.dumps({
    #         'file': ' gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/final_output/seqr_sample_qc.tsv'
    #     })
    #
    #     # Test missing file
    #     mock_does_file_exist = mock.MagicMock()
    #     mock_subprocess.side_effect = [mock_does_file_exist]
    #     mock_does_file_exist.wait.return_value = 1
    #     response = self.client.post(url, content_type='application/json', data=request_data)
    #     self.assertEqual(response.status_code, 400)
    #     self.assertListEqual(
    #         response.json()['errors'],
    #         [
    #             'File not found: gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/final_output/seqr_sample_qc.tsv'])
    #
    #     # Test missing columns
    #     mock_does_file_exist.wait.return_value = 0
    #     mock_file_iter = mock.MagicMock()
    #     mock_file_iter.stdout = [b'', b'']
    #     mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
    #     response = self.client.post(url, content_type='application/json', data=request_data)
    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(
    #         response.reason_phrase,
    #         'The following required columns are missing: seqr_id, data_type, filter_flags, qc_metrics_filters, qc_pop')
    #
    #     # Test no data type error
    #     mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
    #     mock_file_iter.stdout = SAMPLE_QC_DATA_NO_DATA_TYPE
    #     response = self.client.post(url, content_type='application/json', data=request_data)
    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(response.reason_phrase, 'No data type detected')
    #
    #     # Test multiple data types error
    #     mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
    #     mock_file_iter.stdout = SAMPLE_QC_DATA_MORE_DATA_TYPE
    #     response = self.client.post(url, content_type='application/json', data=request_data)
    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(response.reason_phrase, 'Multiple data types detected: wes ,wgs')
    #
    #     # Test unexpected data type error
    #     mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
    #     mock_file_iter.stdout = SAMPLE_QC_DATA_UNEXPECTED_DATA_TYPE
    #     response = self.client.post(url, content_type='application/json', data=request_data)
    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(response.reason_phrase,
    #                      'Unexpected data type detected: "unknown" (should be "exome" or "genome")')
    #
    #     # Test normal functions
    #     mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
    #     mock_file_iter.stdout = SAMPLE_QC_DATA
    #     response = self.client.post(url, content_type='application/json', data=request_data)
    #     self.assertEqual(response.status_code, 200)
    #     response_json = response.json()
    #     self.assertSetEqual(set(response_json.keys()), {'info', 'errors', 'warnings'})
    #     self.assertListEqual(response_json['info'], [
    #         'Parsed 6 exome samples',
    #         'Found and updated matching seqr individuals for 4 samples'
    #     ])
    #     self.assertListEqual(response_json['warnings'], [
    #         'The following 1 samples were added to multiple individuals: NA19678 (2)',
    #         'The following 2 samples were skipped: MANZ_1169_DNA, NA',
    #         'The following filter flags have no known corresponding value and were not saved: not_real_flag',
    #         'The following population platform filters have no known corresponding value and were not saved: not_real_filter'
    #     ])
    #
    #     indiv = Individual.objects.get(id=1)
    #     self.assertIsNone(indiv.filter_flags)
    #     self.assertDictEqual(indiv.pop_platform_filters,
    #                          {'n_deletion': '10898', 'n_snp': '127706', 'r_insertion_deletion': '1.2572E+00',
    #                           'r_ti_tv': '1.8292E+00', 'n_insertion': '13701'})
    #     self.assertEqual(indiv.population, 'AMR')
    #
    #     indiv = Individual.objects.get(id=2)
    #     self.assertDictEqual(indiv.filter_flags, {'coverage_exome': '8.1446E+01'})
    #     self.assertDictEqual(indiv.pop_platform_filters, {'n_insertion': '6857'})
    #     self.assertEqual(indiv.population, 'SAS')
    #
    #     indiv = Individual.objects.get(id=12)
    #     self.assertDictEqual(indiv.filter_flags, {'coverage_exome': '8.1446E+01'})
    #     self.assertDictEqual(indiv.pop_platform_filters, {'n_insertion': '6857'})
    #     self.assertEqual(indiv.population, 'SAS')
    #
    #     indiv = Individual.objects.get(id=5)
    #     self.assertDictEqual(indiv.filter_flags, {'chimera': '5.0841E+00'})
    #     self.assertDictEqual(indiv.pop_platform_filters, {'n_insertion': '29507', 'r_insertion_deletion': '1.343E+00'})
    #     self.assertEqual(indiv.population, 'NFE')
    #
    #     indiv = Individual.objects.get(id=6)
    #     self.assertDictEqual(indiv.filter_flags, {'contamination': '2.79E+00'})
    #     self.assertDictEqual(indiv.pop_platform_filters, {'n_insertion': '38051', 'r_insertion_deletion': '1.8064E+00'})
    #     self.assertEqual(indiv.population, 'OTH')

    # 2022-04-05 mfranklin: disabled because we don't have access to gs://seqr-datasets/
    # @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    # def test_upload_sv_qc(self, mock_subprocess):
    #     url = reverse(upload_qc_pipeline_output, )
    #     self.check_data_manager_login(url)
    #
    #     request_data = json.dumps({
    #         'file': 'gs://seqr-datasets/v02/GRCh38/RDG_WES_Broad_Internal/v15/sample_qc/sv/sv_sample_metadata.tsv'
    #     })
    #
    #     mock_does_file_exist = mock.MagicMock()
    #     mock_does_file_exist.wait.return_value = 0
    #     mock_file_iter = mock.MagicMock()
    #     mock_file_iter.stdout = SAMPLE_SV_WES_QC_DATA
    #     mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
    #     response = self.client.post(url, content_type='application/json', data=request_data)
    #     self.assertEqual(response.status_code, 200)
    #     response_json = response.json()
    #     self.assertSetEqual(set(response_json.keys()), {'info', 'errors', 'warnings'})
    #     self.assertListEqual(response_json['info'], [
    #         'Parsed 6 SV samples',
    #         'Found and updated matching seqr individuals for 4 samples'
    #     ])
    #     self.assertListEqual(response_json['warnings'], ['The following 2 samples were skipped: MANZ_1169_DNA, NA'])
    #
    #     self.assertIsNone(Individual.objects.get(individual_id='NA19675_1').sv_flags)
    #     self.assertListEqual(Individual.objects.get(individual_id='NA19678').sv_flags, ['high_QS_rare_calls:_>10'])
    #     self.assertListEqual(Individual.objects.get(individual_id='HG00732').sv_flags, ['raw_calls:_>100'])
    #     self.assertListEqual(
    #         Individual.objects.get(individual_id='HG00733').sv_flags,
    #         ['high_QS_rare_calls:_>10', 'raw_calls:_>100'])
    #
    #     # Test genome data
    #     mock_file_iter.stdout = SAMPLE_SV_WGS_QC_DATA
    #     mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
    #     response = self.client.post(url, content_type='application/json', data=request_data)
    #     self.assertEqual(response.status_code, 200)
    #     response_json = response.json()
    #     self.assertSetEqual(set(response_json.keys()), {'info', 'errors', 'warnings'})
    #     self.assertListEqual(response_json['info'], [
    #         'Parsed 2 SV samples',
    #         'Found and updated matching seqr individuals for 1 samples'
    #     ])
    #     self.assertListEqual(response_json['warnings'], ['The following 1 samples were skipped: NA19678'])
    #     self.assertListEqual(Individual.objects.get(individual_id='NA21234').sv_flags, ['outlier_num._calls'])
    #     # Should not overwrite existing QC flags
    #     self.assertListEqual(Individual.objects.get(individual_id='NA19678').sv_flags, ['high_QS_rare_calls:_>10'])

    @mock.patch('seqr.views.apis.data_manager_api.KIBANA_ELASTICSEARCH_PASSWORD', 'abc123')
    @mock.patch(
        "seqr.views.apis.data_manager_api.KIBANA_ELASTICSEARCH_PASSWORD", "abc123"
    )
    @responses.activate
    def test_kibana_proxy(self):
        url = "/api/kibana/random/path"
        self.check_data_manager_login(url)

        response_args = {
            "stream": True,
            "body": "Test response",
            "content_type": "text/custom",
            "headers": {"x-test-header": "test", "keep-alive": "true"},
        }
        proxy_url = "http://localhost:5601{}".format(url)
        responses.add(responses.GET, proxy_url, status=200, **response_args)
        responses.add(responses.POST, proxy_url, status=201, **response_args)
        responses.add(
            responses.GET, "{}/bad_response".format(proxy_url), body=HTTPError()
        )

        response = self.client.get(url, HTTP_TEST_HEADER="some/value")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Test response")
        self.assertEqual(response.get("content-type"), "text/custom")
        self.assertEqual(response.get("x-test-header"), "test")
        self.assertIsNone(response.get("keep-alive"))

        data = json.dumps([{"content": "Test Body"}])
        response = self.client.post(url, content_type="application/json", data=data)
        self.assertEqual(response.status_code, 201)

        self.assertEqual(len(responses.calls), 2)

        get_request = responses.calls[0].request
        self.assertEqual(get_request.headers["Host"], "localhost:5601")
        self.assertEqual(
            get_request.headers["Authorization"], "Basic a2liYW5hOmFiYzEyMw=="
        )
        self.assertEqual(get_request.headers["Test-Header"], "some/value")

        post_request = responses.calls[1].request
        self.assertEqual(post_request.headers["Host"], "localhost:5601")
        self.assertEqual(
            get_request.headers["Authorization"], "Basic a2liYW5hOmFiYzEyMw=="
        )
        self.assertEqual(post_request.headers["Content-Type"], "application/json")
        self.assertEqual(post_request.headers["Content-Length"], "26")
        self.assertEqual(post_request.body, data.encode("utf-8"))

        # Test with error response
        response = self.client.get("{}/bad_response".format(url))
        self.assertEqual(response.status_code, 500)

        # Test with connection error
        response = self.client.get("{}/bad_path".format(url))
        self.assertContains(
            response, "Error: Unable to connect to Kibana", status_code=400
        )

    @mock.patch('seqr.views.apis.data_manager_api.datetime')
    @mock.patch('seqr.views.apis.data_manager_api.open')
    def test_receive_rna_seq_table(self, mock_open, mock_datetime):
        mock_datetime.now.return_value = datetime(2021, 3, 1)
        url = reverse(receive_rna_seq_table)
        self.check_data_manager_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Received 0 files instead of 1']})

        response = self.client.post(url, {'f': SimpleUploadedFile('test.json', '')})
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors':['Invalid file extension for test.json: expected ".tsv.gz"']})

        response = self.client.post(url, {'f': SimpleUploadedFile('new_muscle_samples.tsv.gz', b'sample_content')})
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'uploadedFileId': RNA_FILE_ID, 'info': ['Loaded gzipped file new_muscle_samples.tsv.gz'],
        })
        mock_open.return_value.__enter__.return_value.write.assert_called_with(b'sample_content')

    @mock.patch('seqr.views.utils.dataset_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.apis.data_manager_api.os')
    @mock.patch('seqr.views.apis.data_manager_api.load_uploaded_file')
    @mock.patch('seqr.views.utils.dataset_utils.gzip.open')
    @mock.patch('seqr.views.utils.dataset_utils.logger')
    def test_update_rna_seq(self, mock_logger, mock_open, mock_load_uploaded_file, mock_os):
        url = reverse(update_rna_seq, args=['muscle_samples.tsv.gz'])
        self.check_data_manager_login(url)

        # Test errors
        mock_os.path.join.side_effect = lambda *args: '/'.join(args[1:])
        mock_load_uploaded_file.return_value = [['a']]
        mock_file = mock_open.return_value.__enter__.return_value
        mock_file.__next__.return_value = 'geneID\tdetail\tpValue'
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Invalid file: missing column(s) sampleID, padjust, zScore'})

        mock_file.__next__.return_value = 'sampleID\tgeneID\tdetail\tpValue\tpadjust\tzScore\n'
        mock_file.__iter__.return_value = [
            'NA19675_D2\tENSG00000240361\tdetail1\t0.01\t0.001\t-3.1\n',
            'NA19675_D2\tENSG00000240361\tdetail2\t0.01\t0.001\t-5.1\n',
        ]
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': mock.ANY})
        self.assertTrue(response.json()['error'].startswith(
            'Error in NA19675_D2 data for ENSG00000240361: mismatched entries '))

        mock_file.__iter__.return_value = [
            'NA19675_D2\tENSG00000240361\tdetail1\t0.01\t0.001\t-3.1\n',
            'NA19675_D3\tENSG00000240361\tdetail2\t0.01\t0.001\t-3.1\n',
        ]
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Unable to find matches for the following samples: NA19675_D3'})

        response = self.client.post(url, content_type='application/json', data=json.dumps(
            {'mappingFile': {'uploadedFileId': 'map.tsv'}}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Must contain 2 columns. Received 1 columns on line #1: a'})

        # Test already loaded data
        mock_file.__iter__.return_value = [
            'NA19675_D2\tENSG00000240361\tdetail1\t0.01\t0.001\t-3.1\n',
        ]
        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 200)
        info = [
            'Parsed 1 RNA-seq samples',
            'Attempted data loading for 0 RNA-seq samples in the following 0 projects: ',
        ]
        warnings = ['Skipped loading for 1 samples already loaded from this file']
        self.assertDictEqual(response.json(), {'info': info, 'warnings': warnings, 'sampleGuids': []})
        mock_logger.info.assert_has_calls([mock.call(info_log, self.data_manager_user) for info_log in info])
        mock_logger.warning.assert_has_calls([mock.call(warn_log, self.data_manager_user) for warn_log in warnings])
        self.assertEqual(RnaSeqOutlier.objects.count(), 3)

        # Test loading new data
        url = reverse(update_rna_seq, args=[RNA_FILE_ID])
        mock_open.reset_mock()
        mock_logger.reset_mock()
        mock_file.__iter__.return_value = [
            'NA19675_D2\tENSG00000240361\tdetail1\t0.01\t0.13\t-3.1\n',
            'NA19675_D2\tENSG00000240361\tdetail2\t0.01\t0.13\t-3.1\n',
            'NA19675_D2\tENSG00000233750\tdetail1\t0.064\t0.0000057\t7.8\n',
            'NA19675_D3\tENSG00000233750\tdetail1\t0.064\t0.0000057\t7.8\n',
        ]
        mock_load_uploaded_file.return_value = [['NA19675_D2', 'NA19675_1']]
        mock_writes = []
        def mock_write(content):
            mock_writes.append(content)
        mock_open.return_value.__enter__.return_value.write.side_effect = mock_write
        response = self.client.post(url, content_type='application/json', data=json.dumps(
               {'ignoreExtraSamples': True, 'mappingFile': {'uploadedFileId': 'map.tsv'}}))
        self.assertEqual(response.status_code, 200)
        info = [
            'Parsed 2 RNA-seq samples',
            'Attempted data loading for 1 RNA-seq samples in the following 1 projects: 1kg project nåme with uniçøde',
        ]
        warnings = ['Skipped loading for the following 1 unmatched samples: NA19675_D3']
        response_json = response.json()
        self.assertDictEqual(response_json, {'info': info, 'warnings': warnings, 'sampleGuids': [mock.ANY]})
        mock_logger.info.assert_has_calls(
            [mock.call(info_log, self.data_manager_user) for info_log in info] + [
                mock.call('delete 3 RnaSeqOutliers', self.data_manager_user, db_update={
                    'dbEntity': 'RnaSeqOutlier', 'numEntities': 3, 'parentEntityIds': [RNA_SAMPLE_GUID], 'updateType': 'bulk_delete',
                }),
            ], any_order=True
        )
        mock_logger.warning.assert_has_calls([mock.call(warn_log, self.data_manager_user) for warn_log in warnings])

        # test database models are correct
        self.assertEqual(RnaSeqOutlier.objects.count(), 0)
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
        mock_open.assert_any_call(RNA_FILE_ID, 'rt')
        mock_open.assert_called_with(f'rna_sample_data/{sample.guid}.json.gz', 'wt')
        self.assertEqual(''.join(mock_writes), RNA_SAMPLE_DATA)
        mock_os.remove.assert_called_with(RNA_FILE_ID)

    @mock.patch('seqr.views.apis.data_manager_api.os')
    @mock.patch('seqr.views.apis.data_manager_api.gzip.open')
    @mock.patch('seqr.views.apis.data_manager_api.logger')
    def test_load_rna_seq_sample_data(self, mock_logger, mock_open, mock_os):
        RnaSeqOutlier.objects.all().delete()
        mock_os.path.join.side_effect = lambda *args: '/'.join(args[1:])
        mock_open.return_value.__enter__.return_value.read.return_value = RNA_SAMPLE_DATA

        url = reverse(load_rna_seq_sample_data, args=[RNA_SAMPLE_GUID])
        self.check_data_manager_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': True})

        models = RnaSeqOutlier.objects.all()
        self.assertEqual(models.count(), 2)
        self.assertSetEqual({model.sample.guid for model in models}, {RNA_SAMPLE_GUID})
        self.assertListEqual(get_json_for_rna_seq_outliers(models), [
            {'geneId': 'ENSG00000240361', 'pAdjust': 0.13, 'pValue': 0.01, 'zScore': -3.1, 'isSignificant': False},
            {'geneId': 'ENSG00000233750', 'pAdjust': 0.0000057, 'pValue': 0.064, 'zScore': 7.8,'isSignificant': True},
        ])

        file_name = f'rna_sample_data/{RNA_SAMPLE_GUID}.json.gz'
        mock_open.assert_called_with(file_name, 'rt')
        mock_os.remove.assert_called_with(file_name)

        mock_logger.info.assert_has_calls([
            mock.call('Loading outlier data for NA19675_D2', self.data_manager_user),
            mock.call('create 2 RnaSeqOutliers', self.data_manager_user, db_update={
                'dbEntity': 'RnaSeqOutlier', 'numEntities': 2, 'parentEntityIds': [RNA_SAMPLE_GUID], 'updateType': 'bulk_create',
            }),
        ])
