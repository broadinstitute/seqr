import json
import mock
import responses
from copy import deepcopy

from django.db import transaction
from django.urls.base import reverse

from clickhouse_search.test_utils import VARIANT2, VARIANT3, VARIANT_LOOKUP_VARIANT, GCNV_LOOKUP_VARIANT, \
    SV_LOOKUP_VARIANT, SV_VARIANT4, GCNV_VARIANT4
from seqr.models import VariantSearchResults, LocusList, Project, VariantSearch
from seqr.utils.search.utils import InvalidSearchException
from seqr.views.apis.variant_search_api import query_variants_handler, query_single_variant_handler, vlm_lookup_handler, \
    export_variants_handler, search_context_handler, get_saved_search_handler, create_saved_search_handler, \
    update_saved_search_handler, delete_saved_search_handler, get_variant_gene_breakdown, variant_lookup_handler
from seqr.views.utils.test_utils import AuthenticationTestCase, VARIANTS,\
    GENE_VARIANT_FIELDS, GENE_VARIANT_DISPLAY_FIELDS, LOCUS_LIST_FIELDS, FAMILY_FIELDS, \
    PA_LOCUS_LIST_FIELDS, INDIVIDUAL_FIELDS, FUNCTIONAL_FIELDS, IGV_SAMPLE_FIELDS, FAMILY_NOTE_FIELDS, ANALYSIS_GROUP_FIELDS, \
    VARIANT_NOTE_FIELDS, TAG_FIELDS, MATCHMAKER_SUBMISSION_FIELDS, SAVED_VARIANT_DETAIL_FIELDS, DYNAMIC_ANALYSIS_GROUP_FIELDS

LOCUS_LIST_GUID = 'LL00049_pid_genes_autosomal_do'
PROJECT_GUID = 'R0001_1kg'
SEARCH_HASH = 'd380ed0fd28c3127d07a64ea2ba907d7'
SEARCH = {'filters': {}, 'inheritance': None}
PROJECT_FAMILIES = [{'projectGuid': PROJECT_GUID, 'familyGuids': ['F000001_1', 'F000002_2']}]

ALL_VARIANTS = VARIANTS + [VARIANT2, VARIANT3]

VARIANTS_WITH_DISCOVERY_TAGS = deepcopy(ALL_VARIANTS)
DISCOVERY_TAGS = [{
    'savedVariant': {
        'variantGuid': 'SV0000006_1248367227_r0003_tes',
        'familyGuid': 'F000012_12',
        'projectGuid': 'R0003_test',
    },
    'tagGuid': 'VT1726961_2103343353_r0003_tes',
    'name': 'Tier 1 - Novel gene and phenotype',
    'category': 'CMG Discovery Tags',
    'color': '#03441E',
    'searchHash': None,
    'metadata': None,
    'lastModifiedDate': '2018-05-29T16:32:51.449Z',
    'createdBy': None,
}]
VARIANTS_WITH_DISCOVERY_TAGS[2]['discoveryTags'] = DISCOVERY_TAGS

SINGLE_FAMILY_VARIANT = deepcopy(VARIANTS[0])
SINGLE_FAMILY_VARIANT['familyGuids'] = ['F000001_1']

PROJECT_CONTEXT_FIELDS = {'locusListGuids', 'datasetTypes', 'analysisGroupsLoaded', 'projectGuid', 'name'}

PROJECT_TAG_TYPE_FIELDS = {'projectGuid', 'genomeVersion', 'variantTagTypes', 'variantFunctionalTagTypes'}

EXPECTED_TAG = {k: mock.ANY for k in TAG_FIELDS}
expected_functional_tag = {k: mock.ANY for k in FUNCTIONAL_FIELDS}
expected_aip_tag = {
    'structuredMetadata': {
        '4': {'date': '2023-11-15', 'name': 'de Novo'},
        'support': {'date': '2023-11-15', 'name': 'High in Silico Scores'},
    },
    **EXPECTED_TAG,
}
del expected_aip_tag['metadata']
EXPECTED_GENE = {k: mock.ANY for k in GENE_VARIANT_FIELDS}
EXPECTED_GENE['locusListGuids'] = []
expected_pa_gene = deepcopy(EXPECTED_GENE)
expected_pa_gene['locusListGuids'] = ['LL00049_pid_genes_autosomal_do']
expected_pa_gene['panelAppDetail'] = mock.ANY
EXPECTED_SAVED_VARIANT = {k: mock.ANY for k in SAVED_VARIANT_DETAIL_FIELDS}
EXPECTED_SAVED_VARIANT.update( {'key': mock.ANY, 'mainTranscriptId': mock.ANY})
expected_detail_saved_variant = deepcopy(EXPECTED_SAVED_VARIANT)
expected_detail_saved_variant['mmeSubmissions'] = [
    {'geneId': 'ENSG00000135953', 'submissionGuid': 'MS000001_na19675', 'variantGuid': 'SV0000001_2103343353_r0390_100'},
]
expected_detail_saved_variant['mainTranscriptId'] = mock.ANY

EXPECTED_EXOMISER_DATA = [
    {'diseaseId': 'OMIM:219800', 'diseaseName': 'Cystinosis, nephropathic', 'rank': 2,
     'scores': {'exomiser_score': 0.969347946, 'phenotype_score': 0.443567539,
                'variant_score': 0.999200702}},
    {'diseaseId': 'OMIM:618460', 'diseaseName': 'Khan-Khan-Katsanis syndrome', 'rank': 1,
     'scores': {'exomiser_score': 0.977923765, 'phenotype_score': 0.603998205,
                'variant_score': 1}},
]

EXPECTED_LIRICAL_DATA = [
    {'diseaseId': 'OMIM:219800', 'diseaseName': 'Cystinosis, nephropathic', 'rank': 1,
     'scores': {'compositeLR': 0.003, 'post_test_probability': 0}},
]

EXPECTED_SEARCH_RESPONSE = {
    'searchedVariants': ALL_VARIANTS,
    'savedVariantsByGuid': {
        'SV0000001_2103343353_r0390_100': expected_detail_saved_variant,
        'SV0000002_1248367227_r0390_100': EXPECTED_SAVED_VARIANT,
    },
    'genesById': {
        'ENSG00000227232': expected_pa_gene, 'ENSG00000268903': EXPECTED_GENE, 'ENSG00000233653': EXPECTED_GENE,
        'ENSG00000177000': mock.ANY, 'ENSG00000097046': mock.ANY,
    },
    'search': {
        'search': SEARCH,
        'projectFamilies': [{'projectGuid': PROJECT_GUID, 'familyGuids': mock.ANY}],
        'totalResults': 5,
    },
    'variantTagsByGuid': {
        'VT1708633_2103343353_r0390_100': EXPECTED_TAG, 'VT1726945_2103343353_r0390_100': EXPECTED_TAG,
        'VT1726970_2103343353_r0004_tes': EXPECTED_TAG, 'VT1726961_2103343353_r0390_100': EXPECTED_TAG,
        'VT1726985_2103343353_r0390_100': expected_aip_tag,
    },
    'variantNotesByGuid': {
        'VN0714935_2103343353_r0390_100': {k: mock.ANY for k in VARIANT_NOTE_FIELDS},
        'VN0714937_2103343353_r0390_100': {k: mock.ANY for k in VARIANT_NOTE_FIELDS},
    },
    'variantFunctionalDataByGuid': {
        'VFD0000023_1248367227_r0390_10': expected_functional_tag, 'VFD0000024_1248367227_r0390_10': expected_functional_tag,
        'VFD0000025_1248367227_r0390_10': expected_functional_tag, 'VFD0000026_1248367227_r0390_10': expected_functional_tag,
    },
    'locusListsByGuid': {LOCUS_LIST_GUID: {'intervals': mock.ANY}},
    'rnaSeqData': {
        'I000001_na19675': {'outliers': {'ENSG00000268903': mock.ANY}, 'spliceOutliers': {'ENSG00000268903': mock.ANY}},
    },
    'phenotypeGeneScores': {
        'I000001_na19675': {'ENSG00000268903': {'exomiser': EXPECTED_EXOMISER_DATA}},
        'I000002_na19678': {'ENSG00000268903': {'lirical': EXPECTED_LIRICAL_DATA}},
    },
    'mmeSubmissionsByGuid': {'MS000001_na19675': {k: mock.ANY for k in MATCHMAKER_SUBMISSION_FIELDS}},
    'familiesByGuid': {'F000001_1': {'tpmGenes': ['ENSG00000227232']}},
    'totalSampleCounts': {'MITO': {'WES': 1}, 'SNV_INDEL': {'WES': 7}, 'SV': {'WES': 3}},
}

EXPECTED_TRANSCRIPTS_RESPONSE = {
    'transcriptsById': {'ENST00000624735': {'isManeSelect': False, 'refseqId': None, 'transcriptId': 'ENST00000624735'}},
}

EXPECTED_SEARCH_CONTEXT_RESPONSE = {
    'savedSearchesByGuid': {
        'VS0079516_': mock.ANY, 'VS0079525_': mock.ANY, 'VS0079517_': mock.ANY, 'VS0145435_': mock.ANY,
    },
    'projectsByGuid': {PROJECT_GUID: mock.ANY},
    'familiesByGuid': mock.ANY,
    'analysisGroupsByGuid': {'AG0000183_test_group': mock.ANY, 'AG0000185_accepted': mock.ANY, 'DAG0000001_unsolved': mock.ANY, 'DAG0000002_my_new_cases': mock.ANY},
    'locusListsByGuid': {LOCUS_LIST_GUID: mock.ANY, 'LL00005_retina_proteome': mock.ANY},
}

EXPECTED_SEARCH_FAMILY_CONTEXT = {
    'familiesByGuid': {'F000001_1': mock.ANY, 'F000002_2': mock.ANY},
    'individualsByGuid': mock.ANY,
    'igvSamplesByGuid': mock.ANY,
    'locusListsByGuid': {LOCUS_LIST_GUID: mock.ANY},
    'familyNotesByGuid': mock.ANY,
}

MOCK_TOKEN = 'mock_token' # nosec
MOCK_CLIENT_ID = 'mock_client_id'
VLM_CLIENTS_RESPONSE = [
    {'client_id': MOCK_CLIENT_ID, 'name': 'Self', 'client_metadata': {'match_url': 'https://self.com'}},
    {'client_id': 'client1', 'name': 'Node 1', 'client_metadata': {'match_url': 'https://node1.com'}},
    {'client_id': 'client2', 'name': 'Node 2', 'client_metadata': {'match_url': 'https://node2.com'}},
    {'client_id': 'client1', 'name': 'Node 3', 'client_metadata': {'other_url': 'https://node3.com'}},
    {'client_id': 'client1', 'name': 'Node 4'},
]
VLM_MATCH_URL = 'https://node1.com/variant_lookup/1-10439-AC-A'
VLM_MATCH_RESPONSE = {
    'beaconHandovers': [
        {
            'handoverType': {'id': 'Test Node', 'label': 'Test Node browser'},
            'url': VLM_MATCH_URL,
        },
        {
            'handoverType': {'id': 'Test SecondaryDB', 'label': 'Test secondary database'},
            'url': f'{VLM_MATCH_URL}/secondarydb',
        }
    ],
    'meta': {
        'apiVersion': 'v1.0',
        'beaconId': 'com.gnx.beacon.v2',
        'returnedSchemas': [
            {
                'entityType': 'genomicVariant',
                'schema': 'ga4gh-beacon-variant-v2.0.0',
            }
        ]
    },
    'responseSummary': {
        'exists': True,
        'total': 30,
    },
    'response': {
        'resultSets': [
            {
                'exists': True,
                'id': 'Test Node Homozygous',
                'results': [],
                'resultsCount': 7,
                'setType': 'genomicVariant'
            },
            {
                'exists': True,
                'id': 'Test Node Heterozygous',
                'results': [],
                'resultsCount': 23,
                'setType': 'genomicVariant'
            },
            {
                'exists': False,
                'id': 'Test SecondaryDB Homozygous',
                'results': [],
                'resultsCount': 0,
                'setType': 'genomicVariant'
            },
            {
                'exists': True,
                'id': 'Test SecondaryDB Heterozygous',
                'results': [],
                'resultsCount': 2,
                'setType': 'genomicVariant'
            },
        ],
    }
}
VLM_MATCH_RESPONSE_2 = {
    'beaconHandovers': [
        {
            'handoverType': {'id': 'Node2', 'label': ''},
            'url': None,
            'email': 'vlm_test@node2.org',
        }
    ],
    'meta': {
        'apiVersion': 'v1.0',
        'beaconId': 'com.gnx.beacon.v2',
        'returnedSchemas': [
            {
                'entityType': 'genomicVariant',
                'schema': 'ga4gh-beacon-variant-v2.0.0',
            }
        ]
    },
    'responseSummary': {
        'exists': True,
        'total': 30,
    },
    'response': {
        'resultSets': [
            {
                'exists': True,
                'id': 'Homozygous',
                'results': [],
                'resultsCount': 1,
                'setType': 'genomicVariant'
            },
            {
                'exists': False,
                'id': 'Heterozygous',
                'results': [],
                'resultsCount': 0,
                'setType': 'genomicVariant'
            },
        ],
    }
}

def _get_es_variants(results_model, **kwargs):
    results_model.save()
    return deepcopy(ALL_VARIANTS), len(ALL_VARIANTS)


def _get_empty_es_variants(results_model, **kwargs):
    results_model.save()
    return [], 0


COMP_HET_VARAINTS = [[VARIANTS[2], VARIANTS[1]]]
def _get_compound_het_es_variants(results_model, **kwargs):
    results_model.save()
    return deepcopy(COMP_HET_VARAINTS), 1


@mock.patch('seqr.views.utils.permissions_utils.safe_redis_get_json', lambda *args: None)
class VariantSearchAPITest(AuthenticationTestCase):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data', 'variant_searches', 'clickhouse_saved_variants']

    def _assert_expected_search_context(self, response_json):
        self.assertSetEqual(set(response_json), set(EXPECTED_SEARCH_CONTEXT_RESPONSE))
        self.assertDictEqual(response_json, EXPECTED_SEARCH_CONTEXT_RESPONSE)

        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID].keys()), PROJECT_CONTEXT_FIELDS)
        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID]['datasetTypes']), {'SNV_INDEL', 'SV', 'MITO'})

        locus_list_fields = deepcopy(LOCUS_LIST_FIELDS)
        locus_list_fields.update(PA_LOCUS_LIST_FIELDS)
        locus_list_fields.remove('numEntries')
        locus_list_fields.remove('canEdit')
        self.assertSetEqual(set(response_json['locusListsByGuid'][LOCUS_LIST_GUID].keys()), locus_list_fields)
        self.assertSetEqual(set(response_json['analysisGroupsByGuid']['AG0000183_test_group'].keys()), ANALYSIS_GROUP_FIELDS)
        self.assertSetEqual(set(response_json['analysisGroupsByGuid']['DAG0000001_unsolved'].keys()), DYNAMIC_ANALYSIS_GROUP_FIELDS)

        self.assertEqual(len(response_json['familiesByGuid']), 11)
        self.assertSetEqual(set(response_json['familiesByGuid']['F000001_1'].keys()), {
            'projectGuid', 'familyGuid', 'displayName', 'analysisStatus', 'analysedBy', 'assignedAnalyst', 'sampleTypes',
        })
        self.assertDictEqual(response_json['familiesByGuid']['F000001_1'], {
            'projectGuid': PROJECT_GUID, 'familyGuid': 'F000001_1', 'displayName': '1', 'analysisStatus': 'Q',
            'assignedAnalyst': None, 'sampleTypes': [{'datasetType': 'SNV_INDEL', 'sampleType': 'WES', 'isActive': True}],
            'analysedBy': [{'createdBy': 'Test No Access User', 'dataType': 'SNP', 'lastModifiedDate': '2022-07-22T19:27:08.563+00:00'}],
        })

    def test_search_context(self):
        search_context_url = reverse(search_context_handler)
        self.check_collaborator_login(search_context_url, request_data={'familyGuid': 'F000001_1'})

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'foo': 'bar'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid context params: {"foo": "bar"}')

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'familyGuid': 'bar'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid context params: {"familyGuid": "bar"}')

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'projectGuid': PROJECT_GUID}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'familyGuid': 'F000001_1'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'analysisGroupGuid': 'AG0000183_test_group'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

        # Test fetching multiple projects where a locus list is contained in a non-included project
        LocusList.objects.get(guid=LOCUS_LIST_GUID).projects.add(Project.objects.get(id=2))

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'projectCategoryGuid': 'PC000003_test_category_name'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        expected_response = {
            'savedSearchesByGuid': mock.ANY,
            'projectCategoriesByGuid': {'PC000003_test_category_name': mock.ANY},
        }
        expected_response.update(deepcopy(EXPECTED_SEARCH_CONTEXT_RESPONSE))
        expected_response['projectsByGuid']['R0003_test'] = mock.ANY
        self.assertSetEqual(set(response_json), set(expected_response))
        self.assertDictEqual(response_json, expected_response)
        self.assertEqual(len(response_json['savedSearchesByGuid']), 4)
        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID].keys()), PROJECT_CONTEXT_FIELDS)
        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID]['datasetTypes']), {'SNV_INDEL', 'SV', 'MITO'})
        self.assertSetEqual(set(response_json['projectsByGuid']['R0003_test']['datasetTypes']), {'SNV_INDEL'})
        self.assertEqual(len(response_json['familiesByGuid']), 13)

        # Test search hash context
        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': SEARCH_HASH}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search hash: {}'.format(SEARCH_HASH))

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': SEARCH_HASH, 'searchParams': {'search': SEARCH}}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search: no projects/ families specified')

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': SEARCH_HASH, 'searchParams': {'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH}}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': SEARCH_HASH}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

        # Test all project search context
        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': 'djd29394hfw2njr2hod2', 'searchParams': {'allGenomeProjectFamilies': '37', 'search': SEARCH}}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

    @mock.patch('seqr.views.apis.variant_search_api.variant_lookup')
    def test_variant_lookup(self, mock_variant_lookup):
        # TODO
        response_variant = deepcopy(VARIANT_LOOKUP_VARIANT)
        mock_variant_lookup.side_effect = lambda *args, **kwargs: [deepcopy(response_variant)]

        url = f'{reverse(variant_lookup_handler)}?variantId=1-10439-AC-A&genomeVersion=38&affectedOnly=true'
        self.check_require_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        expected_variant = {
            **VARIANT_LOOKUP_VARIANT,
            'familyGuids': [],
            'lookupFamilyGuids': ['F0_1-10439-AC-A', 'F1_1-10439-AC-A', 'F2_1-10439-AC-A'],
            'liftedFamilyGuids': ['F2_1-10439-AC-A'],
            'genotypes': {
                'I0_F0_1-10439-AC-A': [
                    {'ab': 0.0, 'dp': 60, 'gq': 20, 'numAlt': 0, 'filters': [], 'sampleType': 'WES'},
                    {'ab': 0.0, 'dp': 60, 'gq': 20, 'numAlt': 0, 'filters': [], 'sampleType': 'WGS'},
                ],
                'I1_F0_1-10439-AC-A': [
                    {'ab': 0.0, 'dp': 24, 'gq': 0, 'numAlt': 0, 'filters': [], 'sampleType': 'WES'},
                    {'ab': 0.0, 'dp': 24, 'gq': 99, 'numAlt': 1, 'filters': [], 'sampleType': 'WGS'},
                ],
                'I2_F0_1-10439-AC-A': [
                    {'ab': 0.5, 'dp': 10, 'gq': 99, 'numAlt': 1, 'filters': [], 'sampleType': 'WES'},
                    {'ab': 0.5, 'dp': 10, 'gq': 99, 'numAlt': 2, 'filters': [], 'sampleType': 'WGS'},
                ],
                'I0_F1_1-10439-AC-A': [
                    {'ab': 1.0, 'dp': 6, 'gq': 16, 'numAlt': 2, 'filters': [], 'sampleType': 'WES'},
                    {'ab': 1.0, 'dp': 6, 'gq': 16, 'numAlt': 2, 'filters': [], 'sampleType': 'WGS'},
                ],
                'I0_F2_1-10439-AC-A': {'ab': 0.531, 'dp': 27, 'gq': 87, 'numAlt': 1, 'filters': [], 'sampleType': 'WGS'},
            },
        }
        del expected_variant['familyGenotypes']
        expected_individuals = {
            'I0_F0_1-10439-AC-A': {
                'affected': 'N', 'familyGuid': 'F0_1-10439-AC-A', 'features': [],
                'individualGuid': 'I0_F0_1-10439-AC-A', 'sex': 'F',
                'vlmContactEmail': 'test@broadinstitute.org,vlm@broadinstitute.org',
            },
            'I0_F1_1-10439-AC-A': {
                'affected': 'A', 'familyGuid': 'F1_1-10439-AC-A', 'individualGuid': 'I0_F1_1-10439-AC-A', 'sex': 'M',
                'features': [{'category': 'HP:0001626', 'label': '1 terms'}, {'category': 'Other', 'label': '1 terms'}],
                'vlmContactEmail': 'seqr-test@gmail.com,test@broadinstitute.org',
            },
            'I0_F2_1-10439-AC-A': {
                'affected': 'A', 'familyGuid': 'F2_1-10439-AC-A', 'features': [],
                'individualGuid': 'I0_F2_1-10439-AC-A', 'sex': 'F',
                'vlmContactEmail': 'vlm@broadinstitute.org',
            },
            'I1_F0_1-10439-AC-A': {
                'affected': 'N', 'familyGuid': 'F0_1-10439-AC-A', 'features': [],
                'individualGuid': 'I1_F0_1-10439-AC-A', 'sex': 'M',
                'vlmContactEmail': 'test@broadinstitute.org,vlm@broadinstitute.org',
            },
            'I2_F0_1-10439-AC-A': {
                'affected': 'A', 'familyGuid': 'F0_1-10439-AC-A', 'individualGuid': 'I2_F0_1-10439-AC-A', 'sex': 'X0',
                'features': [{'category': 'HP:0000707', 'label': '1 terms'},
                             {'category': 'HP:0001626', 'label': '1 terms'}],
                'vlmContactEmail': 'test@broadinstitute.org,vlm@broadinstitute.org',
            },
        }
        expected_body = self._expected_lookup_body(expected_individuals, [expected_variant], is_build_38=True)
        self.assertDictEqual(response.json(), expected_body)
        mock_variant_lookup.assert_called_with(self.no_access_user, '1-10439-AC-A', '38', sample_type=None, affected_only=True, hom_only=False)

        response_variant['transcripts'] = VARIANTS[0]['transcripts']
        expected_variant['transcripts'] = VARIANTS[0]['transcripts']
        expected_gene_body = {
            'genesById': {'ENSG00000227232': EXPECTED_GENE, 'ENSG00000268903': EXPECTED_GENE},
        }
        expected_body.update(expected_gene_body)
        if 'transcriptsById' in EXPECTED_SEARCH_RESPONSE:
            expected_body['transcriptsById'] = EXPECTED_SEARCH_RESPONSE['transcriptsById']

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), expected_body)

        response_variant['variantId'] = '1-248367227-TC-T'
        response_variant['genomeVersion'] = '37'
        self.login_manager()
        response = self.client.get(url.replace("38", "37") + '&homOnly=true')
        self.assertEqual(response.status_code, 200)

        individual_guid_map = [
            ('I000006_hg00733', 'I0_F0_1-10439-AC-A', {'sampleId': 'HG00733', 'familyGuid': 'F000002_2'}),
            ('I000005_hg00732', 'I1_F0_1-10439-AC-A', {'sampleId': 'HG00732', 'familyGuid': 'F000002_2'}),
            ('I000004_hg00731', 'I2_F0_1-10439-AC-A', {'sampleId': 'HG00731', 'familyGuid': 'F000002_2'}),
            ('I000015_na20885', 'I0_F1_1-10439-AC-A', {'sampleId': 'NA20885', 'familyGuid': 'F000011_11'}),
            ('I000018_na21234', 'I0_F2_1-10439-AC-A', {'sampleId': 'NA21234', 'familyGuid': 'F000014_14'}),
        ]
        expected_variant.update({
            'lookupFamilyGuids': ['F000002_2', 'F000011_11', 'F000014_14'],
            'liftedFamilyGuids': ['F000014_14'],
            'genotypes': {
                individual_guid: [
                    {**sample_genotype, **genotype, 'individualGuid': individual_guid} for sample_genotype in expected_variant['genotypes'][anon_individual_guid]
                ] if isinstance(expected_variant['genotypes'][anon_individual_guid], list) else {
                    **expected_variant['genotypes'][anon_individual_guid], **genotype, 'individualGuid': individual_guid,
                } for individual_guid, anon_individual_guid, genotype in individual_guid_map
            },
            'genomeVersion': '37',
            'variantId': '1-248367227-TC-T',
        })
        expected_individuals = {
            individual_guid: {
                **{k: mock.ANY for k in [*INDIVIDUAL_FIELDS, 'igvSampleGuids']},
                **{k: v for k, v in expected_individuals[anon_individual_guid].items()
                   if k not in {'individualGuid', 'familyGuid', 'features', 'vlmContactEmail'}},
            } for individual_guid, anon_individual_guid, _ in individual_guid_map
        }
        expected_individuals.update({individual_guid: mock.ANY for individual_guid in ['I000019_na21987', 'I000021_na21654']})
        expected_body = self._expected_lookup_body(
            expected_individuals, [expected_variant], include_context=True,
            project_guids=[PROJECT_GUID, 'R0003_test', 'R0004_non_analyst_project'],
            family_guids=['F000002_2', 'F000011_11', 'F000014_14'],
        )
        expected_body.update({
            k: {**EXPECTED_SEARCH_RESPONSE[k]} for k in {'mmeSubmissionsByGuid', 'variantTagsByGuid', 'variantNotesByGuid'}
        })
        expected_body['savedVariantsByGuid']= {
            k: v for k, v in EXPECTED_SEARCH_RESPONSE['savedVariantsByGuid'].items() if k in ['SV0000002_1248367227_r0390_100']
        }
        expected_body.update(expected_gene_body)
        expected_body['genesById']['ENSG00000227232'] = expected_pa_gene
        expected_body['mmeSubmissionsByGuid']['MS000018_P0004517'] = expected_body['mmeSubmissionsByGuid'].pop('MS000001_na19675')
        expected_body['savedVariantsByGuid']['SV0000006_1248367227_r0004_non'] = mock.ANY
        expected_body['variantTagsByGuid']['VT1726970_2103343353_r0004_tes'] = EXPECTED_TAG
        expected_body['variantTagsByGuid']['VT1726961_2103343353_r0005_tes'] = EXPECTED_TAG
        for k in ['VT1708633_2103343353_r0390_100', 'VT1726961_2103343353_r0390_100']:
            del expected_body['variantTagsByGuid'][k]
        expected_body['rnaSeqData']['I000019_na21987'] = {'outliers': {}, 'spliceOutliers': {'ENSG00000268903': mock.ANY}}

        self.assertDictEqual(response.json(), expected_body)
        mock_variant_lookup.assert_called_with(
            self.manager_user, '1-10439-AC-A', '37', sample_type=None, affected_only=True, hom_only=True,
        )

    def _expected_lookup_body(self, individuals_by_guid, variants, is_build_38=False, include_context=False, project_guids=None, family_guids=None):
        exclude_keys = {'searchedVariants', 'search', 'transcriptsById'}
        if not include_context:
            exclude_keys.update({'variantNotesByGuid', 'variantTagsByGuid', 'variantFunctionalDataByGuid'})
        expected_body = {
            **{k: {} for k in EXPECTED_SEARCH_RESPONSE if k not in exclude_keys},
            **{k: {} for k in EXPECTED_SEARCH_FAMILY_CONTEXT},
            'projectsByGuid': {
                p: {k: mock.ANY for k in PROJECT_TAG_TYPE_FIELDS} for p in project_guids or []
            },
            'familiesByGuid': {
                f: {k: mock.ANY for k in [*FAMILY_FIELDS, 'individualGuids']} for f in family_guids or []
            },
            'individualsByGuid': individuals_by_guid,
            'variants': variants,
        }
        if is_build_38:
            expected_body['omimIntervals'] = {}
        if include_context:
            expected_body.update({
                **EXPECTED_TRANSCRIPTS_RESPONSE,
                'locusListsByGuid': EXPECTED_SEARCH_CONTEXT_RESPONSE['locusListsByGuid'],
            })
        if 'totalSampleCounts' in EXPECTED_SEARCH_RESPONSE:
            expected_body['totalSampleCounts'] = {'SV': {'WGS': 3}} if is_build_38 else EXPECTED_SEARCH_RESPONSE['totalSampleCounts']
        return expected_body

    @mock.patch('seqr.views.apis.variant_search_api.variant_lookup')
    def test_sv_variant_lookup(self, mock_variant_lookup):
        # TODO
        lookup_variants = [
            {**GCNV_LOOKUP_VARIANT, 'familyGenotypes': {k: v for k, v in GCNV_LOOKUP_VARIANT['familyGenotypes'].items() if k != 'F000002_2_x'}},
            SV_LOOKUP_VARIANT,
        ]
        mock_variant_lookup.side_effect = lambda *args, **kwargs: [deepcopy(v) for v in lookup_variants]

        url = f'{reverse(variant_lookup_handler)}?variantId=phase2_DEL_chr14_4640&genomeVersion=37&sampleType=WGS'
        self.check_require_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        expected_gcnv_variant = {
            **GCNV_VARIANT4,
            'familyGuids': [],
            'lookupFamilyGuids': ['F0_suffix_140608_DUP'],
            'genotypes': {
                'I0_F0_suffix_140608_DUP': {
                    k: v for k, v in GCNV_VARIANT4['genotypes']['I000004_hg00731'].items()
                    if k not in {'familyGuid', 'individualGuid', 'sampleId'}
                },
                'I1_F0_suffix_140608_DUP': {
                    k: v for k, v in GCNV_VARIANT4['genotypes']['I000005_hg00732'].items()
                    if k not in {'familyGuid', 'individualGuid', 'sampleId'}
                },
                'I2_F0_suffix_140608_DUP': {
                    k: v for k, v in GCNV_VARIANT4['genotypes']['I000006_hg00733'].items()
                    if k not in {'familyGuid', 'individualGuid', 'sampleId'}
                },
            },
        }
        expected_sv_variant = {
            **SV_VARIANT4,
            'familyGuids': [],
            'lookupFamilyGuids': ['F0_phase2_DEL_chr14_4640'],
            'genotypes': {
                'I0_F0_phase2_DEL_chr14_4640': {
                    k: v for k, v in SV_VARIANT4['genotypes']['I000018_na21234'].items()
                    if k not in {'familyGuid', 'individualGuid', 'sampleId'}
                },
                'I1_F0_phase2_DEL_chr14_4640': {
                    k: v for k, v in SV_VARIANT4['genotypes']['I000019_na21987'].items()
                    if k not in {'familyGuid', 'individualGuid', 'sampleId'}
                },
                'I2_F0_phase2_DEL_chr14_4640': {
                    k: v for k, v in SV_VARIANT4['genotypes']['I000021_na21654'].items()
                    if k not in {'familyGuid', 'individualGuid', 'sampleId'}
                },
            },
        }
        expected_individuals = {
            'I0_F0_phase2_DEL_chr14_4640': {
                'affected': 'A', 'familyGuid': 'F0_phase2_DEL_chr14_4640', 'features': [],
                'individualGuid': 'I0_F0_phase2_DEL_chr14_4640', 'sex': 'F',
                'vlmContactEmail': 'vlm@broadinstitute.org',
            },
            'I0_F0_suffix_140608_DUP': {
                'affected': 'A', 'familyGuid': 'F0_suffix_140608_DUP', 'individualGuid': 'I0_F0_suffix_140608_DUP',
                'features': [{'category': 'HP:0000707', 'label': '1 terms'}, {'category': 'HP:0001626', 'label': '1 terms'}],
                'sex': 'X0', 'vlmContactEmail': 'test@broadinstitute.org,vlm@broadinstitute.org',
            },
            'I1_F0_phase2_DEL_chr14_4640': {
                'affected': 'A', 'familyGuid': 'F0_phase2_DEL_chr14_4640', 'features': [],
                'individualGuid': 'I1_F0_phase2_DEL_chr14_4640', 'sex': 'M',
                'vlmContactEmail': 'vlm@broadinstitute.org',
            },
            'I1_F0_suffix_140608_DUP': {
                'affected': 'N', 'familyGuid': 'F0_suffix_140608_DUP', 'individualGuid': 'I1_F0_suffix_140608_DUP',
                'sex': 'M','features': [], 'vlmContactEmail': 'test@broadinstitute.org,vlm@broadinstitute.org',
            },
            'I2_F0_phase2_DEL_chr14_4640': {
                'affected': 'N', 'familyGuid': 'F0_phase2_DEL_chr14_4640', 'features': [],
                'individualGuid': 'I2_F0_phase2_DEL_chr14_4640', 'sex': 'F',
                'vlmContactEmail': 'vlm@broadinstitute.org',
            },
            'I2_F0_suffix_140608_DUP': {
                'affected': 'N', 'familyGuid': 'F0_suffix_140608_DUP', 'individualGuid': 'I2_F0_suffix_140608_DUP',
                'sex': 'F', 'features': [], 'vlmContactEmail': 'test@broadinstitute.org,vlm@broadinstitute.org',
            },
        }
        expected_body = self._expected_lookup_body(expected_individuals,[expected_gcnv_variant, expected_sv_variant])
        self.assertDictEqual(response.json(), expected_body)
        mock_variant_lookup.assert_called_with(
            self.no_access_user, 'phase2_DEL_chr14_4640', '37', sample_type='WGS', affected_only=False, hom_only=False,
        )

        self.login_manager()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        expected_gcnv_variant.update({
            'lookupFamilyGuids': GCNV_VARIANT4['familyGuids'],
            'genotypes': GCNV_VARIANT4['genotypes'],
        })
        expected_sv_variant.update({
            'lookupFamilyGuids': SV_VARIANT4['familyGuids'],
            'genotypes': SV_VARIANT4['genotypes'],
        })
        expected_individuals = {
            i: {k: mock.ANY for k in [*INDIVIDUAL_FIELDS, 'igvSampleGuids']} for i in [
                'I000004_hg00731', 'I000005_hg00732', 'I000006_hg00733', 'I000018_na21234', 'I000019_na21987', 'I000021_na21654',
            ]
        }
        expected_body = self._expected_lookup_body(
            expected_individuals,
            [expected_gcnv_variant, expected_sv_variant],
            project_guids=[PROJECT_GUID, 'R0004_non_analyst_project'],
            family_guids=['F000002_2', 'F000014_14'],
            include_context=True,
        )
        del expected_body['transcriptsById']
        self.assertDictEqual(response.json(), expected_body)
        mock_variant_lookup.assert_called_with(self.manager_user, 'phase2_DEL_chr14_4640', '37', sample_type='WGS', affected_only=False, hom_only=False,)

    @mock.patch('seqr.views.utils.vlm_utils.VLM_CLIENT_SECRET', 'abc123')
    @mock.patch('seqr.views.utils.vlm_utils.VLM_CLIENT_ID', MOCK_CLIENT_ID)
    @mock.patch('seqr.utils.redis_utils.redis.StrictRedis')
    @responses.activate
    def test_vlm_lookup(self, mock_redis):
        mock_cache = {}
        mock_redis.return_value.get.side_effect = mock_cache.get
        mock_redis.return_value.set.side_effect = lambda key, val, **kwargs: mock_cache.update({key: val})
        responses.add(
            responses.POST, 'https://vlm-auth.us.auth0.com/oauth/token', json={'access_token': MOCK_TOKEN},
        )
        responses.add(
            responses.GET, 'https://vlm-auth.us.auth0.com/api/v2/clients?fields=client_id,name,client_metadata&is_global=false',
            json=VLM_CLIENTS_RESPONSE,
        )
        match_url_template = 'https://{}.com/?assemblyId=GRCh38&referenceName=1&start=10439&referenceBases=C&alternateBases=A'
        node_1_url = match_url_template.format('node1')
        responses.add(responses.GET, node_1_url, json=VLM_MATCH_RESPONSE)
        node_2_url = match_url_template.format('node2')
        responses.add(responses.GET, node_2_url, status=400)

        base_url = reverse(vlm_lookup_handler)
        url = f'{base_url}?variantId=1-10439-C-A&genomeVersion=38'
        self.check_require_login(url)

        response = self.client.get(f'{base_url}?variantId=phase2_DEL_chr14_464')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'VLM lookup is not supported for SVs'})

        response = self.client.get(f'{base_url}?variantId=8-10439--ATGS')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Unable to search VLM for invalid allele(s): "", "ATGS"'})

        response = self.client.get(f'{base_url}?variantId=1-10439-AC-A')
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'VLM lookup is not supported for InDels'})

        self.reset_logs()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        expected_body = {'vlmMatches': {
            'Node 1': {
                'Test Node': {'url': VLM_MATCH_URL, 'counts': {'Heterozygous': 23, 'Homozygous': 7}},
                'Test SecondaryDB': {'url': f'{VLM_MATCH_URL}/secondarydb', 'counts': {'Heterozygous': 2, 'Homozygous': 0}},
            }
        }}
        self.assertDictEqual(response.json(), expected_body)

        self.assertEqual(len(responses.calls), 4)
        self.assertFalse('Authorization' in responses.calls[0].request.headers, {})
        self.assertSetEqual({call.request.headers['Authorization'] for call in responses.calls[1:]}, {'Bearer mock_token'})

        expected_params = {
            'assemblyId': 'GRCh38',
            'alternateBases': 'A',
            'referenceBases': 'C',
            'referenceName': '1',
            'start': 10439,
        }
        expected_logs = [
            ('VLM match request to Node 1', {'detail': expected_params}),
            ('VLM match request to Node 2', {'detail': expected_params}),
            (f'VLM match error for Node 2: 400 Client Error: Bad Request for url: {node_2_url}', {
                'severity': 'ERROR',
                '@type': 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent',
                'detail': expected_params,
            }),
        ]
        self.assert_json_logs(self.no_access_user, expected_logs)

        # test with cached token and clients
        self.reset_logs()
        responses.calls.reset()
        responses.add(responses.GET, node_2_url, json=VLM_MATCH_RESPONSE_2)
        expected_body['vlmMatches']['Node 2'] = {
            'Node2': {'url': 'mailto:vlm_test@node2.org', 'counts': {'Heterozygous': 0, 'Homozygous': 1}}
        }
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), expected_body)
        self.assertEqual(len(responses.calls), 2)
        self.assertListEqual([call.request.url for call in responses.calls], [node_1_url, node_2_url])
        self.assertSetEqual({call.request.headers['Authorization'] for call in responses.calls}, {'Bearer mock_token'})
        self.assert_json_logs(None, [
            ('Loaded VLM_TOKEN from redis', None),
            ('Loaded VLM_CLIENTS from redis', None),
        ])
        self.assert_json_logs(self.no_access_user, expected_logs[:2], offset=2)


    def test_saved_search(self):
        get_saved_search_url = reverse(get_saved_search_handler)
        self.check_require_login(get_saved_search_url)

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 4)

        create_saved_search_url = reverse(create_saved_search_handler)

        response = self.client.post(create_saved_search_url, content_type='application/json', data='{}')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, '"Name" is required')

        body = {'name': 'Test Search'}

        invalid_body = {'inheritance': {'filter': {'genotype': {'indiv_1': 'ref_alt'}}}}
        invalid_body.update(body)
        response = self.client.post(create_saved_search_url, content_type='application/json', data=json.dumps(invalid_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Saved searches cannot include custom genotype filters')

        body.update(SEARCH)
        response = self.client.post(create_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        saved_searches = response.json()['savedSearchesByGuid']
        self.assertEqual(len(saved_searches), 1)
        search_guid = next(iter(saved_searches))
        self.assertDictEqual(saved_searches[search_guid], {
            'savedSearchGuid': search_guid, 'name': 'Test Search', 'search': SEARCH, 'createdById': 13, 'order': None,
        })

        # Test no errors if duplicate searches get created
        dup_search_guid = VariantSearch.objects.create(search=SEARCH, created_by=self.no_access_user).guid
        response = self.client.post(create_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(list(response.json()['savedSearchesByGuid'].keys()), [search_guid])
        self.assertIsNone(VariantSearch.objects.filter(guid=dup_search_guid).first())

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 5)

        # Test cannot save different searches with the same name
        body['filters'] = {'test': 'filter'}
        with transaction.atomic():
            response = self.client.post(create_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Saved search with name "Test Search" already exists')

        # Test update endpoint
        update_saved_search_url = reverse(update_saved_search_handler, args=[search_guid])
        body['name'] = None
        response = self.client.post(update_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, '"Name" is required')

        body['name'] = 'Updated Test Search'
        response = self.client.post(update_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json()['savedSearchesByGuid'][search_guid], {
            'savedSearchGuid': search_guid, 'name': 'Updated Test Search', 'search': SEARCH, 'createdById': 13, 'order': None,
        })

        delete_saved_search_url = reverse(delete_saved_search_handler, args=[search_guid])
        response = self.client.get(delete_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'savedSearchesByGuid': {search_guid: None}})

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 4)

        global_saved_search_guid = next(iter(response.json()['savedSearchesByGuid']))

        update_saved_search_url = reverse(update_saved_search_handler, args=[global_saved_search_guid])
        response = self.client.post(update_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 403)

        delete_saved_search_url = reverse(delete_saved_search_handler, args=[global_saved_search_guid])
        response = self.client.get(delete_saved_search_url)
        self.assertEqual(response.status_code, 403)

    def test_search_results_redirect(self):
        response = self.client.get('/report/custom_search/6ebb895dfca0f63c34be1ca59d950205?page=2&sort=cadd')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, '/variant_search/results/6ebb895dfca0f63c34be1ca59d950205?page=2&sort=cadd')
