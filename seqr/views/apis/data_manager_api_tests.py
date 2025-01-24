from collections import defaultdict
from datetime import datetime
from django.urls.base import reverse
import json
import mock
from requests import HTTPError
import responses

from seqr.utils.communication_utils import _set_bulk_notification_stream
from seqr.views.apis.data_manager_api import elasticsearch_status, upload_qc_pipeline_output, delete_index, \
    update_rna_seq, load_rna_seq_sample_data, load_phenotype_prioritization_data, validate_callset, loading_vcfs, \
    get_loaded_projects, load_data
from seqr.views.utils.orm_to_json_utils import _get_json_for_models
from seqr.views.utils.test_utils import AuthenticationTestCase, AirflowTestCase, AirtableTest
from seqr.utils.search.elasticsearch.es_utils_tests import urllib3_responses
from seqr.models import Individual, RnaSeqOutlier, RnaSeqTpm, RnaSeqSpliceOutlier, RnaSample, Project, PhenotypePrioritization
from settings import SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL

PROJECT_GUID = 'R0001_1kg'
NON_ANALYST_PROJECT_GUID = 'R0004_non_analyst_project'

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

RNA_TPM_MUSCLE_SAMPLE_GUID = 'RS000162_T_na19675_d2'
RNA_OUTLIER_MUSCLE_SAMPLE_GUID = 'RS000172_E_na19675_d2'
RNA_SPLICE_SAMPLE_GUID = 'RS000151_S_na19675_1'
PLACEHOLDER_GUID = 'S0000100'
RNA_FILE_ID = 'gs://rna_data/new_muscle_samples.tsv.gz'
SAMPLE_GENE_OUTLIER_DATA = [
    {'gene_id': 'ENSG00000240361', 'p_value': '0.01', 'p_adjust': '0.13', 'z_score': '-3.1'},
    {'gene_id': 'ENSG00000240361', 'p_value': '0.01', 'p_adjust': '0.13', 'z_score': '-3.1'},
    {'gene_id': 'ENSG00000233750', 'p_value': '0.064', 'p_adjust': '0.0000057', 'z_score': '7.8'},
]
SAMPLE_GENE_TPM_DATA = [
    {'gene_id': 'ENSG00000240361', 'tpm': '7.8'},
    {'gene_id': 'ENSG00000233750', 'tpm': '0.0'},
]
SAMPLE_GENE_SPLICE_DATA = [
    {
        'chrom': 'chr2', 'start': '167254166', 'end': '167258349', 'strand': '*', 'type': 'psi3',
        'p_value': '1.56e-25', 'p_adjust': '-4.9', 'delta_intron_jaccard_index': '-0.46', 'counts': '166',
        'mean_counts': '16.6', 'total_counts': '1660', 'mean_total_counts': '1.66',
        'rare_disease_samples_with_this_junction': '1', 'rare_disease_samples_total': '20', 'gene_id': 'ENSG00000233750',
    },
    {
        'chrom': 'chr2', 'start': '167254166', 'end': '167258349', 'strand': '*', 'type': 'psi3',
        'p_value': '1.56e-25', 'p_adjust': '-4.9', 'delta_intron_jaccard_index': '-0.46', 'counts': '166',
        'mean_counts': '16.6', 'total_counts': '1660', 'mean_total_counts': '1.66',
        'rare_disease_samples_with_this_junction': '1', 'rare_disease_samples_total': '20', 'gene_id': 'ENSG00000240361',
    },
    {
        'chrom': 'chr7', 'start': '132885746', 'end': '132975168', 'strand': '*', 'type': 'psi5',
        'p_value': '1.08e-56', 'p_adjust': '-6.53', 'delta_intron_jaccard_index': '-0.85', 'counts': '231',
        'mean_counts': '0.231', 'total_counts': '2313', 'mean_total_counts': '231.3',
        'rare_disease_samples_with_this_junction': '1', 'rare_disease_samples_total': '20', 'gene_id': 'ENSG00000240361',
    },
]
SAMPLE_GENE_SPLICE_DATA2 = {
        'chrom': 'chr2', 'start': '167258096', 'end': '167258349', 'strand': '*', 'type': 'psi3',
        'p_value': '1.56e-25', 'p_adjust': '6.33', 'delta_intron_jaccard_index': '0.45', 'counts': '143',
        'mean_counts': '14.3', 'total_counts': '1433', 'mean_total_counts': '143.3',
        'rare_disease_samples_with_this_junction': '1', 'rare_disease_samples_total': '20', 'gene_id': '',
    }
RNA_OUTLIER_SAMPLE_DATA = {
    RNA_OUTLIER_MUSCLE_SAMPLE_GUID: '\n'.join([json.dumps(row) for row in SAMPLE_GENE_OUTLIER_DATA]) + '\n',
    PLACEHOLDER_GUID: json.dumps({'gene_id': 'ENSG00000240361', 'p_value': '0.04', 'p_adjust': '0.112', 'z_score': '1.9'}) + '\n',
}
RNA_TPM_SAMPLE_DATA = {
    RNA_TPM_MUSCLE_SAMPLE_GUID: '\n'.join([json.dumps(row) for row in SAMPLE_GENE_TPM_DATA]) + '\n',
    PLACEHOLDER_GUID: json.dumps({'gene_id': 'ENSG00000240361', 'tpm': '0.112'}) + '\n',
}
RNA_SPLICE_SAMPLE_DATA = {
    RNA_SPLICE_SAMPLE_GUID: '\n'.join([json.dumps(row) for row in SAMPLE_GENE_SPLICE_DATA]) + '\n',
    PLACEHOLDER_GUID: json.dumps(SAMPLE_GENE_SPLICE_DATA2) + '\n',
}
RNA_FILENAME_TEMPLATE = 'rna_sample_data__{}__2020-04-15T00:00:00'

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

PEDIGREE_HEADER = ['Project_GUID', 'Family_GUID', 'Family_ID', 'Individual_ID', 'Paternal_ID', 'Maternal_ID', 'Sex']
EXPECTED_PEDIGREE_ROWS = [
    ['R0001_1kg', 'F000001_1', '1', 'NA19675_1', 'NA19678', 'NA19679', 'XXY'],
    ['R0001_1kg', 'F000001_1', '1', 'NA19678', '', '', 'M'],
    ['R0001_1kg', 'F000001_1', '1', 'NA19679', '', '', 'F'],
    ['R0001_1kg', 'F000002_2', '2', 'HG00731', 'HG00732', 'HG00733', 'X0'],
]

PROJECT_OPTION = {
    'dataTypeLastLoaded': None,
    'name': 'Non-Analyst Project',
    'projectGuid': 'R0004_non_analyst_project',
}
PROJECT_SAMPLES_OPTION = {**PROJECT_OPTION, 'sampleIds': ['NA21234', 'NA21987']}
EMPTY_PROJECT_OPTION = {
    'dataTypeLastLoaded': None,
    'name': 'Empty Project',
    'projectGuid': 'R0002_empty',
}
EMPTY_PROJECT_SAMPLES_OPTION = {**EMPTY_PROJECT_OPTION, 'sampleIds': ['HG00738', 'HG00739']}

AIRTABLE_SAMPLE_RECORDS = {
    'records': [
        {
            'id': 'recW24C2CJW5lT64K',
            'fields': {
                'SeqrProject': ['https://seqr.broadinstitute.org/project/R0002_empty/project_page'],
                'PDOStatus': ['Methods (Loading)'],
                'CollaboratorSampleID': 'HG00738',
            }
        },
        {
            'id': 'recW24C2CJW5lT64L',
            'fields': {
                'SeqrProject': ['https://seqr.broadinstitute.org/project/R0002_empty/project_page'],
                'PDOStatus': ['Methods (Loading)'],
                'SeqrCollaboratorSampleID': 'HG00739',
            }
        },
        {
            'id': 'rec2B6OGmQpAkQW3s',
            'fields': {
                'SeqrProject': [
                    'https://seqr.broadinstitute.org/project/R0002_empty/project_page',
                    'https://seqr.broadinstitute.org/project/R0004_non_analyst_project/project_page',
                ],
                'PDOStatus': ['Historic', 'Methods (Loading)'],
                'CollaboratorSampleID': 'NA21234',
            }
        },
        {
            'id': 'rec2B6OGmQpAkQW7s',
            'fields': {
                'SeqrProject': ['https://seqr.broadinstitute.org/project/R0004_non_analyst_project/project_page'],
                'PDOStatus': ['Methods (Loading)'],
                'CollaboratorSampleID': 'NA21987',
            }
        },
        {
            'id': 'recW24C2CJW5lT67K',
            'fields': {
                'CollaboratorSampleID': 'NA19678',
                'SeqrProject': ['https://seqr.broadinstitute.org/project/R0001_1kg/project_page'],
                'PDOStatus': ['Available in seqr'],
            }
        },
        {
            'id': 'recW24C2CJW5lT65K',
            'fields': {
                'CollaboratorSampleID': 'HG00731',
                'SeqrProject': ['https://seqr.broadinstitute.org/project/R0001_1kg/project_page'],
                'PDOStatus': ['Available in seqr'],
            }
        },
    ],
}

PIPELINE_RUNNER_URL = 'http://pipeline-runner:6000/loading_pipeline_enqueue'


@mock.patch('seqr.views.apis.data_manager_api.LOADING_DATASETS_DIR', '/local_datasets')
@mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
class DataManagerAPITest(AirtableTest):

    PROJECTS = [PROJECT_GUID, NON_ANALYST_PROJECT_GUID]

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
        self._assert_expected_es_status(response)

    def _assert_expected_es_status(self, response):
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
        self.assertEqual(
            response.json()['error'], '"test_index" is still used by: 1kg project n\xe5me with uni\xe7\xf8de')
        self.assertEqual(len(urllib3_responses.calls), 0)

        urllib3_responses.add_json(
            '/_cat/indices?format=json&h=index,docs.count,store.size,creation.date.string', ES_CAT_INDICES)
        urllib3_responses.add_json('/_cat/aliases?format=json&h=alias,index', ES_CAT_ALIAS)
        urllib3_responses.add_json('/_all/_mapping', ES_INDEX_MAPPING)
        urllib3_responses.add(urllib3_responses.DELETE, '/unused_index')

        response = self.client.post(url, content_type='application/json', data=json.dumps({'index': 'unused_index'}))
        self._assert_expected_delete_index_response(response)

    def _assert_expected_delete_index_response(self, response):
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

        self._test_request_proxy('localhost:5601', url, auth_header='Basic a2liYW5hOmFiYzEyMw==')

        # Test with error response
        response = self.client.get('{}/bad_response'.format(url))
        self.assertEqual(response.status_code, 500)

        # Test with connection error
        response = self.client.get('{}/bad_path'.format(url))
        self.assertContains(response, 'Error: Unable to connect to Kibana', status_code=400)

    def _test_request_proxy(self, host, url, auth_header=None, proxy_path=None):
        response_args = {
            'stream': True,
            'body': 'Test response',
            'content_type': 'text/custom',
            'headers': {'x-test-header': 'test', 'keep-alive': 'true'},
        }
        proxy_url = f'http://{host}{proxy_path or url}'
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
        self.assertEqual(get_request.headers['Host'], host)
        self.assertEqual(get_request.headers['Test-Header'], 'some/value')
        if auth_header:
            self.assertEqual(get_request.headers['Authorization'], auth_header)
        else:
            self.assertFalse('Authorization' in get_request.headers)

        post_request = responses.calls[1].request
        self.assertEqual(post_request.headers['Host'], host)
        self.assertEqual(post_request.headers['Content-Type'], 'application/json')
        self.assertEqual(post_request.headers['Content-Length'], '26')
        self.assertEqual(post_request.body, data.encode('utf-8'))
        if auth_header:
            self.assertEqual(get_request.headers['Authorization'], auth_header)
        else:
            self.assertFalse('Authorization' in get_request.headers)

    @mock.patch('seqr.views.apis.data_manager_api.LUIGI_UI_SERVICE_HOSTNAME')
    @responses.activate
    def test_luigi_proxy(self, mock_hostname):
        mock_hostname.__bool__.return_value = False

        url = '/luigi_ui/api/task_list'
        self.check_data_manager_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, b'Loading Pipeline UI is not configured')

        mock_hostname.__str__.return_value = 'pipeline-runner-ui'
        mock_hostname.__bool__.return_value = True

        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Error: Unable to connect to Luigi UI', status_code=400)

        responses.calls.reset()
        self._test_request_proxy('pipeline-runner-ui:8082', url, proxy_path='/api/task_list')

    RNA_DATA_TYPE_PARAMS = {
        'outlier': {
            'model_cls': RnaSeqOutlier,
            'data_type': 'E',
            'message_data_type': 'Expression Outlier',
            'header': ['sampleID', 'project', 'geneID', 'tissue', 'detail', 'pValue', 'padjust', 'zScore'],
            'optional_headers': ['detail'],
            'loaded_data_row': ['NA19675_D2', '1kg project nåme with uniçøde', 'ENSG00000240361', 'muscle', 'detail1', 0.01, 0.001, -3.1],
            'no_existing_data': ['NA19678', '1kg project nåme with uniçøde', 'ENSG00000233750', 'muscle', 'detail1', 0.064, '0.0000057', 7.8],
            'duplicated_indiv_id_data': [
                ['NA20870', 'Test Reprocessed Project', 'ENSG00000233750', 'muscle', 'detail1', 0.064, '0.0000057', 7.8],
                ['NA20870', '1kg project nåme with uniçøde', 'ENSG00000240361', 'fibroblasts', 'detail2', 0.01, 0.13, -3.1],
            ],
            'write_data': {
                '{"gene_id": "ENSG00000233750", "p_value": "0.064", "p_adjust": "0.0000057", "z_score": "7.8"}\n',
                '{"gene_id": "ENSG00000240361", "p_value": "0.01", "p_adjust": "0.13", "z_score": "-3.1"}\n'
            },
            'new_data': [
                ['NA19675_D2', '1kg project nåme with uniçøde', 'ENSG00000240361', 'muscle', 'detail1', 0.01, 0.13, -3.1],
                ['NA19675_D2', '1kg project nåme with uniçøde', 'ENSG00000240361', 'muscle', 'detail2', 0.01, 0.13, -3.1],
                ['NA19675_D2', '1kg project nåme with uniçøde', 'ENSG00000233750', 'muscle', 'detail1', 0.064, '0.0000057', 7.8],
                ['NA19675_D3', 'Test Reprocessed Project', 'ENSG00000233750', 'muscle', 'detail1', 0.064, '0.0000057', 7.8],
                ['NA20888', 'Test Reprocessed Project', 'ENSG00000240361', 'muscle', '', 0.04, 0.112, 1.9],
            ],
            'skipped_samples': 'NA19675_D3 (Test Reprocessed Project)',
            'sample_tissue_type': 'M',
            'num_parsed_samples': 3,
            'initial_model_count': 3,
            'parsed_file_data': RNA_OUTLIER_SAMPLE_DATA,
            'get_models_json': lambda models: list(models.values_list('gene_id', 'p_adjust', 'p_value', 'z_score')),
            'expected_models_json': [
                ('ENSG00000240361', 0.13, 0.01, -3.1), ('ENSG00000233750', 0.0000057, 0.064, 7.8),
            ],
            'sample_guid': RNA_OUTLIER_MUSCLE_SAMPLE_GUID,
        },
        'tpm': {
            'model_cls': RnaSeqTpm,
            'data_type': 'T',
            'message_data_type': 'Expression',
            'header': ['sample_id', 'project', 'gene_id', 'individual_id', 'tissue', 'TPM'],
            'optional_headers': ['individual_id'],
            'loaded_data_row': ['NA19675_D2', '1kg project nåme with uniçøde', 'ENSG00000135953', 'NA19675_D3', 'muscle', 1.34],
            'no_existing_data': ['NA19678', '1kg project nåme with uniçøde', 'ENSG00000233750', 'NA19678', 'muscle', 0.064],
            'duplicated_indiv_id_data': [
                ['NA20870', 'Test Reprocessed Project', 'ENSG00000240361', 'NA20870', 'muscle', 7.8],
                ['NA20870', '1kg project nåme with uniçøde', 'ENSG00000233750', 'NA20870', 'fibroblasts', 0.0],
            ],
            'write_data': {'{"gene_id": "ENSG00000240361", "tpm": "7.8"}\n',
                           '{"gene_id": "ENSG00000233750", "tpm": "0.0"}\n'},
            'new_data': [
                # existing sample NA19675_D2
                ['NA19675_D2', '1kg project nåme with uniçøde', 'ENSG00000240361', 'NA19675_D2', 'muscle', 7.8],
                ['NA19675_D2', '1kg project nåme with uniçøde', 'ENSG00000233750', 'NA19675_D2', 'muscle', 0.0],
                # no matched individual NA19675_D3
                ['NA19675_D3', '1kg project nåme with uniçøde', 'ENSG00000233750', 'NA19675_D3', 'fibroblasts', 0.064],
                # a different project sample NA20888
                ['NA20888', 'Test Reprocessed Project', 'ENSG00000240361', 'NA20888', 'muscle', 0.112],
                # a project mismatched sample NA20878
                ['NA20878', 'Test Reprocessed Project', 'ENSG00000233750', 'NA20878', 'fibroblasts', 0.064],
            ],
            'skipped_samples': 'NA19675_D3 (1kg project nåme with uniçøde), NA20878 (Test Reprocessed Project)',
            'sample_tissue_type': 'M',
            'num_parsed_samples': 4,
            'initial_model_count': 4,
            'deleted_count': 3,
            'parsed_file_data': RNA_TPM_SAMPLE_DATA,
            'get_models_json': lambda models: list(models.values_list('gene_id', 'tpm')),
            'expected_models_json': [('ENSG00000240361', 7.8), ('ENSG00000233750', 0.0)],
            'sample_guid': RNA_TPM_MUSCLE_SAMPLE_GUID,
            'mismatch_field': 'tpm',
        },
        'splice_outlier': {
            'model_cls': RnaSeqSpliceOutlier,
            'data_type': 'S',
            'message_data_type': 'Splice Outlier',
            'header': ['sampleID', 'projectName', 'geneID', 'chrom', 'start', 'end', 'strand', 'type', 'pValue', 'pAdjust',
                       'deltaIntronJaccardIndex', 'counts', 'meanCounts', 'totalCounts', 'meanTotalCounts', 'tissue', 'rareDiseaseSamplesWithThisJunction',
                       'rareDiseaseSamplesTotal'],
            'optional_headers': [],
            'loaded_data_row': ['NA19675_1', '1kg project nåme with uniçøde', 'ENSG00000240361', 'chr7', 132885746, 132886973, '*',
                                'psi5', 1.08E-56, 3.08E-56, 12.34, 1297, 197, 129, 1297, 'fibroblasts', 0.53953638, 1, 20],
            'no_existing_data': ['NA19678', '1kg project nåme with uniçøde', 'ENSG00000240361', 'chr7', 132885746, 132886973, '*',
                                'psi5', 1.08E-56, 3.08E-56, 12.34, 1297, 197, 129, 1297, 'fibroblasts', 0.53953638, 1, 20],
            'duplicated_indiv_id_data': [
                ['NA20870', 'Test Reprocessed Project', 'ENSG00000233750', 'chr2', 167258096, 167258349, '*',
                 'psi3', 1.56E-25, 6.33, 0.45, 143, 143, 143, 143, 'fibroblasts', 1, 20],
                ['NA20870', '1kg project nåme with uniçøde', 'ENSG00000135953', 'chr2', 167258096, 167258349, '*',
                 'psi3', 1.56E-25, 6.33, 0.45, 143, 143, 143, 143, 'muscle', 1, 20],
            ],
            'write_data': {'{"chrom": "chr2", "start": "167258096",'
                           ' "end": "167258349", "strand": "*", "type": "psi3", "p_value": "1.56e-25", "p_adjust": "6.33",'
                           ' "delta_intron_jaccard_index": "0.45", "counts": "143",'
                           ' "mean_counts": "143", "total_counts": "143", "mean_total_counts": "143",'
                           ' "rare_disease_samples_with_this_junction": "1", "rare_disease_samples_total": "20", "gene_id": "ENSG00000233750"}\n',
                           '{"chrom": "chr2", "start": "167258096",'
                           ' "end": "167258349", "strand": "*", "type": "psi3", "p_value": "1.56e-25", "p_adjust": "6.33",'
                           ' "delta_intron_jaccard_index": "0.45", "counts": "143",'
                           ' "mean_counts": "143", "total_counts": "143", "mean_total_counts": "143",'
                           ' "rare_disease_samples_with_this_junction": "1", "rare_disease_samples_total": "20", "gene_id": "ENSG00000135953"}\n',
            },
            'new_data': [
                # existing sample NA19675_1
                ['NA19675_1', '1kg project nåme with uniçøde', 'ENSG00000233750;ENSG00000240361', 'chr2', 167254166, 167258349, '*', 'psi3',
                 1.56E-25, -4.9, -0.46, 166, 16.6, 1660, 1.66, 'fibroblasts', 1, 20],
                ['NA19675_1', '1kg project nåme with uniçøde', 'ENSG00000240361', 'chr7', 132885746, 132975168, '*', 'psi5',
                 1.08E-56, -6.53, -0.85, 231, 0.231, 2313, 231.3, 'fibroblasts', 1, 20],
                # no matched individual NA19675_D3
                ['NA19675_D3', '1kg project nåme with uniçøde', 'ENSG00000233750', 'chr2', 167258096, 167258349, '*',
                 'psi3', 1.56E-25, 6.33, 0.45, 143, 14.3, 1433, 143.3, 'muscle', 1, 20],
                # a new sample NA20888
                ['NA20888', 'Test Reprocessed Project', '', 'chr2', 167258096, 167258349, '*',
                 'psi3', 1.56E-25, 6.33, 0.45, 143, 14.3, 1433, 143.3, 'fibroblasts', 1, 20],
                # a project mismatched sample NA20878
                ['NA20878', 'Test Reprocessed Project', 'ENSG00000233750', 'chr2', 167258096, 167258349, '*', 'psi3',
                 1.56E-25, 6.33, 0.45, 143, 14.3, 1433, 143.3, 'fibroblasts', 1, 20],
            ],
            'skipped_samples': 'NA19675_D3 (1kg project nåme with uniçøde), NA20878 (Test Reprocessed Project)',
            'sample_tissue_type': 'F',
            'num_parsed_samples': 4,
            'initial_model_count': 7,
            'deleted_count': 4,
            'parsed_file_data': RNA_SPLICE_SAMPLE_DATA,
            'allow_missing_gene': True,
            'get_models_json': lambda models: list(
                models.values_list('gene_id', 'chrom', 'start', 'end', 'strand', 'type', 'p_value', 'p_adjust', 'delta_intron_jaccard_index',
                                   'counts', 'rare_disease_samples_with_this_junction', 'rare_disease_samples_total')),
            'expected_models_json': [
                ('ENSG00000233750', '2', 167254166, 167258349, '*', 'psi3', 1.56e-25, -4.9, -0.46, 166, 1, 20),
                ('ENSG00000240361', '2', 167254166, 167258349, '*', 'psi3', 1.56e-25, -4.9, -0.46, 166, 1, 20),
                ('ENSG00000240361', '7', 132885746, 132975168, '*', 'psi5', 1.08e-56, -6.53, -0.85, 231, 1, 20)
            ],
            'sample_guid': RNA_SPLICE_SAMPLE_GUID,
            'row_id': 'ENSG00000233750-2-167254166-167258349-*-psi3',
        },
    }

    def _has_expected_file_loading_logs(self, file, user, info=None, warnings=None, additional_logs=None, additional_logs_offset=None):
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

        self.assert_json_logs(user, expected_logs)

    def _check_rna_sample_model(self, individual_id, data_source, data_type, tissue_type, is_active_sample=True):
        rna_samples = RnaSample.objects.filter(
            individual_id=individual_id, tissue_type=tissue_type, data_source=data_source, data_type=data_type,
        )
        self.assertEqual(len(rna_samples), 1)
        sample = rna_samples.first()
        self.assertEqual(sample.is_active, is_active_sample)
        self.assertEqual(sample.tissue_type, tissue_type)
        return sample.guid

    def test_update_rna_outlier(self, *args, **kwargs):
        self._test_update_rna_seq('outlier', *args, **kwargs)

    def test_update_rna_tpm(self, *args, **kwargs):
        self._test_update_rna_seq('tpm', *args, **kwargs)

    def test_update_rna_splice_outlier(self, *args, **kwargs):
        self._test_update_rna_seq('splice_outlier', *args, **kwargs)

    @mock.patch('seqr.utils.communication_utils.BASE_URL', 'https://test-seqr.org/')
    @mock.patch('seqr.views.utils.dataset_utils.SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL', 'seqr-data-loading')
    @mock.patch('seqr.views.utils.file_utils.tempfile.gettempdir', lambda: 'tmp/')
    @mock.patch('seqr.utils.communication_utils.send_html_email')
    @mock.patch('seqr.utils.communication_utils.safe_post_to_slack')
    @mock.patch('seqr.views.apis.data_manager_api.datetime')
    @mock.patch('seqr.views.apis.data_manager_api.os.mkdir')
    @mock.patch('seqr.views.apis.data_manager_api.os.rename')
    @mock.patch('seqr.views.apis.data_manager_api.load_uploaded_file')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    @mock.patch('seqr.views.apis.data_manager_api.gzip.open')
    def _test_update_rna_seq(self, data_type, mock_open, mock_subprocess, mock_load_uploaded_file,
                            mock_rename, mock_mkdir, mock_datetime, mock_send_slack, mock_send_email):
        url = reverse(update_rna_seq)
        self.check_pm_login(url)

        params = self.RNA_DATA_TYPE_PARAMS[data_type]
        model_cls = params['model_cls']
        header = params['header']
        loaded_data_row = params['loaded_data_row']

        # Test errors
        body = {'dataType': data_type, 'file': 'gs://rna_data/muscle_samples.tsv'}
        mock_datetime.now.return_value = datetime(2020, 4, 15)
        mock_load_uploaded_file.return_value = [['a']]
        mock_load_uploaded_file.return_value = [['a']]
        mock_does_file_exist = mock.MagicMock()
        mock_does_file_exist.wait.return_value = 1
        mock_subprocess.side_effect = [mock_does_file_exist]
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'File not found: gs://rna_data/muscle_samples.tsv'})

        mock_does_file_exist.wait.return_value = 0
        mock_file_iter = mock.MagicMock()
        def _set_file_iter_stdout(rows):
            mock_file_iter.stdout = [('\t'.join([str(col) for col in row]) + '\n').encode() for row in rows]
            mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter, mock_does_file_exist]

        _set_file_iter_stdout([])
        invalid_body = {**body, 'file': body['file'].replace('tsv', 'xlsx')}
        response = self.client.post(url, content_type='application/json', data=json.dumps(invalid_body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(), {'error': 'Unexpected iterated file type: gs://rna_data/muscle_samples.xlsx'})

        _set_file_iter_stdout([['']])
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'error': f'Invalid file: missing column(s): '
                     f'{", ".join(sorted([col for col in header if col not in params["optional_headers"]]))}',
        })

        mapping_body = {'mappingFile': {'uploadedFileId': 'map.tsv'}}
        body.update(mapping_body)
        mock_subprocess.side_effect = [mock_does_file_exist, mock_file_iter]
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Must contain 2 columns: a'})

        mock_load_uploaded_file.return_value = [['NA19675_D2', 'NA19675_1']]
        missing_sample_row = ['NA19675_D3'] + loaded_data_row[1:]
        _set_file_iter_stdout([header, loaded_data_row, missing_sample_row])
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': ['Unable to find matches for the following samples: NA19675_D3 (1kg project nåme with uniçøde)'], 'warnings': None})

        unknown_gene_id_row1 = loaded_data_row[:2] + ['NOT_A_GENE_ID1'] + loaded_data_row[3:]
        unknown_gene_id_row2 = loaded_data_row[:2] + ['NOT_A_GENE_ID2'] + loaded_data_row[3:]
        _set_file_iter_stdout([header, unknown_gene_id_row1, unknown_gene_id_row2])
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['errors'][0], 'Unknown Gene IDs: NOT_A_GENE_ID1, NOT_A_GENE_ID2')

        if not params.get('allow_missing_gene'):
            _set_file_iter_stdout([header, loaded_data_row[:2] + [''] + loaded_data_row[3:]])
            response = self.client.post(url, content_type='application/json', data=json.dumps(body))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['errors'][0], 'Samples missing required "gene_id": NA19675_D2')

        # Test already loaded data
        mock_send_slack.reset_mock()
        mock_subprocess.reset_mock()
        self.reset_logs()
        _set_file_iter_stdout([header, loaded_data_row])
        body['file'] = 'gs://rna_data/muscle_samples.tsv.gz'
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        info = [
            'Parsed 1 RNA-seq samples',
            'Attempted data loading for 0 RNA-seq samples in the following 0 projects: ',
        ]
        warnings = ['Skipped loading for 1 samples already loaded from this file']
        self.assertDictEqual(response.json(), {'info': info, 'warnings': warnings, 'sampleGuids': [], 'fileName': mock.ANY})
        self._has_expected_file_loading_logs('gs://rna_data/muscle_samples.tsv.gz', info=info, warnings=warnings, user=self.pm_user)
        self.assertEqual(model_cls.objects.count(), params['initial_model_count'])
        mock_send_slack.assert_not_called()
        mock_send_email.assert_not_called()
        self.assertEqual(mock_subprocess.call_count, 2)
        mock_subprocess.assert_has_calls([mock.call(command, stdout=-1, stderr=-2, shell=True) for command in [  # nosec
            f'gsutil ls {body["file"]}',
            f'gsutil cat {body["file"]} | gunzip -c -q - ',
        ]])

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
                individual_id=new_sample_individual_id, data_source='new_muscle_samples.tsv.gz', data_type=params['data_type'],
                tissue_type=params.get('sample_tissue_type'), is_active_sample=False,
            )
            self.assertTrue(new_sample_guid in response_json['sampleGuids'])
            additional_logs = [(f'create {num_created_samples} RnaSamples', {'dbUpdate': {
                'dbEntity': 'RnaSample', 'updateType': 'bulk_create',
                'entityIds': response_json['sampleGuids'] if num_created_samples > 1 else [new_sample_guid],
            }})] + (additional_logs or [])
            self._has_expected_file_loading_logs(
                'gs://rna_data/new_muscle_samples.tsv.gz', info=info, warnings=warnings, user=self.pm_user,
                additional_logs=additional_logs, additional_logs_offset=2)

            return response_json, new_sample_guid

        # Test loading new data
        mock_open.reset_mock()
        mock_subprocess.reset_mock()
        self.reset_logs()
        mock_files = defaultdict(mock.MagicMock)
        mock_open.side_effect = lambda file_name, *args: mock_files[file_name]
        body.update({'ignoreExtraSamples': True, 'mappingFile': {'uploadedFileId': 'map.tsv'}, 'file': RNA_FILE_ID})
        warnings = [
            f'Skipped loading for the following {len(params["skipped_samples"].split(","))} '
            f'unmatched samples: {params["skipped_samples"]}']
        deleted_count = params.get('deleted_count', params['initial_model_count'])
        response_json, new_sample_guid = _test_basic_data_loading(
            params['new_data'], params["num_parsed_samples"], 2, 16, body,
            '1kg project nåme with uniçøde, Test Reprocessed Project', warnings=warnings, num_created_samples=2,
            additional_logs=[
                ('update 1 RnaSamples', {'dbUpdate': {
                    'dbEntity': 'RnaSample', 'entityIds': [params['sample_guid']],
                    'updateType': 'bulk_update', 'updateFields': ['is_active']}}),
                (f'delete {model_cls.__name__}s', {'dbUpdate': {
                    'dbEntity': model_cls.__name__, 'numEntities': deleted_count,
                   'parentEntityIds': [params['sample_guid']], 'updateType': 'bulk_delete'}}),
            ])
        self.assertFalse(params['sample_guid'] in response_json['sampleGuids'])
        self.assertEqual(mock_send_slack.call_count, 2)
        mock_send_slack.assert_has_calls([
            mock.call(
                'seqr-data-loading',
                f'0 new RNA {params["message_data_type"]} sample(s) are loaded in <https://test-seqr.org/project/R0001_1kg/project_page|1kg project nåme with uniçøde>',
            ), mock.call(
                'seqr-data-loading',
                f'1 new RNA {params["message_data_type"]} sample(s) are loaded in <https://test-seqr.org/project/R0003_test/project_page|Test Reprocessed Project>\n```NA20888```',
            ),
        ])
        self.assertEqual(mock_send_email.call_count, 2)
        self._assert_expected_notifications(mock_send_email, [
            {'data_type': f'RNA {params["message_data_type"]}', 'user': self.data_manager_user,
             'email_body': f'data for 0 new RNA {params["message_data_type"]} sample(s)'},
            {'data_type': f'RNA {params["message_data_type"]}', 'user': self.data_manager_user,
             'email_body': f'data for 1 new RNA {params["message_data_type"]} sample(s)',
             'project_guid': 'R0003_test', 'project_name': 'Test Reprocessed Project'}
        ])

        # test database models are correct
        self.assertEqual(model_cls.objects.count(), params['initial_model_count'] - deleted_count)
        sample_guid = self._check_rna_sample_model(individual_id=1, data_source='new_muscle_samples.tsv.gz', data_type=params['data_type'],
                                                   tissue_type=params.get('sample_tissue_type'), is_active_sample=False)
        self.assertSetEqual(set(response_json['sampleGuids']), {sample_guid, new_sample_guid})

        # test correct file interactions
        file_path = RNA_FILENAME_TEMPLATE.format(data_type)
        expected_subprocess_calls = [
            f'gsutil ls {RNA_FILE_ID}',
            f'gsutil cat {RNA_FILE_ID} | gunzip -c -q - ',
        ] + self._additional_expected_loading_subprocess_calls(file_path)
        self.assertEqual(mock_subprocess.call_count, len(expected_subprocess_calls))
        mock_subprocess.assert_has_calls([
            mock.call(command, stdout=-1, stderr=-2, shell=True) for command in expected_subprocess_calls  # nosec
        ])
        mock_mkdir.assert_any_call(f'tmp/temp_uploads/{file_path}')
        filename = f'tmp/temp_uploads/{file_path}/{new_sample_guid}.json.gz'
        expected_files = {
            f'tmp/temp_uploads/{file_path}/{new_sample_guid if guid == PLACEHOLDER_GUID else sample_guid}.json.gz': data
            for guid, data in params['parsed_file_data'].items()
        }
        self.assertIn(filename, expected_files)
        file_rename = self._assert_expected_file_open(mock_rename, mock_open, expected_files.keys())
        for filename in expected_files:
            self.assertEqual(
                ''.join([call.args[0] for call in mock_files[file_rename[filename]].write.call_args_list]),
                expected_files[filename],
            )

        # test loading new data without deleting existing data
        data = [params['no_existing_data']]
        body.pop('mappingFile')
        _test_basic_data_loading(data, 1, 1, 2, body, '1kg project nåme with uniçøde')

        # Test loading data when where are duplicated individual ids in different projects.
        data = params['duplicated_indiv_id_data']
        mock_files = defaultdict(mock.MagicMock)
        _test_basic_data_loading(data, 2, 2, 20, body, '1kg project nåme with uniçøde, Test Reprocessed Project',
                                 num_created_samples=2)

        self.assertSetEqual(
            {''.join([call.args[0] for call in mock_file.write.call_args_list]) for mock_file in mock_files.values()},
            params['write_data'],
        )

        # Test loading data when where an individual has multiple tissue types
        data = [data[1][:2] + data[0][2:], data[1]]
        mock_files = defaultdict(mock.MagicMock)
        mock_rename.reset_mock()
        new_sample_individual_id = 7
        response_json, new_sample_guid = _test_basic_data_loading(data, 2, 2, new_sample_individual_id, body,
                                                                  '1kg project nåme with uniçøde')
        second_tissue_sample_guid = self._check_rna_sample_model(
            individual_id=new_sample_individual_id, data_source='new_muscle_samples.tsv.gz', data_type=params['data_type'],
            tissue_type='M' if params.get('sample_tissue_type') == 'F' else 'F', is_active_sample=False,
        )
        self.assertTrue(second_tissue_sample_guid != new_sample_guid)
        self.assertTrue(second_tissue_sample_guid in response_json['sampleGuids'])
        self._assert_expected_file_open(mock_rename, mock_open, [
            f'tmp/temp_uploads/{RNA_FILENAME_TEMPLATE.format(data_type)}/{sample_guid}.json.gz'
            for sample_guid in response_json['sampleGuids']
        ])
        self.assertSetEqual(
            {''.join([call.args[0] for call in mock_file.write.call_args_list]) for mock_file in mock_files.values()},
            params['write_data'],
        )

    @staticmethod
    def _additional_expected_loading_subprocess_calls(file_path):
        return []

    def _get_expected_read_file_subprocess_calls(self, file_name, sample_guid):
        return []

    def _assert_expected_file_open(self, mock_rename, mock_open, expected_file_names):
        file_rename = {call.args[1]: call.args[0] for call in mock_rename.call_args_list}
        self.assertSetEqual(set(expected_file_names), set(file_rename.keys()))
        mock_open.assert_has_calls([mock.call(file_rename[filename], 'at') for filename in expected_file_names])
        return file_rename

    def test_load_rna_seq_sample_data(self):

        url = reverse(load_rna_seq_sample_data, args=[RNA_TPM_MUSCLE_SAMPLE_GUID])
        self.check_pm_login(url)

        for data_type, params in self.RNA_DATA_TYPE_PARAMS.items():
            with self.subTest(data_type):
                sample_guid = params['sample_guid']
                url = reverse(load_rna_seq_sample_data, args=[sample_guid])
                model_cls = params['model_cls']
                model_cls.objects.all().delete()
                self.reset_logs()
                parsed_file_lines = params['parsed_file_data'][sample_guid].strip().split('\n')

                file_name = RNA_FILENAME_TEMPLATE.format(data_type)
                not_found_logs = self._set_file_not_found(file_name, sample_guid)

                body = {'fileName': file_name, 'dataType': data_type}
                response = self.client.post(url, content_type='application/json', data=json.dumps(body))
                self.assertEqual(response.status_code, 400)
                self.assertDictEqual(response.json(), {'error': 'Data for this sample was not properly parsed. Please re-upload the data'})
                self.assert_json_logs(self.pm_user, [
                    ('Loading outlier data for NA19675_1', None),
                    *not_found_logs,
                    (f'No saved temp data found for {sample_guid} with file prefix {file_name}', {
                        'severity': 'ERROR', '@type': 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent',
                    }),
                ])

                self._add_file_iter([row.encode('utf-8') for row in parsed_file_lines])

                self.reset_logs()
                response = self.client.post(url, content_type='application/json', data=json.dumps(body))
                self.assertEqual(response.status_code, 200)
                self.assertDictEqual(response.json(), {'success': True})

                models = model_cls.objects.all()
                num_models = len(params['expected_models_json'])
                self.assertEqual(models.count(), num_models)
                self.assertSetEqual({model.sample.guid for model in models}, {sample_guid})
                self.assertTrue(all(model.sample.is_active for model in models))

                subprocess_logs = self._get_expected_read_file_subprocess_calls(file_name, sample_guid)

                self.assert_json_logs(self.pm_user, [
                    ('Loading outlier data for NA19675_1', None),
                    *subprocess_logs,
                    (f'create {model_cls.__name__}s', {'dbUpdate': {
                        'dbEntity': model_cls.__name__, 'numEntities': num_models, 'parentEntityIds': [sample_guid],
                        'updateType': 'bulk_create',
                    }}),
                ])

                self.assertListEqual(list(params['get_models_json'](models)), params['expected_models_json'])

                mismatch_row = {**json.loads(parsed_file_lines[0]), params.get('mismatch_field', 'p_value'): '0.05'}
                self._add_file_iter([json.dumps(mismatch_row).encode('utf-8')])
                response = self.client.post(url, content_type='application/json', data=json.dumps(body))
                self.assertEqual(response.status_code, 400)
                self.assertDictEqual(response.json(), {
                    'error': f'Error in {sample_guid.split("_", 1)[-1].upper()}: mismatched entries for {params.get("row_id", mismatch_row["gene_id"])}'
                })

    @classmethod
    def _join_data(cls, data):
        return ['\t'.join(line).encode('utf-8') for line in data]

    @mock.patch('seqr.utils.communication_utils.BASE_URL', 'https://test-seqr.org/')
    @mock.patch('seqr.models.random')
    @mock.patch('seqr.utils.communication_utils.send_html_email')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_load_phenotype_prioritization_data(self, mock_subprocess, mock_send_email, mock_random):
        url = reverse(load_phenotype_prioritization_data)
        self.check_data_manager_login(url)

        request_body = {'file': 'gs://seqr_data/lirical_data.tsv.gz'}
        mock_subprocess.return_value.wait.return_value = 1
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'File not found: gs://seqr_data/lirical_data.tsv.gz')
        mock_subprocess.assert_called_with('gsutil ls gs://seqr_data/lirical_data.tsv.gz', stdout=-1, stderr=-2, shell=True)  # nosec

        mock_subprocess.reset_mock()
        mock_subprocess.return_value.wait.return_value = 0
        mock_subprocess.return_value.stdout = self._join_data(PHENOTYPE_PRIORITIZATION_MISS_HEADER)
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Invalid file: missing column(s) project, diseaseId')
        mock_subprocess.assert_called_with('gsutil cat gs://seqr_data/lirical_data.tsv.gz | gunzip -c -q - ', stdout=-1, stderr=-2, shell=True)  # nosec

        mock_subprocess.reset_mock()
        mock_subprocess.return_value.stdout = self._join_data(PHENOTYPE_PRIORITIZATION_HEADER + LIRICAL_NO_PROJECT_DATA)
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Both sample ID and project fields are required.')
        mock_subprocess.assert_called_with('gsutil cat gs://seqr_data/lirical_data.tsv.gz | gunzip -c -q - ', stdout=-1, stderr=-2, shell=True)  # nosec

        mock_subprocess.return_value.stdout = self._join_data(PHENOTYPE_PRIORITIZATION_HEADER + LIRICAL_DATA + EXOMISER_DATA)
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Multiple tools found lirical and exomiser. Only one in a file is supported.')

        mock_subprocess.return_value.stdout = self._join_data(PHENOTYPE_PRIORITIZATION_HEADER + LIRICAL_PROJECT_NOT_EXIST_DATA)
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Project CMG_Beggs_WGS not found. ')

        mock_random.randint.return_value = 12345
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
        mock_random.randint.side_effect = [256989491, 295284416]
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        info = [
            'Loaded Lirical data from gs://seqr_data/lirical_data.tsv.gz',
            'Project 1kg project nåme with uniçøde: deleted 1 record(s), loaded 1 record(s)',
            'Project Test Reprocessed Project: loaded 1 record(s)'
        ]
        self.assertEqual(response.json()['info'], info)
        self._has_expected_file_loading_logs('gs://seqr_data/lirical_data.tsv.gz', user=self.data_manager_user, additional_logs=[
            ('delete 1 PhenotypePrioritizations', {'dbUpdate': {
                'dbEntity': 'PhenotypePrioritization', 'updateType': 'bulk_delete',
                'entityIds': ['PP000003_NA19678_ENSG000002689'],
            }}),
            ('create 2 PhenotypePrioritizations', {'dbUpdate': {
                'dbEntity': 'PhenotypePrioritization', 'updateType': 'bulk_create',
                "entityIds": ['PP256989491_na19678ensg0000010', 'PP295284416_na20885ensg0000010'],
            }}),
        ])
        saved_data = _get_json_for_models(PhenotypePrioritization.objects.filter(tool='lirical').order_by('id'),
                                          nested_fields=[{'fields': ('individual', 'guid'), 'key': 'individualGuid'}])
        self.assertListEqual(saved_data, EXPECTED_LIRICAL_DATA)
        mock_subprocess.assert_called_with('gsutil cat gs://seqr_data/lirical_data.tsv.gz | gunzip -c -q - ', stdout=-1, stderr=-2, shell=True)  # nosec
        self._assert_expected_notifications(mock_send_email, [
            {'data_type': 'Lirical', 'user': self.data_manager_user, 'email_body': 'data for 1 Lirical sample(s)'},
            {'data_type': 'Lirical', 'user': self.data_manager_user, 'email_body': 'data for 1 Lirical sample(s)',
             'project_guid': 'R0003_test', 'project_name': 'Test Reprocessed Project'}
        ])

        # Test uploading new data
        self.reset_logs()
        mock_send_email.reset_mock()
        mock_subprocess.return_value.stdout = self._join_data(PHENOTYPE_PRIORITIZATION_HEADER + UPDATE_LIRICAL_DATA)
        mock_random.randint.side_effect = [177442291, 215071655]
        response = self.client.post(url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)
        info = [
            'Loaded Lirical data from gs://seqr_data/lirical_data.tsv.gz',
            'Project 1kg project nåme with uniçøde: deleted 1 record(s), loaded 2 record(s)'
        ]
        self.assertEqual(response.json()['info'], info)
        self._has_expected_file_loading_logs('gs://seqr_data/lirical_data.tsv.gz', user=self.data_manager_user, additional_logs=[
            ('delete 1 PhenotypePrioritizations', {'dbUpdate': {
                'dbEntity': 'PhenotypePrioritization', 'updateType': 'bulk_delete',
                'entityIds': ['PP256989491_na19678ensg0000010'],
            }}),
            ('create 2 PhenotypePrioritizations', {'dbUpdate': {
                'dbEntity': 'PhenotypePrioritization', 'updateType': 'bulk_create',
                'entityIds': ['PP177442291_na19678ensg0000010', 'PP215071655_na19678ensg0000010'],
            }}),
        ])
        saved_data = _get_json_for_models(PhenotypePrioritization.objects.filter(tool='lirical'),
                                          nested_fields=[{'fields': ('individual', 'guid'), 'key': 'individualGuid'}])
        self.assertListEqual(saved_data, EXPECTED_UPDATED_LIRICAL_DATA)
        self._assert_expected_notifications(mock_send_email, [
            {'data_type': 'Lirical', 'user': self.data_manager_user, 'email_body': 'data for 2 Lirical sample(s)'},
        ])

    @staticmethod
    def _assert_expected_notifications(mock_send_email, expected_notifs: list[dict]):
        calls = []
        for notif_dict in expected_notifs:
            project_guid = notif_dict.get('project_guid', PROJECT_GUID)
            project_name = notif_dict.get('project_name', '1kg project nåme with uniçøde')
            url = f'https://test-seqr.org/project/{project_guid}/project_page'
            project_link = f'<a href={url}>{project_name}</a>'
            expected_email_body = (
                f'Dear seqr user,\n\nThis is to notify you that {notif_dict["email_body"]} '
                f'has been loaded in seqr project {project_link}\n\nAll the best,\nThe seqr team'
            )
            calls.append(
                mock.call(
                    email_body=expected_email_body,
                    subject=f'New {notif_dict["data_type"]} data available in seqr',
                    to=['test_user_manager@test.com'],
                    process_message=_set_bulk_notification_stream,
                )
            )
        mock_send_email.assert_has_calls(calls)

    @mock.patch('seqr.utils.file_utils.os.path.isfile', lambda *args: True)
    @mock.patch('seqr.utils.file_utils.glob.glob')
    def test_loading_vcfs(self, mock_glob):
        url = reverse(loading_vcfs)
        self.check_pm_login(url)

        mock_glob.return_value = []
        response = self.client.get(url, content_type='application/json')
        self._test_expected_vcf_responses(response, mock_glob, url)

    def _test_expected_vcf_responses(self, response, mock_glob, url):
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'vcfs': []})
        mock_glob.assert_called_with('/local_datasets/**', recursive=True)

        mock_glob.return_value = ['/local_datasets/sharded_vcf/part001.vcf', '/local_datasets/sharded_vcf/part002.vcf', '/local_datasets/test.vcf.gz']
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'vcfs': ['/sharded_vcf/part00*.vcf', '/test.vcf.gz']})
        mock_glob.assert_called_with('/local_datasets/**', recursive=True)

        # test data manager access
        self.login_data_manager_user()
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)

    @mock.patch('seqr.utils.file_utils.os.path.isfile')
    @mock.patch('seqr.utils.file_utils.glob.glob')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    def test_validate_callset(self, mock_subprocess, mock_glob, mock_os_isfile):
        url = reverse(validate_callset)
        self.check_pm_login(url)

        mock_os_isfile.return_value = False
        mock_glob.return_value = []
        mock_subprocess.return_value.wait.return_value = -1
        mock_subprocess.return_value.stdout = [b'File not found']
        body = {'filePath': f'{self.CALLSET_DIR}/mito_callset.mt', 'datasetType': 'SV'}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [
            'Invalid VCF file format - file path must end with .bed or .bed.gz or .vcf or .vcf.gz or .vcf.bgz',
        ])

        body['datasetType'] = 'MITO'
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [f'Data file or path {self.CALLSET_DIR}/mito_callset.mt is not found.'])

        mock_os_isfile.return_value = True
        mock_subprocess.return_value.wait.return_value = 0
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': True})

        mock_subprocess.return_value.communicate.return_value = (
            b'', b'CommandException: One or more URLs matched no objects.',
        )
        body = {'filePath': f'{self.CALLSET_DIR}/sharded_vcf/part0*.vcf'}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(
            response.json()['errors'], [f'Data file or path {self.CALLSET_DIR}/sharded_vcf/part0*.vcf is not found.'],
        )

        mock_subprocess.return_value.communicate.return_value = (
            b'gs://test_bucket/sharded_vcf/part001.vcf\ngs://test_bucket/sharded_vcf/part002.vcf\n', b'',
        )
        mock_glob.return_value = ['/local_dir/sharded_vcf/part001.vcf', '/local_dir/sharded_vcf/part002.vcf']
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': True})

        # test data manager access
        self.login_data_manager_user()
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)

    @mock.patch('seqr.views.utils.permissions_utils.INTERNAL_NAMESPACES', ['my-seqr-billing', 'ext-data'])
    @mock.patch('seqr.views.utils.airtable_utils.BASE_URL', 'https://seqr.broadinstitute.org/')
    @responses.activate
    def test_get_loaded_projects(self):
        responses.add(
            responses.GET, 'https://api.airtable.com/v0/app3Y97xtbbaOopVR/Samples', json=AIRTABLE_SAMPLE_RECORDS, status=200,
        )

        url = reverse(get_loaded_projects, args=['38', 'WGS', 'SV'])
        self.check_pm_login(url)

        self.reset_logs()
        response = self._assert_expected_pm_access(lambda: self.client.get(url))
        self.assertDictEqual(response.json(), {'projects': [{**self.PROJECT_OPTION, 'dataTypeLastLoaded': '2018-02-05T06:31:55.397Z'}]})

        response = self.client.get(url.replace('SV', 'MITO'))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'projects': [self.PROJECT_OPTION]})

        snv_indel_url = url.replace('SV', 'SNV_INDEL')
        response = self.client.get(snv_indel_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'projects': [self.PROJECT_OPTION]})

        snv_indel_url = snv_indel_url.replace('38', '37')
        response = self.client.get(snv_indel_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'projects': self.WGS_PROJECT_OPTIONS})
        self._assert_expected_get_projects_requests()

        # test projects with no data loaded are returned for any sample type
        response = self.client.get(snv_indel_url.replace('WGS', 'WES'))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'projects': self.WES_PROJECT_OPTIONS})

    def _assert_expected_pm_access(self, get_response):
        response = get_response()
        self.assertEqual(response.status_code, 200)
        self.login_data_manager_user()
        return response

    @responses.activate
    @mock.patch('seqr.views.utils.airtable_utils.BASE_URL', 'https://seqr.broadinstitute.org/')
    @mock.patch('seqr.views.utils.export_utils.os.makedirs')
    @mock.patch('seqr.views.utils.export_utils.open')
    @mock.patch('seqr.views.utils.export_utils.TemporaryDirectory')
    def test_load_data(self, mock_temp_dir, mock_open, mock_mkdir):
        url = reverse(load_data)
        self.check_pm_login(url)

        responses.add(responses.GET, 'https://api.airtable.com/v0/app3Y97xtbbaOopVR/Samples', json=AIRTABLE_SAMPLE_RECORDS, status=200)
        responses.add(responses.POST, PIPELINE_RUNNER_URL)
        mock_temp_dir.return_value.__enter__.return_value = '/mock/tmp'
        body = {'filePath': f'{self.CALLSET_DIR}/mito_callset.mt', 'datasetType': 'MITO', 'sampleType': 'WES', 'genomeVersion': '38', 'projects': [
            json.dumps(option) for option in self.PROJECT_OPTIONS + [{'projectGuid': 'R0005_not_project'}]
        ], 'skipValidation': True}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'The following projects are invalid: R0005_not_project'})

        body['projects'] = body['projects'][:-1]
        self._test_no_affected_family(url, body)

        self.reset_logs()
        responses.calls.reset()
        response = self._assert_expected_pm_access(
            lambda: self.client.post(url, content_type='application/json', data=json.dumps(body))
        )
        self.assertDictEqual(response.json(), {'success': True})

        self._assert_expected_load_data_requests(sample_type='WES', skip_validation=True)
        self._has_expected_ped_files(mock_open, mock_mkdir, 'MITO', sample_type='WES')

        dag_json = {
            'projects_to_run': [
                'R0001_1kg',
                'R0004_non_analyst_project'
            ],
            'dataset_type': 'MITO',
            'reference_genome': 'GRCh38',
            'callset_path': f'{self.TRIGGER_CALLSET_DIR}/mito_callset.mt',
            'sample_type': 'WES',
            'skip_validation': True,
        }
        self._assert_success_notification(dag_json)

        # Test loading trigger error
        self._set_loading_trigger_error()
        mock_open.reset_mock()
        mock_mkdir.reset_mock()
        responses.calls.reset()
        self.reset_logs()

        del body['skipValidation']
        del dag_json['skip_validation']
        body.update({'datasetType': 'SV', 'filePath': f'{self.CALLSET_DIR}/sv_callset.vcf'})
        self._trigger_error(url, body, dag_json, mock_open, mock_mkdir)

        responses.add(responses.POST, PIPELINE_RUNNER_URL)
        responses.calls.reset()
        mock_open.reset_mock()
        mock_mkdir.reset_mock()
        body.update({'sampleType': 'WGS', 'projects': [json.dumps(self.PROJECT_OPTION)]})
        del body['datasetType']
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self._test_load_single_project(mock_open, mock_mkdir, response, url=url, body=body)

        # Test write pedigree error
        self.reset_logs()
        responses.calls.reset()
        mock_mkdir.reset_mock()
        mock_open.reset_mock()
        mock_open.side_effect = OSError('Restricted filesystem')
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self._assert_write_pedigree_error(response)
        self.assert_json_logs(self.data_manager_user, [
            ('Uploading Pedigrees failed. Errors: Restricted filesystem', {
                'severity': 'ERROR',
                '@type': 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent',
                'detail': {'R0004_non_analyst_project_pedigree': mock.ANY},
            }),
        ])

    def _trigger_error(self, url, body, dag_json, mock_open, mock_mkdir):
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self._assert_expected_load_data_requests(trigger_error=True, dataset_type='GCNV', sample_type='WES')
        self._assert_trigger_error(response, body, dag_json)
        self._has_expected_ped_files(mock_open, mock_mkdir, 'GCNV', sample_type='WES')

    def _has_expected_ped_files(self, mock_open, mock_mkdir, dataset_type, sample_type='WGS', single_project=False):
        mock_open.assert_has_calls([
            mock.call(f'{self._local_pedigree_path(dataset_type, sample_type)}/{project}_pedigree.tsv', 'w')
            for project in self.PROJECTS[(1 if single_project else 0):]
        ], any_order=True)
        files = [
            [row.split('\t') for row in write_call.args[0].split('\n')]
            for write_call in mock_open.return_value.__enter__.return_value.write.call_args_list
        ]
        self.assertEqual(len(files), 1 if single_project else 2)

        num_rows = 7 if self.MOCK_AIRTABLE_KEY else 15
        if not single_project:
            self.assertEqual(len(files[0]), num_rows)
            self.assertListEqual(files[0][:5], [PEDIGREE_HEADER] + EXPECTED_PEDIGREE_ROWS[:num_rows-1])
        file = files[0 if single_project else 1]
        self.assertEqual(len(file), 3)
        self.assertListEqual(file, [
            PEDIGREE_HEADER,
            ['R0004_non_analyst_project', 'F000014_14', '14', 'NA21234', '', '', 'F'],
            ['R0004_non_analyst_project', 'F000014_14', '14', 'NA21987', '', '', 'M'],
        ])

    def _test_load_single_project(self, mock_open, mock_mkdir, response, *args, **kwargs):
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': True})
        self._has_expected_ped_files(mock_open, mock_mkdir, 'SNV_INDEL', single_project=True)
        # Only a DAG trigger, no airtable calls as there is no previously loaded WGS SNV_INDEL data for these samples
        self.assertEqual(len(responses.calls), 1)

    def _test_no_affected_family(self, url, body):
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'errors': ['The following families have no affected individuals and can not be loaded to seqr: F000005_5'],
            'warnings': None,
        })
        Individual.objects.filter(guid='I000009_na20874').update(affected='A')


class LocalDataManagerAPITest(AuthenticationTestCase, DataManagerAPITest):
    fixtures = ['users', '1kg_project', 'reference_data']

    TRIGGER_CALLSET_DIR = '/local_datasets'
    CALLSET_DIR = ''
    PROJECT_OPTION = PROJECT_OPTION
    WGS_PROJECT_OPTIONS = [EMPTY_PROJECT_OPTION]
    WES_PROJECT_OPTIONS = [
        {'name': '1kg project nåme with uniçøde', 'projectGuid': 'R0001_1kg', 'dataTypeLastLoaded': '2017-02-05T06:25:55.397Z'},
        EMPTY_PROJECT_OPTION,
    ]
    PROJECT_OPTIONS = [{'projectGuid': 'R0001_1kg'}, PROJECT_OPTION]

    def setUp(self):
        patcher = mock.patch('seqr.utils.file_utils.os.path.isfile')
        self.mock_does_file_exist = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.utils.file_utils.gzip.open')
        self.mock_open = patcher.start()
        self.mock_file_iter = self.mock_open.return_value.__enter__.return_value.__iter__
        self.mock_file_iter.return_value = []
        self.addCleanup(patcher.stop)
        super().setUp()

    def _set_file_not_found(self, file_name, sample_guid):
        self.mock_does_file_exist.return_value = False
        self.mock_file_iter.return_value = []
        return []

    def _add_file_iter(self, stdout):
        self.mock_does_file_exist.return_value = True
        self.mock_file_iter.return_value += stdout

    def _assert_expected_get_projects_requests(self):
        self.assertEqual(len(responses.calls), 0)

    def _assert_expected_load_data_requests(self, dataset_type='MITO', sample_type='WGS', trigger_error=False, skip_project=False, skip_validation=False):
        self.assertEqual(len(responses.calls), 1)
        projects = [PROJECT_GUID, NON_ANALYST_PROJECT_GUID]
        if skip_project:
            projects = projects[1:]
        body = {
            'projects_to_run': projects,
            'callset_path': '/local_datasets/sv_callset.vcf' if trigger_error else '/local_datasets/mito_callset.mt',
            'sample_type': sample_type,
            'dataset_type': dataset_type,
            'reference_genome': 'GRCh38',
        }
        if skip_validation:
            body['skip_validation'] = True
        self.assertDictEqual(json.loads(responses.calls[0].request.body), body)

    @staticmethod
    def _local_pedigree_path(dataset_type, sample_type):
        return f'/local_datasets/GRCh38/{dataset_type}/pedigrees/{sample_type}'

    def _has_expected_ped_files(self, mock_open, mock_mkdir, dataset_type, *args, sample_type='WGS', **kwargs):
        super()._has_expected_ped_files(mock_open, mock_mkdir, dataset_type,  *args, sample_type, **kwargs)
        mock_mkdir.assert_called_once_with(self._local_pedigree_path(dataset_type, sample_type), exist_ok=True)

    def _assert_success_notification(self, dag_json):
        self.maxDiff = None
        self.assert_json_logs(self.pm_user, [('Triggered loading pipeline', {'detail': dag_json})])

    def _set_loading_trigger_error(self):
        responses.add(responses.POST, PIPELINE_RUNNER_URL, status=400)

    def _trigger_error(self, url, body, dag_json, mock_open, mock_mkdir):
        super()._trigger_error(url, body, dag_json, mock_open, mock_mkdir)

        responses.add(responses.POST, PIPELINE_RUNNER_URL, status=409)
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self._assert_trigger_error(response, body, dag_json, response_body={
            'errors': ['Loading pipeline is already running. Wait for it to complete and resubmit'], 'warnings': None,
        })

    def _assert_trigger_error(self, response, body, *args, response_body=None, **kwargs):
        self.assertEqual(response.status_code, 400)
        error = f'400 Client Error: Bad Request for url: {PIPELINE_RUNNER_URL}'
        self.assertDictEqual(response.json(), response_body or {'error': error})
        self.assert_json_logs(self.data_manager_user, [
            (error, {'severity': 'WARNING', 'requestBody': body, 'httpRequest': mock.ANY, 'traceback': mock.ANY}),
        ])

    def _test_load_single_project(self, *args, **kwargs):
        super()._test_load_single_project(*args, **kwargs)
        self._assert_expected_load_data_requests(dataset_type='SNV_INDEL', skip_project=True, trigger_error=True)

    def _assert_write_pedigree_error(self, response):
        self.assertEqual(response.status_code, 500)
        self.assertDictEqual(response.json(), {'error': 'Restricted filesystem'})
        self.assertEqual(len(responses.calls), 0)


@mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
class AnvilDataManagerAPITest(AirflowTestCase, DataManagerAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']

    ADDITIONAL_REQUEST_COUNT = 1
    LOADING_PROJECT_GUID = NON_ANALYST_PROJECT_GUID
    CALLSET_DIR = 'gs://test_bucket'
    TRIGGER_CALLSET_DIR = CALLSET_DIR
    LOCAL_WRITE_DIR = '/mock/tmp'
    PROJECT_OPTION = PROJECT_SAMPLES_OPTION
    WGS_PROJECT_OPTIONS = [EMPTY_PROJECT_SAMPLES_OPTION]
    WES_PROJECT_OPTIONS = [EMPTY_PROJECT_SAMPLES_OPTION]
    PROJECT_OPTIONS = [
        {'projectGuid': 'R0001_1kg', 'sampleIds': ['NA19675_1', 'NA19678', 'NA19679', 'HG00732', 'HG00733']},
        PROJECT_SAMPLES_OPTION,
    ]

    def setUp(self):
        patcher = mock.patch('seqr.utils.file_utils.subprocess.Popen')
        self.mock_subprocess = patcher.start()
        self.mock_does_file_exist = mock.MagicMock()
        self.mock_file_iter = mock.MagicMock()
        self.mock_file_iter.stdout = []
        self.mock_subprocess.side_effect = [self.mock_does_file_exist, self.mock_file_iter]
        self.addCleanup(patcher.stop)
        super().setUp()

    def _set_file_not_found(self, file_name, sample_guid):
        self.mock_file_iter.stdout = []
        self.mock_does_file_exist.wait.return_value = 1
        self.mock_does_file_exist.stdout = [b'CommandException: One or more URLs matched no objects']
        self.mock_subprocess.side_effect = [self.mock_does_file_exist]
        return [
            (f'==> gsutil ls gs://seqr-scratch-temp/{file_name}/{sample_guid}.json.gz', None),
            ('CommandException: One or more URLs matched no objects', None),
        ]

    def _add_file_iter(self, stdout):
        self.mock_does_file_exist.wait.return_value = 0
        self.mock_file_iter.stdout += stdout
        self.mock_subprocess.side_effect = [self.mock_does_file_exist, self.mock_file_iter]

    def _get_expected_read_file_subprocess_calls(self, file_name, sample_guid):
        gsutil_cat = f'gsutil cat gs://seqr-scratch-temp/{file_name}/{sample_guid}.json.gz | gunzip -c -q - '
        self.mock_subprocess.assert_called_with(gsutil_cat, stdout=-1, stderr=-2, shell=True)  # nosec
        return [
            (f'==> gsutil ls gs://seqr-scratch-temp/{file_name}/{sample_guid}.json.gz', None),
            (f'==> {gsutil_cat}', None),
        ]

    @staticmethod
    def _additional_expected_loading_subprocess_calls(file_path):
        return [f'gsutil mv tmp/temp_uploads/{file_path} gs://seqr-scratch-temp/{file_path}']

    def _assert_expected_es_status(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Elasticsearch is disabled')

    def _assert_expected_delete_index_response(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Deleting indices is disabled for the hail backend')

    def _assert_expected_get_projects_requests(self):
        pdo_filter = "OR(SEARCH('Methods (Loading)',ARRAYJOIN(PDOStatus,';')),SEARCH('On hold for phenotips, but ready to load',ARRAYJOIN(PDOStatus,';')))"
        expected_filters = [
            f'AND(LEN({{PassingCollaboratorSampleIDs}})>0{additional_filter},{pdo_filter})'
            for additional_filter in [',LEN({SV_CallsetPath})>0', ',LEN({MITO_WGS_CallsetPath})>0', '', '']
        ]
        self.assertEqual(len(responses.calls), len(expected_filters))
        for i, filter_formula in enumerate(expected_filters):
            self.assert_expected_airtable_call(
                call_index=i,
                filter_formula=filter_formula,
                fields=['CollaboratorSampleID', 'SeqrCollaboratorSampleID', 'PDOStatus', 'SeqrProject'],
            )

    def _assert_expected_pm_access(self, get_response):
        response = get_response()
        self.assertEqual(response.status_code, 403)
        self.assert_json_logs(self.pm_user, [
            ('PermissionDenied: Error: To access RDG airtable user must login with Broad email.', {'severity': 'WARNING'})
        ])
        self.login_data_manager_user()
        return super()._assert_expected_pm_access(get_response)

    @staticmethod
    def _get_dag_variable_overrides(*args, **kwargs):
        return {
            'callset_path': 'mito_callset.mt',
            'sample_source': 'Broad_Internal',
            'sample_type': 'WES',
            'dataset_type': 'MITO',
            'skip_validation': True,
        }

    def _assert_expected_load_data_requests(self, dataset_type='MITO', **kwargs):
        required_sample_field = 'MITO_WES_CallsetPath' if dataset_type == 'MITO' else 'gCNV_CallsetPath'
        self._assert_expected_airtable_call(required_sample_field, 'R0001_1kg')
        self.assert_airflow_loading_calls(offset=1, dataset_type=dataset_type, **kwargs)

    def _assert_expected_airtable_call(self, required_sample_field, project_guid):
        self.assert_expected_airtable_call(
            call_index=0,
            filter_formula=f"AND(SEARCH('https://seqr.broadinstitute.org/project/{project_guid}/project_page',ARRAYJOIN({{SeqrProject}},';')),LEN({{PassingCollaboratorSampleIDs}})>0,LEN({{{required_sample_field}}})>0,OR(SEARCH('Available in seqr',ARRAYJOIN(PDOStatus,';')),SEARCH('Historic',ARRAYJOIN(PDOStatus,';'))))",
            fields=['CollaboratorSampleID', 'SeqrCollaboratorSampleID', 'PDOStatus', 'SeqrProject'],
        )

    def _set_loading_trigger_error(self):
        self.set_dag_trigger_error_response(status=400)
        self.mock_authorized_session.reset_mock()

    def _assert_success_notification(self, dag_json):
        dag_json['sample_source'] = 'Broad_Internal'

        message = f"""*test_data_manager@broadinstitute.org* triggered loading internal WES MITO data for 2 projects

        Pedigree files have been uploaded to gs://seqr-loading-temp/v3.1/GRCh38/MITO/pedigrees/WES

        DAG LOADING_PIPELINE is triggered with following:
        ```{json.dumps(dag_json, indent=4)}```
    """
        self.mock_slack.assert_called_once_with(SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, message)
        self.mock_slack.reset_mock()

    def _assert_trigger_error(self, response, body, dag_json, **kwargs):
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': True})

        self.mock_airflow_logger.warning.assert_not_called()
        self.mock_airflow_logger.error.assert_called_with(mock.ANY, self.data_manager_user)
        errors = [call.args[0] for call in self.mock_airflow_logger.error.call_args_list]
        for error in errors:
            self.assertRegex(error, '400 Client Error: Bad Request')

        dag_json = json.dumps(dag_json, indent=4).replace('mito_callset.mt', 'sv_callset.vcf').replace(
            'WGS', 'WES').replace('MITO', 'GCNV').replace('v01', 'v3.1')
        error_message = f"""ERROR triggering internal WES SV loading: {errors[0]}
        
        DAG LOADING_PIPELINE should be triggered with following: 
        ```{dag_json}```
        """
        self.mock_slack.assert_called_once_with(SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, error_message)

    def _trigger_error(self, url, body, dag_json, mock_open, mock_mkdir):
        super()._trigger_error(url, body, dag_json, mock_open, mock_mkdir)

        responses.calls.reset()
        body['projects'] = [json.dumps({**PROJECT_OPTION, 'sampleIds': PROJECT_SAMPLES_OPTION['sampleIds'] + ['NA21988']})]
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'warnings': None,
            'errors': ['The following samples are included in airtable but missing from seqr: NA21988'],
        })
        body['projects'] = [json.dumps({**PROJECT_OPTION, 'sampleIds': [PROJECT_SAMPLES_OPTION['sampleIds'][1]]})]
        body['sampleType'] = 'WGS'

        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'warnings': None,
            'errors': ['The following families have previously loaded samples absent from airtable: 14 (NA21234)'],
        })
        self.assertEqual(len(responses.calls), 1)
        self._assert_expected_airtable_call(required_sample_field='SV_CallsetPath', project_guid='R0004_non_analyst_project')
        self.mock_authorized_session.reset_mock()

    def _test_load_single_project(self, mock_open, mock_mkdir, response, *args, url=None, body=None, **kwargs):
        super()._test_load_single_project(mock_open, mock_mkdir, response, url, body)
        self.ADDITIONAL_REQUEST_COUNT = 0
        self.assert_airflow_loading_calls(offset=0, dataset_type='SNV_INDEL', trigger_error=True)

        responses.calls.reset()
        mock_open.reset_mock()
        mock_mkdir.reset_mock()
        body['projects'] = [json.dumps(option) for option in self.PROJECT_OPTIONS]
        body['sampleType'] = 'WES'
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': True})
        self._has_expected_ped_files(mock_open, mock_mkdir, 'SNV_INDEL', sample_type='WES')
        self.assertEqual(len(responses.calls), 2)
        self.assert_expected_airtable_call(
            call_index=0,
            filter_formula="AND(SEARCH('https://seqr.broadinstitute.org/project/R0001_1kg/project_page',ARRAYJOIN({SeqrProject},';')),LEN({PassingCollaboratorSampleIDs})>0,OR(SEARCH('Available in seqr',ARRAYJOIN(PDOStatus,';')),SEARCH('Historic',ARRAYJOIN(PDOStatus,';'))))",
            fields=['CollaboratorSampleID', 'SeqrCollaboratorSampleID', 'PDOStatus', 'SeqrProject'],
        )
        body['projects'] = body['projects'][1:]

    @staticmethod
    def _local_pedigree_path(*args):
        return '/mock/tmp'

    def _has_expected_ped_files(self, mock_open, mock_mkdir, dataset_type, *args, sample_type='WGS', **kwargs):
        super()._has_expected_ped_files(mock_open, mock_mkdir, dataset_type, sample_type, **kwargs)

        mock_mkdir.assert_not_called()
        self.mock_subprocess.assert_called_once_with(
            f'gsutil mv /mock/tmp/* gs://seqr-loading-temp/v3.1/GRCh38/{dataset_type}/pedigrees/{sample_type}/',
            stdout=-1, stderr=-2, shell=True,  # nosec
        )
        self.mock_subprocess.reset_mock()

    def _assert_write_pedigree_error(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(responses.calls), 1)

    def _test_no_affected_family(self, url, body):
        # Sample ID filtering skips the unaffected family
        pass

    def _test_expected_vcf_responses(self, response, mock_glob, url):
        self.assertEqual(response.status_code, 403)
