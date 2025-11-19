from collections import defaultdict
from datetime import datetime
from django.urls.base import reverse
import json
import mock
from requests import HTTPError
import responses

from clickhouse_search.models import EntriesSnvIndel, ProjectGtStatsSnvIndel, AnnotationsSnvIndel
from seqr.utils.communication_utils import _set_bulk_notification_stream
from seqr.views.apis.data_manager_api import elasticsearch_status, delete_index, \
    update_rna_seq, load_phenotype_prioritization_data, validate_callset, loading_vcfs, \
    get_loaded_projects, load_data, trigger_delete_project, trigger_delete_family
from seqr.views.utils.orm_to_json_utils import _get_json_for_models
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, AirtableTest
from seqr.utils.search.elasticsearch.es_utils_tests import urllib3_responses
from seqr.models import Individual, Sample, RnaSeqOutlier, RnaSeqTpm, RnaSeqSpliceOutlier, RnaSample, Project, PhenotypePrioritization
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
    'test_index_mito_wgs does not exist and is used by project(s) 1kg project n\xe5me with uni\xe7\xf8de (1 samples)',
    'test_index_old does not exist and is used by project(s) 1kg project n\xe5me with uni\xe7\xf8de (1 samples)',
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
        'gene_id': 'ENSG00000233750', 'chrom': 'chr2', 'start': '167254166', 'end': '167258349', 'strand': '*', 'type': 'psi3',
        'p_value': '1.56e-25', 'p_adjust': '-4.9', 'delta_intron_jaccard_index': '-0.46', 'counts': '166',
        'mean_counts': '16.6', 'total_counts': '1660', 'mean_total_counts': '1.66',
        'rare_disease_samples_with_this_junction': '1', 'rare_disease_samples_total': '20',
    },
    {
        'gene_id': 'ENSG00000240361', 'chrom': 'chr2', 'start': '167254166', 'end': '167258349', 'strand': '*', 'type': 'psi3',
        'p_value': '1.56e-25', 'p_adjust': '-4.9', 'delta_intron_jaccard_index': '-0.46', 'counts': '166',
        'mean_counts': '16.6', 'total_counts': '1660', 'mean_total_counts': '1.66',
        'rare_disease_samples_with_this_junction': '1', 'rare_disease_samples_total': '20',
    },
    {
        'gene_id': 'ENSG00000240361', 'chrom': 'chr7', 'start': '132885746', 'end': '132975168', 'strand': '*', 'type': 'psi5',
        'p_value': '1.08e-56', 'p_adjust': '-6.53', 'delta_intron_jaccard_index': '-0.85', 'counts': '231',
        'mean_counts': '0.231', 'total_counts': '2313', 'mean_total_counts': '231.3',
        'rare_disease_samples_with_this_junction': '1', 'rare_disease_samples_total': '20',
    },
]
SAMPLE_GENE_SPLICE_DATA2 = {
        'gene_id': '', 'chrom': 'chr2', 'start': '167258096', 'end': '167258349', 'strand': '*', 'type': 'psi3',
        'p_value': '1.56e-25', 'p_adjust': '6.33', 'delta_intron_jaccard_index': '0.45', 'counts': '143',
        'mean_counts': '14.3', 'total_counts': '1433', 'mean_total_counts': '143.3',
        'rare_disease_samples_with_this_junction': '1', 'rare_disease_samples_total': '20',
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
RNA_OUTLIER_REQUIRED_COLUMNS = 'geneID, pValue, padjust, sampleID, zScore'
RNA_TPM_REQUIRED_COLUMNS = 'Name OR gene_id, TPM, sample_id'
RNA_SPLICE_OUTLIER_REQUIRED_COLUMNS = 'chrom OR seqnames, counts, deltaIntronJaccardIndex OR deltaPsi, end, geneID OR hgncSymbol, meanCounts, meanTotalCounts, pAdjust OR padjust, pValue, sampleID, start, strand, totalCounts, type'

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

CORE_REQUEST_BODY = {
    'filePath': '/callset.vcf',
    'sampleType': 'WES',
    'genomeVersion': '38',
}

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
                'VCFIDWithMismatch': 'ABC123',
            }
        },
        {
            'id': 'rec2B6OGmQpAkQW7s',
            'fields': {
                'SeqrProject': ['https://seqr.broadinstitute.org/project/R0004_non_analyst_project/project_page'],
                'PDOStatus': ['Methods (Loading)'],
                'CollaboratorSampleID': 'NA21987',
                'VCFIDWithMismatch': 'NA21987_a',
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
INVALID_AIRTABLE_SAMPLE_RECORDS = {
    'records': [
        {
            'id': 'rec2B6OGmQpAkQW3s',
            'fields': {
                'SeqrProject': [
                    'https://seqr.broadinstitute.org/project/R0002_empty/project_page',
                    'https://seqr.broadinstitute.org/project/R0004_non_analyst_project/project_page',
                ],
                'PDOStatus': ['Historic', 'Methods (Loading)', 'Available in seqr'],
                'CollaboratorSampleID': 'NA21234',
            }
        },
        {
            'id': 'recW24C2CJW5lT65K',
            'fields': {
                'CollaboratorSampleID': 'HG00731',
                'SeqrProject': ['https://seqr.broadinstitute.org/project/R0001_1kg/details'],
                'PDOStatus': ['Available in seqr'],
            }
        },
    ],
}

AIRTABLE_RNA_SAMPLE_RECORDS = [
    {
        'id': 'recW24C2CJW5lT75K',
        'fields': {
            'SeqrCollaboratorSampleID': 'NA19675_1',
            'CollaboratorSampleID': 'NA19675_D2',
            'SeqrProject': ['https://seqr.broadinstitute.org/project/R0001_1kg/project_page'],
            'PDOStatus': ['RNA ready to load'],
        }
    },
    {
        'id': 'recW56C2CJW5lT6c5',
        'fields': {
            'CollaboratorSampleID': 'NA19678',
            'SeqrProject': [
                'https://seqr.broadinstitute.org/project/R0001_1kg/project_page',
                'https://seqr.broadinstitute.org/project/R0003_test/project_page',
            ],
            'PDOStatus': ['RNA ready to load', 'Available in seqr'],
            'TissueOfOrigin': ['Muscle'],
        }
    },
    {
        'id': 'recW56C2CJW5lT75x',
        'fields': {
            'CollaboratorSampleID': 'NA20888',
            'SeqrProject': ['https://seqr.broadinstitute.org/project/R0003_test/project_page'],
            'PDOStatus': ['RNA ready to load'],
            'TissueOfOrigin': ['Muscle'],
        }
    },
    {
        'id': 'rec2B6OGmVpAkQW3s',
        'fields': {
            'CollaboratorSampleID': 'NA12345',
            'SeqrProject': [
                'https://seqr.broadinstitute.org/project/R0002_empty/project_page',
                'https://seqr.broadinstitute.org/project/R0004_non_analyst_project/project_page',
            ],
            'PDOStatus': ['RNA ready to load', 'RNA ready to load'],
            'TissueOfOrigin': ['Muscle', 'Brain'],
        }
    },
    *INVALID_AIRTABLE_SAMPLE_RECORDS['records'],
]

VCF_SAMPLES = [
    'ABC123', 'NA19675_1', 'NA19678', 'NA19679', 'HG00731', 'HG00732', 'HG00733', 'NA20874', 'NA21234', 'NA21987',
]

PIPELINE_RUNNER_HOST = 'http://pipeline-runner:6000'
PIPELINE_RUNNER_URL = f'{PIPELINE_RUNNER_HOST}/loading_pipeline_enqueue'


@mock.patch('seqr.views.apis.data_manager_api.LOADING_DATASETS_DIR', '/local_datasets')
@mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
class DataManagerAPITest(AirtableTest):

    PROJECTS = [PROJECT_GUID, NON_ANALYST_PROJECT_GUID]
    VCF_SAMPLES = VCF_SAMPLES
    SKIP_TDR = False

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
        self._assert_expected_delete_active_index_response(response)

        urllib3_responses.add_json(
            '/_cat/indices?format=json&h=index,docs.count,store.size,creation.date.string', ES_CAT_INDICES)
        urllib3_responses.add_json('/_cat/aliases?format=json&h=alias,index', ES_CAT_ALIAS)
        urllib3_responses.add_json('/_all/_mapping', ES_INDEX_MAPPING)
        urllib3_responses.add(urllib3_responses.DELETE, '/unused_index')

        response = self.client.post(url, content_type='application/json', data=json.dumps({'index': 'unused_index'}))
        self._assert_expected_delete_index_response(response)

    def _assert_expected_delete_active_index_response(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'], '"test_index" is still used by: 1kg project n\xe5me with uni\xe7\xf8de')
        self.assertEqual(len(urllib3_responses.calls), 0)

    def _assert_expected_delete_index_response(self, response):
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'indices'})
        self.assertEqual(len(response_json['indices']), 6)
        self.assertDictEqual(response_json['indices'][0], TEST_INDEX_EXPECTED_DICT)
        self.assertDictEqual(response_json['indices'][3], TEST_INDEX_NO_PROJECT_EXPECTED_DICT)
        self.assertDictEqual(response_json['indices'][4], TEST_SV_INDEX_EXPECTED_DICT)

        self.assertEqual(urllib3_responses.calls[0].request.method, 'DELETE')

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
        'E': {
            'model_cls': RnaSeqOutlier,
            'message_data_type': 'Expression Outlier',
            'header': ['sampleID', 'geneID', 'detail', 'pValue', 'padjust', 'zScore'],
            'required_columns': RNA_OUTLIER_REQUIRED_COLUMNS,
            'loaded_data_row': ['NA19675_D2', 'ENSG00000240361', 'detail1', 0.01, 0.001, -3.1],
            'no_existing_data': ['NA19678', 'ENSG00000233750', 'detail1', 0.064, '0.0000057', 7.8],
            'new_data': [
                ['NA19675_D2', 'ENSG00000240361', 'detail1', 0.01, 0.13, -3.1],
                ['NA19675_D2', 'ENSG00000240361', 'detail2', 0.01, 0.13, -3.1],
                ['NA19675_D2', 'ENSG00000233750', 'detail1', 0.064, '0.0000057', 7.8],
                ['NA19675_D3', 'ENSG00000233750', 'detail1', 0.064, '0.0000057', 7.8],
                ['NA20888', 'ENSG00000240361', '', 0.04, 0.112, 1.9],
            ],
            'skipped_samples': 'NA19675_D3',
            'sample_tissue_type': 'Muscle',
            'num_parsed_samples': 3,
            'initial_model_count': 3,
            'parsed_file_data': RNA_OUTLIER_SAMPLE_DATA,
            'sample_guid': RNA_OUTLIER_MUSCLE_SAMPLE_GUID,
        },
        'T': {
            'model_cls': RnaSeqTpm,
            'message_data_type': 'Expression',
            'header': ['sample_id', 'gene_id', 'TPM', 'Description'],
            'required_columns': RNA_TPM_REQUIRED_COLUMNS,
            'loaded_data_row': ['NA19675_D2', 'ENSG00000135953', 1.34, ''],
            'no_existing_data': ['NA19678', 'ENSG00000233750', 0.064, ''],
            'new_data': [
                # existing sample NA19675_D2
                ['NA19675_D2', 'ENSG00000240361', 7.8, 'some gene of interest'],
                ['NA19675_D2', 'ENSG00000233750', 0.0, ''],
                # no matched individual NA19675_D3
                ['NA19675_D3', 'ENSG00000233750', 0.064, ''],
                # a different project sample NA20888
                ['NA20888', 'ENSG00000240361', 0.112, ''],
                # a project mismatched sample NA20878
                ['NA20878', 'ENSG00000233750', 0.064, ''],
            ],
            'skipped_samples': 'NA19675_D3, NA20878',
            'sample_tissue_type': 'Muscle',
            'num_parsed_samples': 4,
            'initial_model_count': 5,
            'deleted_count': 3,
            'parsed_file_data': RNA_TPM_SAMPLE_DATA,
            'sample_guid': RNA_TPM_MUSCLE_SAMPLE_GUID,
        },
        'S': {
            'model_cls': RnaSeqSpliceOutlier,
            'message_data_type': 'Splice Outlier',
            'header': ['sampleID', 'geneID', 'chrom', 'start', 'end', 'strand', 'type', 'pValue', 'pAdjust',
                       'deltaIntronJaccardIndex', 'counts', 'meanCounts', 'totalCounts', 'meanTotalCounts', 'rareDiseaseSamplesWithThisJunction',
                       'rareDiseaseSamplesTotal'],
            'required_columns': RNA_SPLICE_OUTLIER_REQUIRED_COLUMNS,
            'loaded_data_row': ['NA19675_1', 'ENSG00000240361', 'chr7', 132885746, 132886973, '*',
                                'psi5', 1.08E-56, 3.08E-56, 12.34, 1297, 197, 129, 1297, 0.53953638, 1, 20],
            'no_existing_data': ['NA19678', 'ENSG00000240361', 'chr7', 132885746, 132886973, '*',
                                'psi5', 1.08E-56, 3.08E-56, 12.34, 1297, 197, 129, 1297, 0.53953638, 1, 20],
            'new_data': [
                # existing sample NA19675_1
                ['NA19675_1', 'ENSG00000233750;ENSG00000240361', 'chr2', 167254166, 167258349, '*', 'psi3',
                 1.56E-25, -4.9, -0.46, 166, 16.6, 1660, 1.66, 1, 20],
                ['NA19675_1', 'ENSG00000240361', 'chr7', 132885746, 132975168, '*', 'psi5',
                 1.08E-56, -6.53, -0.85, 231, 0.231, 2313, 231.3, 1, 20],
                # no matched individual NA19675_D3
                ['NA19675_D3', 'ENSG00000233750', 'chr2', 167258096, 167258349, '*',
                 'psi3', 1.56E-25, 6.33, 0.45, 143, 14.3, 1433, 143.3, 1, 20],
                # a new sample NA20888
                ['NA20888', '', 'chr2', 167258096, 167258349, '*',
                 'psi3', 1.56E-25, 6.33, 0.45, 143, 14.3, 1433, 143.3, 1, 20],
                # a project mismatched sample NA20878
                ['NA20878', 'ENSG00000233750', 'chr2', 167258096, 167258349, '*', 'psi3',
                 1.56E-25, 6.33, 0.45, 143, 14.3, 1433, 143.3, 1, 20],
            ],
            'skipped_samples': 'NA19675_D3, NA20878',
            'sample_tissue_type': 'Fibroblast',
            'num_parsed_samples': 4,
            'initial_model_count': 7,
            'deleted_count': 4,
            'parsed_file_data': RNA_SPLICE_SAMPLE_DATA,
            'allow_missing_gene': True,
            'sample_guid': RNA_SPLICE_SAMPLE_GUID,
        },
    }

    def _has_expected_file_loading_logs(self, file, user, info=None, warnings=None, additional_logs=None, additional_logs_offset=None, include_airtable_logs=False):
        expected_logs = [
            (f'==> gsutil ls {file}', None),
            (f'==> gsutil cat {file} | gunzip -c -q - ', None),
        ] + [(info_log, None) for info_log in info or []] + [
            (warn_log, {'severity': 'WARNING'}) for warn_log in warnings or []
        ]
        if include_airtable_logs:
            expected_logs = [
                ('Fetching Samples records 0-1 from airtable', None),
                ('Fetched 6 Samples records from airtable', None),
                ('Skipping samples associated with misconfigured PDOs in Airtable: HG00731, NA21234', {'severity': 'WARNING'}),
                ('Skipping samples associated with multiple conflicting PDOs in Airtable: NA12345', {'severity': 'WARNING'}),
            ] + expected_logs
        if additional_logs:
            if additional_logs_offset:
                for log in reversed(additional_logs):
                    expected_logs.insert(additional_logs_offset, log)
            else:
                expected_logs += additional_logs

        self.assert_json_logs(user, expected_logs)

    def _check_rna_sample_model(self, individual_id, data_source, data_type, tissue_type, is_active_sample=True):
        tissue_type = tissue_type[0]
        rna_samples = RnaSample.objects.filter(
            individual_id=individual_id, tissue_type=tissue_type, data_source=data_source, data_type=data_type,
        )
        self.assertEqual(len(rna_samples), 1)
        sample = rna_samples.first()
        self.assertEqual(sample.is_active, is_active_sample)
        self.assertEqual(sample.tissue_type, tissue_type)
        return sample.guid

    def test_update_rna_outlier(self, *args, **kwargs):
        self._test_update_rna_seq('E', *args, **kwargs)

    def test_update_rna_tpm(self, *args, **kwargs):
        self._test_update_rna_seq('T', *args, **kwargs)

    def test_update_rna_splice_outlier(self, *args, **kwargs):
        self._test_update_rna_seq('S', *args, **kwargs)

    @mock.patch('seqr.views.utils.airtable_utils.BASE_URL', 'https://seqr.broadinstitute.org/')
    @mock.patch('seqr.utils.communication_utils.BASE_URL', 'https://test-seqr.org/')
    @mock.patch('seqr.utils.search.add_data_utils.SEQR_SLACK_DATA_ALERTS_NOTIFICATION_CHANNEL', 'seqr-data-loading')
    @mock.patch('seqr.views.utils.file_utils.tempfile.gettempdir', lambda: 'tmp/')
    @mock.patch('seqr.utils.communication_utils.send_html_email')
    @mock.patch('seqr.utils.communication_utils.safe_post_to_slack')
    @mock.patch('seqr.views.utils.dataset_utils.datetime')
    @mock.patch('seqr.views.utils.dataset_utils.os.mkdir')
    @mock.patch('seqr.views.utils.dataset_utils.os.rename')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    @mock.patch('seqr.views.utils.dataset_utils.gzip.open')
    @responses.activate
    def _test_update_rna_seq(self, data_type, mock_open, mock_subprocess,
                            mock_rename, mock_mkdir, mock_datetime, mock_send_slack, mock_send_email):
        url = reverse(update_rna_seq)
        self.check_pm_login(url)

        params = self.RNA_DATA_TYPE_PARAMS[data_type]
        model_cls = params['model_cls']
        header = params['header']
        loaded_data_row = params['loaded_data_row']
        samples_url = 'https://api.airtable.com/v0/app3Y97xtbbaOopVR/Samples'
        responses.add(responses.GET, samples_url, json={'records': []})

        # Test errors
        body = {'dataType': data_type, 'file': 'gs://rna_data/muscle_samples.tsv'}
        mock_datetime.now.return_value = datetime(2020, 4, 15)
        mock_does_file_exist = mock.MagicMock()
        mock_does_file_exist.wait.return_value = 1
        mock_subprocess.side_effect = [mock_does_file_exist]
        self.reset_logs()
        response = self._assert_expected_pm_access(
            lambda: self.client.post(url, content_type='application/json', data=json.dumps(body)), status_code=400,
        )
        self.assertDictEqual(response.json(), {'error': 'File not found: gs://rna_data/muscle_samples.tsv'})

        mock_does_file_exist.wait.return_value = 0
        mock_file_iter = mock.MagicMock()
        def _set_file_iter_stdout(rows):
            mock_file_iter.wait.return_value = 0
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
            'error': f'Invalid file: missing column(s): {params["required_columns"]}',
        })

        _set_file_iter_stdout([header, loaded_data_row])
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'errors': [f'Unable to find matches for the following samples: {loaded_data_row[0]}'], 'warnings': None})

        airtable_sample_records = [
            {
                **AIRTABLE_RNA_SAMPLE_RECORDS[0],
                'fields': {
                    **AIRTABLE_RNA_SAMPLE_RECORDS[0]['fields'],
                    'TissueOfOrigin': [params['sample_tissue_type']],
                }
            },
            *AIRTABLE_RNA_SAMPLE_RECORDS[1:],
        ]
        responses.replace(responses.GET, samples_url, json={'records': airtable_sample_records})
        unknown_gene_id_row1 = loaded_data_row[:1] + ['NOT_A_GENE_ID1'] + loaded_data_row[2:]
        unknown_gene_id_row2 = loaded_data_row[:1] + ['NOT_A_GENE_ID2'] + loaded_data_row[2:]
        _set_file_iter_stdout([header, unknown_gene_id_row1, unknown_gene_id_row2])
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['errors'][0], 'Unknown Gene IDs: NOT_A_GENE_ID1, NOT_A_GENE_ID2')

        if not params.get('allow_missing_gene'):
            _set_file_iter_stdout([header, loaded_data_row[:1] + [''] + loaded_data_row[2:]])
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
        self._has_expected_file_loading_logs('gs://rna_data/muscle_samples.tsv.gz', info=info, warnings=warnings, user=self.data_manager_user, include_airtable_logs=True)
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
            responses.calls.reset()
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
                individual_id=new_sample_individual_id, data_source='new_muscle_samples.tsv.gz', data_type=data_type,
                tissue_type='M', is_active_sample=False,
            )
            self.assertTrue(new_sample_guid in response_json['sampleGuids'])
            additional_logs = [(f'create {num_created_samples} RnaSamples', {'dbUpdate': {
                'dbEntity': 'RnaSample', 'updateType': 'bulk_create',
                'entityIds': response_json['sampleGuids'] if num_created_samples > 1 else [new_sample_guid],
            }})] + (additional_logs or [])
            self._has_expected_file_loading_logs(
                'gs://rna_data/new_muscle_samples.tsv.gz', info=info, warnings=warnings, user=self.data_manager_user,
                additional_logs=additional_logs, additional_logs_offset=6, include_airtable_logs=True)

            self.assertEqual(len(responses.calls), 1)
            self.assert_expected_airtable_call(
                call_index=0,
                filter_formula="AND(LEN({PassingCollaboratorSampleIDs})>0,LEN({TissueOfOrigin})>0,OR(SEARCH('RNA ready to load',ARRAYJOIN(PDOStatus,';'))))",
                fields=['CollaboratorSampleID', 'SeqrCollaboratorSampleID', 'PDOStatus', 'SeqrProject', 'TissueOfOrigin'],
            )

            return response_json, new_sample_guid

        # Test loading new data
        mock_open.reset_mock()
        mock_subprocess.reset_mock()
        self.reset_logs()
        mock_files = defaultdict(mock.MagicMock)
        mock_open.side_effect = lambda file_name, *args: mock_files[file_name]
        body.update({'ignoreExtraSamples': True, 'file': RNA_FILE_ID})
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
                f'0 new RNA {params["message_data_type"]} samples are loaded in <https://test-seqr.org/project/R0001_1kg/project_page|1kg project nåme with uniçøde>',
            ), mock.call(
                'seqr-data-loading',
                f'1 new RNA {params["message_data_type"]} samples are loaded in <https://test-seqr.org/project/R0003_test/project_page|Test Reprocessed Project>\n```NA20888```',
            ),
        ])
        self.assertEqual(mock_send_email.call_count, 2)
        self._assert_expected_notifications(mock_send_email, [
            {'data_type': f'RNA {params["message_data_type"]}', 'user': self.data_manager_user,
             'email_body': f'data for 0 new RNA {params["message_data_type"]} samples'},
            {'data_type': f'RNA {params["message_data_type"]}', 'user': self.data_manager_user,
             'email_body': f'data for 1 new RNA {params["message_data_type"]} samples',
             'project_guid': 'R0003_test', 'project_name': 'Test Reprocessed Project'}
        ])

        # test database models are correct
        self.assertEqual(model_cls.objects.count(), params['initial_model_count'] - deleted_count)
        sample_guid = self._check_rna_sample_model(individual_id=1, data_source='new_muscle_samples.tsv.gz', data_type=data_type,
                                                   tissue_type=params.get('sample_tissue_type'), is_active_sample=False)
        self.assertSetEqual(set(response_json['sampleGuids']), {sample_guid, new_sample_guid})

        # test correct file interactions
        file_path = RNA_FILENAME_TEMPLATE.format(data_type)
        expected_subprocess_calls = [
            f'gsutil ls {RNA_FILE_ID}',
            f'gsutil cat {RNA_FILE_ID} | gunzip -c -q - ',
            f'gsutil mv tmp/temp_uploads/{file_path} gs://seqr-scratch-temp/{file_path}',

        ]
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
        _test_basic_data_loading(data, 1, 1, 2, body, '1kg project nåme with uniçøde')

    def _assert_expected_file_open(self, mock_rename, mock_open, expected_file_names):
        file_rename = {call.args[1]: call.args[0] for call in mock_rename.call_args_list}
        self.assertSetEqual(set(expected_file_names), set(file_rename.keys()))
        mock_open.assert_has_calls([mock.call(file_rename[filename], 'at') for filename in expected_file_names])
        return file_rename

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
        saved_data = _get_json_for_models(PhenotypePrioritization.objects.filter(tool='lirical').order_by('id'),
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

    def test_loading_vcfs(self):
        url = reverse(loading_vcfs)
        self.check_pm_login(url)

        response = self.client.get(url, content_type='application/json')
        self._test_expected_vcf_responses(response, url)

    def _test_expected_vcf_responses(self, response, url):
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'vcfs': []})
        self.mock_glob.assert_called_with('/local_datasets/**', recursive=True)

        self.mock_glob.return_value = ['/local_datasets/sharded_vcf/part001.vcf', '/local_datasets/sharded_vcf/part002.vcf', '/local_datasets/test.vcf.gz']
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'vcfs': ['/sharded_vcf/part00*.vcf', '/test.vcf.gz']})
        self.mock_glob.assert_called_with('/local_datasets/**', recursive=True)

        # test data manager access
        self.login_data_manager_user()
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_validate_callset(self):
        url = reverse(validate_callset)
        self.check_pm_login(url)

        self._set_file_not_found()

        self._test_validate_dataset_type(url)

        body = {**self.REQUEST_BODY, 'filePath': f'{self.CALLSET_DIR}/callset.txt'}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [
            'Invalid VCF file format - file path must end with .vcf or .vcf.gz or .vcf.bgz',
        ])

        response = self.client.post(url, content_type='application/json', data=json.dumps(self.REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [f'Data file or path {self.CALLSET_DIR}/callset.vcf is not found.'])

        vcf_file_rows = [
            '##fileformat=VCFv4.3\n',
            '##INFO=<ID=AA,Number=1,Type=String,Description="Ancestral Allele">',
            '##INFO=<ID=AC,Number=A,Type=Integer,Description="Allele count in genotypes, for each ALT allele, in the same order as listed">\n',
            '##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency, for each ALT allele, in the same order as listed">\n',
            '##INFO=<ID=AN,Number=1,Type=Integer,Description="Total number of alleles in called genotypes">\n',
            '##FORMAT=<ID=AD,Number=.,Type=Integer,Description="Allelic depths for the ref and alt alleles in the order listed">\n',
            '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Approximate read depth (reads with MQ=255 or with bad mates are filtered)">\n',
            '##FORMAT=<ID=GQ,Number=1,Type=Integer,Description="Genotype Quality">\n',
            '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n',
            '#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG00735\tNA19675_1\tNA19679\n'
        ]
        vcf_samples = ['HG00735', 'NA19675_1', 'NA19679']
        self._add_file_iter(vcf_file_rows, is_gz=False)
        response = self.client.post(url, content_type='application/json', data=json.dumps(self.REQUEST_BODY))

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'vcfSamples': vcf_samples})

        self._add_file_iter(vcf_file_rows, is_gz=True)
        body = {**self.REQUEST_BODY, 'filePath': f'{self.CALLSET_DIR}/callset.vcf.gz'}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'vcfSamples': vcf_samples})
        self._assert_expected_read_vcf_header_subprocess_calls(body)

        self._set_file_not_found(list_files=True)
        body = {**self.REQUEST_BODY, 'filePath': f'{self.CALLSET_DIR}/sharded_vcf/part0*.vcf'}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(
            response.json()['errors'], [f'Data file or path {self.CALLSET_DIR}/sharded_vcf/part0*.vcf is not found.'],
        )

        self._add_file_list_iter(
            ['sharded_vcf/part001.vcf', 'sharded_vcf/part002.vcf'], vcf_file_rows,
        )
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'vcfSamples': vcf_samples})

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

        self._assert_expected_airtable_errors(url)

    def _assert_expected_pm_access(self, get_response, status_code=200):
        response = get_response()
        self.assertEqual(response.status_code, status_code)
        self.login_data_manager_user()
        return response

    def _assert_expected_airtable_errors(self, url):
        return True

    @responses.activate
    @mock.patch('seqr.views.utils.airtable_utils.BASE_URL', 'https://seqr.broadinstitute.org/')
    @mock.patch('reference_data.models.GeneInfo.CURRENT_VERSION')
    @mock.patch('seqr.views.utils.export_utils.os.makedirs')
    @mock.patch('seqr.views.utils.export_utils.gzip.open')
    @mock.patch('seqr.views.utils.export_utils.open')
    @mock.patch('seqr.views.utils.export_utils.TemporaryDirectory')
    def test_load_data(self, mock_temp_dir, mock_open, mock_gzip_open, mock_mkdir, mock_current_gene_version):
        mock_current_gene_version.__int__.return_value = 27
        url = reverse(load_data)
        self.check_pm_login(url)

        responses.add(responses.GET, 'https://api.airtable.com/v0/app3Y97xtbbaOopVR/Samples', json=AIRTABLE_SAMPLE_RECORDS, status=200)
        responses.add(responses.POST, PIPELINE_RUNNER_URL)
        mock_temp_dir.return_value.__enter__.return_value = '/mock/tmp'
        body = {**self.REQUEST_BODY, 'projects': [
            json.dumps(option) for option in self.PROJECT_OPTIONS + [{'projectGuid': 'R0005_not_project'}]
        ], 'vcfSamples': self.VCF_SAMPLES, 'skipSRChecks': True}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'The following projects are invalid: R0005_not_project'})

        body['projects'] = body['projects'][:-1]
        self._test_no_affected_family(url, body)

        self.reset_logs()
        responses.calls.reset()
        self._set_file_not_found(has_mv_commands=True)
        response = self._assert_expected_pm_access(
            lambda: self.client.post(url, content_type='application/json', data=json.dumps(body)),
        )
        self.assertDictEqual(response.json(), {'success': True})

        self._assert_expected_load_data_requests(sample_type='WES', skip_check_sex_and_relatedness=True)
        self._has_expected_ped_files(mock_open, mock_gzip_open, mock_mkdir, 'SNV_INDEL', sample_type='WES', has_remap=bool(self.MOCK_AIRTABLE_KEY))

        variables = {
            'projects_to_run': [
                'R0001_1kg',
                'R0004_non_analyst_project'
            ],
            'dataset_type': 'SNV_INDEL',
            'reference_genome': 'GRCh38',
            'callset_path': f'{self.TRIGGER_CALLSET_DIR}/callset.vcf',
            'sample_type': 'WES',
            'skip_check_sex_and_relatedness': True,
        }
        if self.SKIP_TDR:
            variables['skip_expect_tdr_metrics'] = True
        self._assert_success_notification(variables)

        # Test loading trigger error
        self._set_file_not_found(has_mv_commands=True)
        mock_open.reset_mock()
        mock_gzip_open.reset_mock()
        mock_mkdir.reset_mock()
        responses.calls.reset()
        self.reset_logs()

        del body['skipSRChecks']
        del variables['skip_check_sex_and_relatedness']
        body.update({'datasetType': 'SV', 'filePath': f'{self.CALLSET_DIR}/sv_callset.vcf'})
        self._trigger_error(url, body, variables, mock_open, mock_gzip_open, mock_mkdir)

        self._set_file_found()
        responses.calls.reset()
        mock_open.reset_mock()
        mock_gzip_open.reset_mock()
        mock_mkdir.reset_mock()
        body.update({'sampleType': 'WGS', 'projects': [json.dumps(self.PROJECT_OPTION)], 'vcfSamples': VCF_SAMPLES})
        del body['datasetType']
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self._test_load_single_project(mock_open, mock_gzip_open, mock_mkdir, response, url=url, body=body)

        # Test write pedigree error
        self.reset_logs()
        self._set_file_found()
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

        # Test when gene data is not fully loaded
        responses.calls.reset()
        self._set_file_not_found(has_mv_commands=True)
        mock_open.side_effect = None
        mock_current_gene_version.__int__.return_value = 39
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 500)
        self.assertDictEqual(response.json(), {
            'error': 'Gene reference data is not yet loaded. If this is a new seqr installation, wait for the initial data load to complete. If this is an existing installation, see the documentation for updating data in seqr.',
        })
        self.assertEqual(len(responses.calls), 0)

    def _assert_expected_load_data_requests(self, dataset_type='SNV_INDEL', sample_type='WGS', trigger_error=False, skip_project=False, skip_check_sex_and_relatedness=False):
        projects = [PROJECT_GUID, NON_ANALYST_PROJECT_GUID]
        if skip_project:
            projects = projects[1:]
        body = {
            'projects_to_run': projects,
            'callset_path': f'{self.TRIGGER_CALLSET_DIR}/{"sv_" if trigger_error else ""}callset.vcf',
            'sample_type': sample_type,
            'dataset_type': dataset_type,
            'reference_genome': 'GRCh38',
        }
        if self.SKIP_TDR:
            body['skip_expect_tdr_metrics'] = True
        if skip_check_sex_and_relatedness:
            body['skip_check_sex_and_relatedness'] = True
        self.assertDictEqual(json.loads(responses.calls[-1].request.body), body)

    def _trigger_error(self, url, body, variables, mock_open, mock_gzip_open, mock_mkdir):
        responses.add(responses.POST, PIPELINE_RUNNER_URL, status=400)
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self._assert_expected_load_data_requests(trigger_error=True, dataset_type='GCNV', sample_type='WES')
        self._assert_trigger_error(response, body, variables, response_body={
            'error': f'400 Client Error: Bad Request for url: {PIPELINE_RUNNER_URL}'
        })
        self._has_expected_ped_files(mock_open, mock_gzip_open, mock_mkdir, 'GCNV', sample_type='WES')

        self._set_file_not_found(has_mv_commands=True)
        self.reset_logs()
        responses.add(responses.POST, PIPELINE_RUNNER_URL, status=409)
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self._assert_trigger_error(response, body, variables, response_body={
            'errors': ['Loading pipeline is already running. Wait for it to complete and resubmit'], 'warnings': None,
        })

        responses.add(responses.POST, PIPELINE_RUNNER_URL)

    def _has_expected_ped_files(self, mock_open, mock_gzip_open, mock_mkdir, dataset_type, sample_type='WGS', single_project=False, has_remap=False, has_gene_id_file=False):
        mock_open.assert_has_calls([
            mock.call(f'{self._local_pedigree_path(dataset_type, sample_type)}/{project}_pedigree.tsv', 'w')
            for project in self.PROJECTS[(1 if single_project else 0):]
        ], any_order=True)
        files = [
            [row.split('\t') for row in write_call.args[0].split('\n')]
            for write_call in mock_open.return_value.__enter__.return_value.write.call_args_list
        ]
        self.assertEqual(len(files), 1 if single_project else 2)

        if has_gene_id_file:
            mock_gzip_open.assert_not_called()
        else:
            mock_gzip_open.assert_called_once_with(f'{self.LOCAL_WRITE_DIR}/db_id_to_gene_id.csv.gz', 'wt')
            file = [
                row.split(',') for row in mock_gzip_open.return_value.__enter__.return_value.write.call_args.args[0].split('\n')
            ]
            self.assertEqual(len(file), self.NUM_FIXTURE_GENES)
            self.assertListEqual(file[:3], [['db_id', 'gene_id'], ['1', 'ENSG00000223972'], ['2', 'ENSG00000227232']])

        num_rows = 7 if self.MOCK_AIRTABLE_KEY else 8
        pedigree_header = PEDIGREE_HEADER + ['VCF_ID'] if has_remap else PEDIGREE_HEADER
        if not single_project:
            self.assertEqual(len(files[0]), num_rows)
            expected_rows = EXPECTED_PEDIGREE_ROWS[:num_rows-1]
            if has_remap:
                expected_rows = [row + [''] for row in expected_rows]
            self.assertListEqual(files[0][:5], [pedigree_header] + expected_rows)
        file = files[0 if single_project else 1]
        self.assertEqual(len(file), 3)
        self.assertListEqual(file, [
            pedigree_header,
            ['R0004_non_analyst_project', 'F000014_14', 'fam14', 'NA21234', '', '', 'F'] + (['ABC123'] if has_remap else []),
            ['R0004_non_analyst_project', 'F000014_14', 'fam14', 'NA21987', '', '', 'M'] + ([''] if has_remap else []),
        ])

    def _test_load_single_project(self, mock_open, mock_gzip_open, mock_mkdir, response, *args, **kwargs):
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': True})
        self._has_expected_ped_files(mock_open, mock_gzip_open, mock_mkdir, 'SNV_INDEL', single_project=True, has_gene_id_file=True)
        # Only a pipeline trigger, no airtable calls as there is no previously loaded WGS SNV_INDEL data for these samples
        self.assertEqual(len(responses.calls), 1)
        self._assert_expected_load_data_requests(skip_project=True, trigger_error=True)

    def _test_no_affected_family(self, url, body):
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'errors': ['The following families do not have any affected individuals: 5'],
            'warnings': None,
        })
        Individual.objects.filter(guid='I000009_na20874').update(affected='A')

    @responses.activate
    def test_trigger_delete_project(self):
        url = reverse(trigger_delete_project)
        self.check_data_manager_login(url)

        Project.objects.filter(guid=PROJECT_GUID).update(genome_version='38')
        response = self.client.post(
            url, content_type='application/json', data=json.dumps({'project': PROJECT_GUID, 'datasetType': 'SNV_INDEL'})
        )
        self._assert_expected_delete_project(response)

    @responses.activate
    def test_trigger_delete_family(self):
        responses.add(responses.POST, f'{PIPELINE_RUNNER_HOST}/delete_families_enqueue', status=200)

        url = reverse(trigger_delete_family)
        self.check_data_manager_login(url)

        Project.objects.filter(guid=PROJECT_GUID).update(genome_version='38')
        response = self.client.post(url, content_type='application/json', data=json.dumps({'family': 'F000002_2'}))
        self._assert_expected_delete_family(response)

    def _assert_expected_delete_project(self, response):
        self.assertEqual(response.status_code, 500)
        self.assertDictEqual(response.json(), {'error': 'trigger_delete_project is disabled without the clickhouse backend'})

    def _assert_expected_delete_family(self, response):
        self.assertEqual(response.status_code, 500)
        self.assertDictEqual(response.json(), {'error': 'trigger_delete_family is disabled without the clickhouse backend'})


class LocalDataManagerAPITest(AuthenticationTestCase, DataManagerAPITest):
    fixtures = ['users', '1kg_project', 'reference_data']

    NUM_FIXTURE_GENES = 52
    TRIGGER_CALLSET_DIR = '/local_datasets'
    LOCAL_WRITE_DIR = TRIGGER_CALLSET_DIR
    CALLSET_DIR = ''
    PROJECT_OPTION = PROJECT_OPTION
    WGS_PROJECT_OPTIONS = [EMPTY_PROJECT_OPTION]
    WES_PROJECT_OPTIONS = [
        {'name': '1kg project nåme with uniçøde', 'projectGuid': 'R0001_1kg', 'dataTypeLastLoaded': '2017-02-05T06:25:55.397Z'},
        EMPTY_PROJECT_OPTION,
    ]
    PROJECT_OPTIONS = [{'projectGuid': 'R0001_1kg'}, PROJECT_OPTION]
    REQUEST_BODY = CORE_REQUEST_BODY
    SKIP_TDR = True

    def setUp(self):
        patcher = mock.patch('seqr.utils.file_utils.os.path.isfile')
        self.mock_does_file_exist = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.utils.file_utils.glob.glob')
        self.mock_glob = patcher.start()
        self.mock_glob.return_value = []
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.utils.file_utils.gzip.open')
        self.mock_open = patcher.start()
        self.mock_file_iter = self.mock_open.return_value.__enter__.return_value.__iter__
        self.mock_file_iter.return_value = []
        self.mock_file_iter.stdout = []
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.utils.file_utils.open')
        self.mock_unzipped_open = patcher.start()
        self.mock_unzipped_file_iter = self.mock_unzipped_open.return_value.__enter__.return_value.__iter__
        self.mock_unzipped_file_iter.return_value = []
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.utils.file_utils.subprocess.Popen')
        self.mock_subprocess = patcher.start()
        self.mock_subprocess.side_effect = [self.mock_file_iter]
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.utils.search.add_data_utils.LOADING_DATASETS_DIR', self.TRIGGER_CALLSET_DIR)
        patcher.start()
        self.addCleanup(patcher.stop)
        super().setUp()

    def _set_file_not_found(self, file_name=None, sample_guid=None, list_files=False, has_mv_commands=False):
        self.mock_does_file_exist.return_value = False
        self.mock_file_iter.return_value = []
        return []

    def _set_file_found(self):
        self.mock_does_file_exist.return_value = True

    def _add_file_iter(self, stdout, is_gz=True):
        self.mock_does_file_exist.return_value = True
        file_iter = self.mock_file_iter if is_gz else self.mock_unzipped_file_iter
        file_iter.return_value += stdout
        file_iter.stdout += stdout

    def _add_file_list_iter(self, file_list, stdout):
        self.mock_does_file_exist.return_value = True
        self.mock_unzipped_file_iter.return_value = stdout
        self.mock_glob.return_value = [f'/local_dir/{file}' for file in file_list]

    def _assert_expected_get_projects_requests(self):
        self.assertEqual(len(responses.calls), 0)

    def _assert_expected_load_data_requests(self, *args, **kwargs):
        self.assertEqual(len(responses.calls), 1)
        super()._assert_expected_load_data_requests(*args, **kwargs)

    @staticmethod
    def _local_pedigree_path(dataset_type, sample_type):
        return f'/local_datasets/GRCh38/{dataset_type}/pedigrees/{sample_type}'

    def _has_expected_ped_files(self, mock_open, mock_gzip_open, mock_mkdir, dataset_type, *args, sample_type='WGS', has_gene_id_file=False, **kwargs):
        super()._has_expected_ped_files(mock_open, mock_gzip_open, mock_mkdir, dataset_type,  *args, sample_type, has_gene_id_file=has_gene_id_file, **kwargs)
        call_paths = [self._local_pedigree_path(dataset_type, sample_type)]
        if not has_gene_id_file:
            call_paths.append(self.LOCAL_WRITE_DIR)
        self.assertEqual(mock_mkdir.call_count, len(call_paths))
        mock_mkdir.assert_has_calls([mock.call(call_path, exist_ok=True) for call_path in call_paths])

    def _assert_success_notification(self, variables):
        self.maxDiff = None
        self.assert_json_logs(self.pm_user, [('Triggered Loading Pipeline', {'detail': variables})])

    def _trigger_error(self, url, body, variables, mock_open, mock_gzip_open, mock_mkdir):
        super()._trigger_error(url, body, variables, mock_open, mock_gzip_open, mock_mkdir)

        body['vcfSamples'] = body['vcfSamples'][:5]
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'errors': ['The following families have previously loaded samples absent from the vcf\nFamily 2: HG00732, HG00733'],
            'warnings': None,
        })

    def _assert_trigger_error(self, response, body, variables, response_body):
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), response_body)
        error = response_body.get('error') or response_body['errors'][0]
        self.assert_json_logs(self.data_manager_user, [
            (error, {'severity': 'WARNING', 'requestBody': body, 'httpRequest': mock.ANY, 'traceback': mock.ANY}),
        ])

    def _assert_expected_read_vcf_header_subprocess_calls(self, body):
        self.mock_subprocess.assert_has_calls([
            mock.call(f'dd skip=0 count=65537 bs=1 if={self.TRIGGER_CALLSET_DIR}{body["filePath"]} status="none" | gunzip -c - ', stdout=-1, stderr=-2, shell=True) # nosec
        ])

    def _assert_write_pedigree_error(self, response):
        self.assertEqual(response.status_code, 500)
        self.assertDictEqual(response.json(), {'error': 'Restricted filesystem'})
        self.assertEqual(len(responses.calls), 0)

    def _test_validate_dataset_type(self, url):
        pass

    def _test_update_rna_seq(self, data_type, *args, **kwargs):
        url = reverse(update_rna_seq)
        self.check_pm_login(url)
        body = {'dataType': data_type, 'file': 'gs://rna_data/muscle_samples.tsv'}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 500)
        self.assertDictEqual(response.json(), {'error': 'Airtable is not configured'})


@mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP', 'project-managers')
class AnvilDataManagerAPITest(AnvilAuthenticationTestCase, DataManagerAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data', 'clickhouse_search']

    NUM_FIXTURE_GENES = 59
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
    REQUEST_BODY = {
        **CORE_REQUEST_BODY,
        'filePath': CALLSET_DIR + CORE_REQUEST_BODY['filePath'],
        'datasetType': 'SNV_INDEL',
    }
    VCF_SAMPLES = [s for s in VCF_SAMPLES if s != 'NA21234']

    def setUp(self):
        patcher = mock.patch('seqr.utils.file_utils.subprocess.Popen')
        self.mock_subprocess = patcher.start()
        self.mock_does_file_exist = mock.MagicMock()
        self.mock_file_iter = mock.MagicMock()
        self.mock_file_iter.stdout = []
        self.mock_file_iter.wait.return_value = 0
        self.mock_subprocess.side_effect = [self.mock_does_file_exist, self.mock_file_iter]
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.utils.search.add_data_utils.safe_post_to_slack')
        self.mock_slack = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.utils.search.add_data_utils.LOADING_DATASETS_DIR', 'gs://seqr-loading-temp/v3.1')
        patcher.start()
        self.addCleanup(patcher.stop)
        super().setUp()

    def _set_file_not_found(self, file_name=None, sample_guid=None, list_files=False, has_mv_commands=False):
        self.mock_file_iter.stdout = []
        self.mock_does_file_exist.wait.return_value = 1
        subprocess_side_effect = [self.mock_does_file_exist]
        error = b'CommandException: One or more URLs matched no objects'
        if list_files:
            self.mock_does_file_exist.communicate.return_value = (b'', error)
            subprocess_side_effect.append(self.mock_does_file_exist)
        else:
            self.mock_does_file_exist.stdout = [error]
        if has_mv_commands:
            mock_mv = mock.MagicMock()
            mock_mv.wait.return_value = 0
            subprocess_side_effect = [mock_mv, self.mock_does_file_exist, mock_mv]
        self.mock_subprocess.side_effect = subprocess_side_effect
        return [
            (f'==> gsutil ls gs://seqr-scratch-temp/{file_name}/{sample_guid}.json.gz', None),
            ('CommandException: One or more URLs matched no objects', {'severity': 'WARNING'}),
        ]

    def _set_file_found(self):
        self.mock_subprocess.reset_mock()
        self.mock_does_file_exist.wait.return_value = 0
        self.mock_subprocess.side_effect = [
            self.mock_does_file_exist, self.mock_does_file_exist, self.mock_does_file_exist, self.mock_does_file_exist,
        ]

    def _add_file_iter(self, stdout, is_gz=True):
        self.mock_does_file_exist.wait.return_value = 0
        if not is_gz:
            stdout = [row.encode('utf-8') for row in stdout]
        self.mock_file_iter.stdout += stdout
        self.mock_subprocess.side_effect = [self.mock_does_file_exist, self.mock_file_iter]

    def _add_file_list_iter(self, file_list, stdout):
        formatted_files = '\n'.join([f'{self.CALLSET_DIR}/{file}' for file in file_list])
        self.mock_does_file_exist.communicate.return_value = (f'{formatted_files}\n'.encode('utf-8'), b'')
        self.mock_does_file_exist.wait.return_value = 0
        self.mock_file_iter.stdout += [row.encode('utf-8') for row in stdout]
        self.mock_subprocess.side_effect = [
            self.mock_does_file_exist, self.mock_does_file_exist,  self.mock_file_iter, self.mock_does_file_exist, self.mock_does_file_exist, self.mock_file_iter,
        ]

    def _get_expected_read_file_subprocess_calls(self, file_name, sample_guid):
        gsutil_cat = f'gsutil cat gs://seqr-scratch-temp/{file_name}/{sample_guid}.json.gz | gunzip -c -q - '
        self.mock_subprocess.assert_called_with(gsutil_cat, stdout=-1, stderr=-2, shell=True)  # nosec
        return [
            (f'==> gsutil ls gs://seqr-scratch-temp/{file_name}/{sample_guid}.json.gz', None),
            (f'==> {gsutil_cat}', None),
        ]

    def _assert_expected_es_status(self, response):
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()['error'], 'elasticsearch_status is disabled without the elasticsearch backend')

    def _assert_expected_delete_index_response(self, response):
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()['error'], 'delete_index is disabled without the elasticsearch backend')

    def _assert_expected_delete_active_index_response(self, response):
        self._assert_expected_delete_index_response(response)

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

    def _assert_expected_pm_access(self, get_response, *args, **kwargs):
        response = get_response()
        self.assertEqual(response.status_code, 403)
        self.assert_json_logs(self.pm_user, [
            ('PermissionDenied: Error: To access RDG airtable user must login with Broad email.', {'severity': 'WARNING'})
        ])
        self.login_data_manager_user()
        return super()._assert_expected_pm_access(get_response, *args, **kwargs)

    def _assert_expected_load_data_requests(self, *args, dataset_type='SNV_INDEL', skip_project=False, **kwargs):
        num_calls = 1
        is_gcnv = dataset_type == 'GCNV'
        required_sample_field = 'gCNV_CallsetPath' if is_gcnv else None
        if not skip_project:
            self._assert_expected_airtable_call(required_sample_field, 'R0001_1kg')
            num_calls += 1
        if (not is_gcnv) and (not skip_project):
            self._assert_expected_airtable_vcf_id_call(required_sample_field, call_index=1)
            num_calls += 1

        self.assertEqual(len(responses.calls), num_calls)
        super()._assert_expected_load_data_requests(*args, dataset_type=dataset_type, skip_project=skip_project, **kwargs)

    def _assert_expected_airtable_call(self, required_sample_field, project_guid, call_index=0, additional_filter=None, additional_pdo_statuses='', additional_fields=None):
        airtable_filters = [
            f"SEARCH('https://seqr.broadinstitute.org/project/{project_guid}/project_page',ARRAYJOIN({{SeqrProject}},';'))",
            "LEN({PassingCollaboratorSampleIDs})>0",
            f"OR(SEARCH('Available in seqr',ARRAYJOIN(PDOStatus,';')),SEARCH('Historic',ARRAYJOIN(PDOStatus,';')){additional_pdo_statuses})",
        ]
        if additional_filter:
            airtable_filters.insert(2, additional_filter)
        if required_sample_field:
            airtable_filters.insert(2, f'LEN({{{required_sample_field}}})>0')

        self.assert_expected_airtable_call(
            call_index=call_index,
            filter_formula=f"AND({','.join(airtable_filters)})",
            fields=['CollaboratorSampleID', 'SeqrCollaboratorSampleID', 'PDOStatus', 'SeqrProject', *(additional_fields or [])],
        )

    def _assert_expected_airtable_vcf_id_call(self, required_sample_field=None, additional_vcf_ids='', **kwargs):
        self._assert_expected_airtable_call(
            required_sample_field, 'R0004_non_analyst_project', **kwargs, additional_fields=['VCFIDWithMismatch', 'SeqrIDWithMismatch'],
            additional_filter=f"OR(SeqrIDWithMismatch='NA21234'{additional_vcf_ids})",
            additional_pdo_statuses=",SEARCH('Methods (Loading)',ARRAYJOIN(PDOStatus,';')),SEARCH('On hold for phenotips, but ready to load',ARRAYJOIN(PDOStatus,';'))",
        )

    def _assert_success_notification(self, variables):
        message = f"""*test_data_manager@broadinstitute.org* triggered loading internal WES SNV_INDEL data for 12 samples in 2 projects (1kg project nåme with uniçøde: 10; Non-Analyst Project: 2)

Pedigree files have been uploaded to gs://seqr-loading-temp/v3.1/GRCh38/SNV_INDEL/pedigrees/WES

Loading pipeline is triggered with:
```{json.dumps(variables, indent=4)}```"""
        self.mock_slack.assert_called_once_with(SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, message)
        self.mock_slack.reset_mock()

    def _assert_trigger_error(self, response, body, variables, response_body):
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': False})

        error = response_body.get('error') or response_body['errors'][0]
        variables = {
            **variables,
            'dataset_type': 'GCNV',
            'callset_path': variables['callset_path'].replace('callset.vcf', 'sv_callset.vcf'),
        }
        self.assert_json_logs(self.data_manager_user, [
            (f'Error Triggering Loading Pipeline: {error}', {'severity': 'WARNING', 'detail': variables}),
        ], offset=6)

        error_message = f"""ERROR triggering internal WES SV loading: {error}
Loading pipeline should be triggered with:
```{json.dumps(variables, indent=4)}```"""
        self.mock_slack.assert_called_once_with(SEQR_SLACK_LOADING_NOTIFICATION_CHANNEL, error_message)
        self.mock_slack.reset_mock()

    def _trigger_error(self, url, body, variables, mock_open, mock_gzip_open, mock_mkdir):
        body['vcfSamples'] = None
        super()._trigger_error(url, body, variables, mock_open, mock_gzip_open, mock_mkdir)

        responses.calls.reset()
        body['vcfSamples'] = ['ABC123', 'NA19675_1']
        body['projects'] = [json.dumps({**PROJECT_OPTION, 'sampleIds': PROJECT_SAMPLES_OPTION['sampleIds'] + ['NA21988']})]
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'warnings': None,
            'errors': [
                'The following samples are included in airtable for Non-Analyst Project but are missing from seqr: NA21988',
                'The following samples are included in airtable but are missing from the VCF: NA21987',
            ],
        })
        body['projects'] = [json.dumps({**PROJECT_OPTION, 'sampleIds': [PROJECT_SAMPLES_OPTION['sampleIds'][1]]})]
        body['sampleType'] = 'WGS'
        self.assertEqual(len(responses.calls), 1)
        self._assert_expected_airtable_vcf_id_call(
            required_sample_field='gCNV_CallsetPath', additional_vcf_ids=",SeqrIDWithMismatch='NA21987'",
        )

        responses.calls.reset()
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'warnings': None,
            'errors': [
                'The following families have previously loaded samples absent from airtable\nFamily fam14: NA21234, NA21654',
                'The following samples are included in airtable but are missing from the VCF: NA21987',
            ],
        })
        self.assertEqual(len(responses.calls), 2)
        self._assert_expected_airtable_call(required_sample_field='SV_CallsetPath', project_guid='R0004_non_analyst_project')

    def _test_load_single_project(self, mock_open, mock_gzip_open, mock_mkdir, response, *args, url=None, body=None, **kwargs):
        super()._test_load_single_project(mock_open, mock_gzip_open, mock_mkdir, response, url, body)

        responses.calls.reset()
        mock_open.reset_mock()
        mock_gzip_open.reset_mock()
        mock_mkdir.reset_mock()
        body['projects'] = [json.dumps(option) for option in self.PROJECT_OPTIONS]
        body['sampleType'] = 'WES'
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'success': True})
        self._has_expected_ped_files(mock_open, mock_gzip_open, mock_mkdir, 'SNV_INDEL', sample_type='WES', has_gene_id_file=True)
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

    def _has_expected_ped_files(self, mock_open, mock_gzip_open, mock_mkdir, dataset_type, *args, sample_type='WGS', has_gene_id_file=False, **kwargs):
        super()._has_expected_ped_files(mock_open, mock_gzip_open, mock_mkdir, dataset_type, sample_type, has_gene_id_file=has_gene_id_file, **kwargs)

        mock_mkdir.assert_not_called()
        expected_calls = [mock.call(
            f'gsutil mv /mock/tmp/* gs://seqr-loading-temp/v3.1/GRCh38/{dataset_type}/pedigrees/{sample_type}/',
            stdout=-1, stderr=-2, shell=True,  # nosec
        ), mock.call(
            'gsutil ls gs://seqr-loading-temp/v3.1/db_id_to_gene_id.csv.gz', stdout=-1, stderr=-2, shell=True, # nosec
        )]
        if not has_gene_id_file:
            expected_calls.append(mock.call(
                'gsutil mv /mock/tmp/* gs://seqr-loading-temp/v3.1/', stdout=-1, stderr=-2, shell=True, # nosec
            ))
        self.assertEqual(self.mock_subprocess.call_count, len(expected_calls))
        self.mock_subprocess.assert_has_calls(expected_calls)
        self.mock_subprocess.reset_mock()

    def _assert_write_pedigree_error(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(responses.calls), 1)

    def _test_no_affected_family(self, url, body):
        # Sample ID filtering skips the unaffected family
        pass

    def _test_expected_vcf_responses(self, response, url):
        self.assertEqual(response.status_code, 403)

    def _assert_expected_read_vcf_header_subprocess_calls(self, body):
        self.mock_subprocess.assert_has_calls([
            mock.call(command, stdout=-1, stderr=-2, shell=True) # nosec
            for command in [
                f'gsutil cat -r 0-65536 {body["filePath"]} | gunzip -c -q - ',
            ]
        ])

    def _test_validate_dataset_type(self, url):
        body = {'filePath': f'{self.CALLSET_DIR}/mito_callset.mt', 'datasetType': 'MITO', 'genomeVersion': 'GRCh38'}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [f'Data file or path {self.CALLSET_DIR}/mito_callset.mt is not found.'])

        body['datasetType'] = 'SV'
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], [
            'Invalid VCF file format - file path must end with .bed or .bed.gz or .vcf or .vcf.gz or .vcf.bgz',
        ])

        body['filePath'] = f'{self.CALLSET_DIR}/sv_callset.vcf'
        vcf_file_rows = [
            '##fileformat=VCFv4.3\n',
            '##INFO=<ID=AA,Number=1,Type=String,Description="Ancestral Allele">',
            '##INFO=<ID=AC,Number=A,Type=Integer,Description="Allele count in genotypes, for each ALT allele, in the same order as listed">\n',
            '##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency, for each ALT allele, in the same order as listed">\n',
            '##INFO=<ID=AN,Number=1,Type=Integer,Description="Total number of alleles in called genotypes">\n',
            '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Approximate read depth (reads with MQ=255 or with bad mates are filtered)">\n',
            '#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG00735\tNA19675_1\tNA19679\n'
        ]
        self._add_file_iter(vcf_file_rows, is_gz=False)
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Missing required FORMAT field(s) GQ, GT'])

        self._set_file_not_found()

    def _assert_expected_delete_project(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'info': [
                'Deactivated search for 7 individuals',
                'Deleted all SNV_INDEL search data for project 1kg project n\xe5me with uni\xe7\xf8de',
            ],
        })
        self.assertEqual(EntriesSnvIndel.objects.filter(project_guid=PROJECT_GUID).count(), 0)
        self.assertEqual(ProjectGtStatsSnvIndel.objects.filter(project_guid=PROJECT_GUID).count(), 0)

        updated_seqr_pops_by_key = dict(AnnotationsSnvIndel.objects.all().join_seqr_pop().values_list('key', 'seqrPop'))
        self.assertDictEqual(updated_seqr_pops_by_key, {
            1: (2, 2, 1, 1),
            2: (1, 1, 0, 0),
            3: (0, 0, 0, 0),
            4: (0, 0, 0, 0),
            5: (1, 1, 0, 0),
            6: (0, 0, 0, 0),
            22: (0, 3, 0, 1),
        })

        project_samples = Sample.objects.filter(individual__family__project__guid=PROJECT_GUID, is_active=True)
        self.assertEqual(project_samples.filter(dataset_type='SNV_INDEL').count(), 0)
        self.assertEqual(project_samples.count(), 4)

    def _assert_expected_delete_family(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'info': [
                'Disabled search for 7 samples in the following 1 families: 2',
                'Triggered delete family data',
            ],
        })

        family_samples = Sample.objects.filter(individual__family_id=2, is_active=True)
        self.assertEqual(family_samples.count(),0)

        self.assertEqual(len(responses.calls), 1)
        self.assertDictEqual(json.loads(responses.calls[-1].request.body), {
            'project_guid': 'R0001_1kg',
            'family_guids': ['F000002_2'],
        })

    def _assert_expected_airtable_errors(self, url):
        responses.replace(
            responses.GET, 'https://api.airtable.com/v0/app3Y97xtbbaOopVR/Samples',
            json=INVALID_AIRTABLE_SAMPLE_RECORDS, status=200,
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {
            'error': 'The following samples are associated with misconfigured PDOs in Airtable: HG00731, NA21234',
        })
