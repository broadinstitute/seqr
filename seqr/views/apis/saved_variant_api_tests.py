from copy import deepcopy
import json
import mock

from django.urls.base import reverse

from seqr.models import SavedVariant, VariantNote, VariantTag, VariantFunctionalData, Family
from seqr.views.apis.saved_variant_api import saved_variant_data, create_variant_note_handler, create_saved_variant_handler, \
    update_variant_note_handler, delete_variant_note_handler, update_variant_tags_handler, update_saved_variant_json, \
    update_variant_main_transcript, update_variant_functional_data_handler, update_variant_acmg_classification_handler
from seqr.views.utils.orm_to_json_utils import get_json_for_saved_variants
from seqr.views.utils.test_utils import AuthenticationTestCase, SAVED_VARIANT_DETAIL_FIELDS, TAG_FIELDS, GENE_VARIANT_FIELDS, \
    TAG_TYPE_FIELDS, LOCUS_LIST_FIELDS, PA_LOCUS_LIST_FIELDS, FAMILY_FIELDS, INDIVIDUAL_FIELDS, IGV_SAMPLE_FIELDS, \
    FAMILY_NOTE_FIELDS, MATCHMAKER_SUBMISSION_FIELDS, AnvilAuthenticationTestCase


PROJECT_GUID = 'R0001_1kg'
VARIANT_GUID = 'SV0000001_2103343353_r0390_100'
LOCUS_LIST_GUID = 'LL00049_pid_genes_autosomal_do'
GENE_GUID = 'ENSG00000135953'
VARIANT_GUID_2 = 'SV0000002_1248367227_r0390_100'
NO_TAG_VARIANT_GUID = 'SV0059957_11562437_f019313_1'

COMPOUND_HET_1_GUID = 'SV0059956_11560662_f019313_1'
COMPOUND_HET_2_GUID = 'SV0059957_11562437_f019313_1'
GENE_GUID_2 = 'ENSG00000197530'

VARIANT_TAG_RESPONSE_KEYS = {
    'variantTagsByGuid', 'variantNotesByGuid', 'variantFunctionalDataByGuid', 'savedVariantsByGuid',
}
SAVED_VARIANT_RESPONSE_KEYS = {
    *VARIANT_TAG_RESPONSE_KEYS, 'familiesByGuid', 'omimIntervals',
    'genesById', 'locusListsByGuid', 'rnaSeqData', 'mmeSubmissionsByGuid', 'transcriptsById', 'phenotypeGeneScores',
}

COMPOUND_HET_3_JSON = {
    'alt': 'C',
    'chrom': '15',
    'genotypes': {},
    'genomeVersion': '37',
    'mainTranscriptId': None,
    'originalAltAlleles': ['C'],
    'populations': {'callset': {'ac': 17, 'af': 0.607, 'an': 28}},
    'pos': 62456358,
    'predictions': {'cadd': 12.34},
    'ref': 'A',
    'transcripts': {},
    'xpos': 15062456358,
    'projectGuid': 'R0001_1kg',
    'familyGuids': ['F000001_1'],
    'variantId': '15-62456358-A-C',
    'acmgClassification': None,
}

COMPOUND_HET_4_JSON = {
    'alt': 'A',
    'chrom': '15',
    'genotypes': {},
    'genomeVersion': '37',
    'mainTranscriptId': None,
    'originalAltAlleles': ['A'],
    'populations': {'callset': {'ac': 1, 'af': 0.033, 'an': 8686}},
    'pos': 62456406,
    'predictions': {'cadd': 13.56},
    'ref': 'G',
    'transcripts': {},
    'xpos': 15062456406,
    'projectGuid': 'R0001_1kg',
    'familyGuids': ['F000001_1'],
    'variantId': '15-62456406-G-A',
    'acmgClassification': None,
}

COMPOUND_HET_5_JSON = {
    'alt': 'C',
    'chrom': '16',
    'genotypes': {},
    'genomeVersion': '37',
    'mainTranscriptId': None,
    'originalAltAlleles': ['C'],
    'populations': {'callset': {'ac': 18, 'af': 0.563, 'an': 32}},
    'pos': 31096164,
    'predictions': {'cadd': 7.099},
    'ref': 'G',
    'transcripts': {},
    'xpos': 16031096164,
    'projectGuid': 'R0001_1kg',
    'familyGuids': ['F000001_1'],
    'variantId': '16-31096164-G-C',
    'acmgClassification': None,
}

CREATE_VARIANT_JSON = {
    'alt': 'A',
    'chrom': '2',
    'genotypes': {},
    'genomeVersion': '37',
    'mainTranscriptId': None,
    'originalAltAlleles': ['A'],
    'populations': {'callset': {'ac': 2, 'af': 0.063, 'an': 32}},
    'pos': 61413835,
    'predictions': {'cadd': 21.9},
    'ref': 'AAAG',
    'transcripts': {},
    'projectGuid': 'R0001_1kg',
    'familyGuids': ['F000001_1', 'F000002_2'],
    'variantId': '2-61413835-AAAG-A',
    'CAID': None,
}

CREATE_VARIANT_REQUEST_BODY = {
    'searchHash': 'd380ed0fd28c3127d07a64ea2ba907d7',
    'familyGuid': 'F000001_1',
    'tags': [{'name': 'Review', 'metadata': 'a note'}],
    'note': '',
    'functionalData': [],
    'variant': CREATE_VARIANT_JSON,
}

INVALID_CREATE_VARIANT_REQUEST_BODY = deepcopy(CREATE_VARIANT_REQUEST_BODY)
INVALID_CREATE_VARIANT_REQUEST_BODY['variant']['chrom'] = '27'


class SavedVariantAPITest(object):

    @mock.patch('seqr.views.utils.variant_utils.OMIM_GENOME_VERSION', '37')
    def test_saved_variant_data(self):
        url = reverse(saved_variant_data, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), SAVED_VARIANT_RESPONSE_KEYS)

        variants = response_json['savedVariantsByGuid']
        self.assertSetEqual(set(variants.keys()), {'SV0000002_1248367227_r0390_100', VARIANT_GUID})

        variant = variants[VARIANT_GUID]
        self.assertSetEqual(set(variants['SV0000002_1248367227_r0390_100'].keys()), SAVED_VARIANT_DETAIL_FIELDS)
        fields = {'mainTranscriptId', 'mmeSubmissions'}
        fields.update(SAVED_VARIANT_DETAIL_FIELDS)
        self.assertSetEqual(set(variant.keys()), fields)
        self.assertListEqual(variant['familyGuids'], ['F000001_1'])
        self.assertSetEqual(set(variant['genotypes'].keys()), {'I000003_na19679', 'I000001_na19675', 'I000002_na19678'})
        self.assertSetEqual(
            set(variant['tagGuids']), {'VT1708633_2103343353_r0390_100', 'VT1726961_2103343353_r0390_100'},
        )
        self.assertListEqual(variant['noteGuids'], [])
        self.assertListEqual(variant['mmeSubmissions'], [
            {'geneId': 'ENSG00000135953', 'submissionGuid': 'MS000001_na19675', 'variantGuid': VARIANT_GUID}
        ])

        tag = response_json['variantTagsByGuid']['VT1708633_2103343353_r0390_100']
        self.assertSetEqual(set(tag.keys()), TAG_FIELDS)

        submissions = response_json['mmeSubmissionsByGuid']
        self.assertSetEqual(set(submissions.keys()), {'MS000001_na19675'})
        self.assertSetEqual(set(submissions['MS000001_na19675'].keys()), MATCHMAKER_SUBMISSION_FIELDS)

        locus_list_fields = {'intervals'}
        self.assertEqual(len(response_json['locusListsByGuid']), 1)
        self.assertSetEqual(set(response_json['locusListsByGuid'][LOCUS_LIST_GUID].keys()), locus_list_fields)

        gene_fields = {'locusListGuids'}
        gene_fields.update(GENE_VARIANT_FIELDS)
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000135953'})
        self.assertSetEqual(set(response_json['genesById']['ENSG00000135953'].keys()), gene_fields)

        self.assertDictEqual(
            response_json['transcriptsById'],
            {'ENST00000258436': {'isManeSelect': True, 'refseqId': 'NM_017900.2', 'transcriptId': 'ENST00000258436'}},
        )

        self.assertDictEqual(response_json['rnaSeqData'], {'I000001_na19675': {
            'outliers': {
                'ENSG00000135953': [{
                    'geneId': 'ENSG00000135953', 'zScore': 7.31, 'pValue': 0.00000000000948, 'pAdjust': 0.00000000781,
                    'tissueType': 'M', 'isSignificant': True,
                }]
            },
            'spliceOutliers': {},
        }})

        self.assertDictEqual(response_json['familiesByGuid'], {'F000001_1': {'tpmGenes': ['ENSG00000135953']}})

        self.assertDictEqual(response_json['omimIntervals'], {})

        # include project tag types
        response = self.client.get('{}?loadProjectTagTypes=true'.format(url))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        response_keys = {'projectsByGuid'}
        response_keys.update(SAVED_VARIANT_RESPONSE_KEYS)
        self.assertSetEqual(set(response_json.keys()), response_keys)
        self.assertEqual(len(response_json['savedVariantsByGuid']), 2)
        project = response_json['projectsByGuid'][PROJECT_GUID]
        self.assertSetEqual(set(project.keys()), {'variantTagTypes', 'variantFunctionalTagTypes', 'genomeVersion', 'projectGuid'})
        self.assertSetEqual(set(project['variantTagTypes'][0].keys()), TAG_TYPE_FIELDS)

        # include locus list details
        response = self.client.get('{}?includeLocusLists=true'.format(url))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), SAVED_VARIANT_RESPONSE_KEYS)
        self.assertEqual(len(response_json['savedVariantsByGuid']), 2)
        locus_list_fields.update(LOCUS_LIST_FIELDS)
        locus_list_fields.update(PA_LOCUS_LIST_FIELDS)
        self.assertEqual(len(response_json['locusListsByGuid']), 2)
        self.assertSetEqual(set(response_json['locusListsByGuid'][LOCUS_LIST_GUID].keys()), locus_list_fields)

        # include family context info
        load_family_context_url = '{}?loadFamilyContext=true'.format(url)
        response = self.client.get(load_family_context_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        family_context_response_keys = {
            'individualsByGuid', 'familyNotesByGuid', 'igvSamplesByGuid', 'projectsByGuid'
        }
        family_context_response_keys.update(SAVED_VARIANT_RESPONSE_KEYS)
        self.assertSetEqual(set(response_json.keys()), family_context_response_keys)
        self.assertEqual(len(response_json['savedVariantsByGuid']), 2)
        self.assertEqual(set(response_json['familiesByGuid'].keys()), {'F000001_1', 'F000002_2'})
        family_fields = {'individualGuids', 'tpmGenes'}
        family_fields.update(FAMILY_FIELDS)
        self.assertSetEqual(set(response_json['familiesByGuid']['F000001_1'].keys()), family_fields)
        self.assertSetEqual(set(response_json['familiesByGuid']['F000001_1']['tpmGenes']), {'ENSG00000135953'})
        individual_fields = {'igvSampleGuids'}
        individual_fields.update(INDIVIDUAL_FIELDS)
        self.assertSetEqual(set(next(iter(response_json['individualsByGuid'].values())).keys()), individual_fields)
        self.assertSetEqual(set(next(iter(response_json['familyNotesByGuid'].values())).keys()), FAMILY_NOTE_FIELDS)
        self.assertSetEqual(set(next(iter(response_json['igvSamplesByGuid'].values())).keys()), IGV_SAMPLE_FIELDS)
        self.assertEqual(len(response_json['locusListsByGuid']), 1)
        self.assertDictEqual(response_json['projectsByGuid'], {PROJECT_GUID: {'familiesLoaded': True}})

        # get variants with no tags for whole project
        response = self.client.get('{}?includeNoteVariants=true'.format(url))
        self.assertEqual(response.status_code, 200)
        no_families_response_keys = {*SAVED_VARIANT_RESPONSE_KEYS}
        no_families_response_keys.remove('familiesByGuid')
        no_families_response_keys.remove('transcriptsById')
        self.assertSetEqual(set(response.json().keys()), no_families_response_keys)
        variants = response.json()['savedVariantsByGuid']
        self.assertSetEqual(set(variants.keys()), {COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID})
        self.assertListEqual(variants[COMPOUND_HET_1_GUID]['tagGuids'], [])
        self.assertListEqual(variant['noteGuids'], [])

        # filter by family
        response = self.client.get('{}?families=F000002_2'.format(url))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json['savedVariantsByGuid'].keys()), {'SV0000002_1248367227_r0390_100'})
        self.assertDictEqual(response_json['rnaSeqData'], {})

        # filter by variant guid
        response = self.client.get('{}{}'.format(url, VARIANT_GUID))
        self.assertEqual(response.status_code, 200)

        self.assertSetEqual(set(response.json()['savedVariantsByGuid'].keys()), {VARIANT_GUID})

        response = self.client.get('{}{}'.format(url, NO_TAG_VARIANT_GUID))
        self.assertEqual(response.status_code, 200)

        self.assertSetEqual(set(response.json()['savedVariantsByGuid'].keys()), {NO_TAG_VARIANT_GUID})

        # filter by invalid variant guid
        response = self.client.get('{}foo'.format(url))
        self.assertEqual(response.status_code, 404)

        # Test with discovery SVs
        response = self.client.get(url.replace(PROJECT_GUID, 'R0003_test'))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), no_families_response_keys)

        self.assertSetEqual(
            set(response_json['savedVariantsByGuid'].keys()),
            {'SV0000006_1248367227_r0003_tes', 'SV0000007_prefix_19107_DEL_r00'})
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000135953', 'ENSG00000240361'})
        self.assertDictEqual(response_json['omimIntervals'], {'3': {
            'chrom': '1',
            'start': 249044482,
            'end': 249055991,
            'mimNumber': 600315,
            'phenotypeDescription': '?Immunodeficiency 16', 'phenotypeInheritance': 'Autosomal recessive',
            'phenotypeMimNumber': 615120,
        }})
        self.assertDictEqual(response_json['rnaSeqData'], {})

        # Test cross-project discovery for analyst users
        self.login_analyst_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), SAVED_VARIANT_RESPONSE_KEYS)
        variants = response_json['savedVariantsByGuid']
        self.assertSetEqual(
            set(variants.keys()),
            {'SV0000002_1248367227_r0390_100', VARIANT_GUID}
        )
        discovery_tags = [{
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
        self.assertListEqual(variants['SV0000002_1248367227_r0390_100']['discoveryTags'], discovery_tags)
        self.assertListEqual(variants['SV0000002_1248367227_r0390_100']['familyGuids'], ['F000002_2'])
        self.assertSetEqual(set(response_json['familiesByGuid'].keys()), {'F000001_1', 'F000012_12'})
        self.assertSetEqual(set(response_json['familiesByGuid']['F000012_12'].keys()), FAMILY_FIELDS)
        self.assertDictEqual(response_json['familiesByGuid']['F000001_1'], {'tpmGenes': ['ENSG00000135953']})

        # Test discovery tags with family context
        response = self.client.get(load_family_context_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), family_context_response_keys)
        self.assertSetEqual(
            set(response_json['savedVariantsByGuid'].keys()),
            {'SV0000002_1248367227_r0390_100', 'SV0000001_2103343353_r0390_100'}
        )
        self.assertListEqual(variants['SV0000002_1248367227_r0390_100']['discoveryTags'], discovery_tags)
        self.assertListEqual(variants['SV0000002_1248367227_r0390_100']['familyGuids'], ['F000002_2'])
        self.assertEqual(set(response_json['familiesByGuid'].keys()), {'F000001_1', 'F000002_2', 'F000012_12'})

        # Test empty project
        empty_project_url = url.replace(PROJECT_GUID, 'R0002_empty')
        response = self.client.get(empty_project_url)
        self.assertEqual(response.status_code, 200)
        empty_response = {k: {} for k in VARIANT_TAG_RESPONSE_KEYS}
        self.assertDictEqual(response.json(), empty_response)

        response = self.client.get(f'{empty_project_url}?loadProjectTagTypes=true&loadFamilyContext=true')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), empty_response)

    def test_create_saved_variant(self):
        create_saved_variant_url = reverse(create_saved_variant_handler)
        self.check_collaborator_login(create_saved_variant_url, request_data={'familyGuid': 'F000001_1'})

        response = self.client.post(create_saved_variant_url, content_type='application/json', data=json.dumps(
            INVALID_CREATE_VARIANT_REQUEST_BODY))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Invalid chromosome: 27'})

        response = self.client.post(create_saved_variant_url, content_type='application/json', data=json.dumps(
            CREATE_VARIANT_REQUEST_BODY))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.json()['savedVariantsByGuid']), 1)
        variant_guid = next(iter(response.json()['savedVariantsByGuid']))

        saved_variant = SavedVariant.objects.get(guid=variant_guid, family__guid='F000001_1')
        variant_json = {'xpos': 2061413835}
        variant_json.update(CREATE_VARIANT_JSON)
        self.assertDictEqual(variant_json, saved_variant.saved_variant_json)

        variant_json.update({
            'variantGuid': variant_guid,
            'familyGuids': ['F000001_1'],
            'acmgClassification': None,
            'selectedMainTranscriptId': None,
            'noteGuids': [],
            'functionalDataGuids': [],
        })
        response_json = response.json()
        response_variant_json = response_json['savedVariantsByGuid'][variant_guid]
        tag_guids = response_variant_json.pop('tagGuids')
        self.assertEqual(len(tag_guids), 1)
        tag = response_json['variantTagsByGuid'][tag_guids[0]]
        self.assertDictEqual(variant_json, response_variant_json)

        self.assertEqual('Review', tag['name'])
        self.assertEqual('a note', tag['metadata'])
        self.assertEqual('Review', VariantTag.objects.get(saved_variants__guid=variant_guid).variant_tag_type.name)

        # creating again without specifying the guid should not error and should not create a duplicate
        response = self.client.post(create_saved_variant_url, content_type='application/json', data=json.dumps(
            CREATE_VARIANT_REQUEST_BODY))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(list(response.json()['savedVariantsByGuid'].keys()), [variant_guid])

    def test_create_saved_sv_variant(self):
        create_saved_variant_url = reverse(create_saved_variant_handler)
        self.check_collaborator_login(create_saved_variant_url, request_data={'familyGuid': 'F000001_1'})

        variant_json = {
            'chrom': '2',
            'genotypes': {},
            'genomeVersion': '37',
            'mainTranscriptId': None,
            'populations': {'sv_callset': {'ac': 2, 'af': 0.063, 'an': 32}},
            'pos': 61413835,
            'end': 61414175,
            'predictions': {'strvctvre': 21.9},
            'transcripts': {'ENSG00000240361': []},
            'projectGuid': 'R0001_1kg',
            'familyGuids': ['F000001_1', 'F000002_2'],
            'svType': 'DUP',
            'variantId': 'batch_123_DUP',
            'acmgClassification': None,
        }

        request_body = {
            'familyGuid': 'F000001_1',
            'tags': [],
            'note': 'A promising SV',
            'saveAsGeneNote': True,
            'functionalData': [],
            'variant': variant_json,
        }

        response = self.client.post(create_saved_variant_url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {*VARIANT_TAG_RESPONSE_KEYS, 'genesById'})
        self.assertEqual(len(response_json['savedVariantsByGuid']), 1)
        variant_guid = next(iter(response_json['savedVariantsByGuid']))

        saved_variant = SavedVariant.objects.get(guid=variant_guid, family__guid='F000001_1')
        variant_json.update({'xpos': 2061413835})
        self.assertDictEqual(variant_json, saved_variant.saved_variant_json)
        self.assertEqual(saved_variant.xpos_end, 2061414175)

        variant_json.update({
            'variantGuid': variant_guid,
            'familyGuids': ['F000001_1'],
            'alt': None,
            'ref': None,
            'selectedMainTranscriptId': None,
            'tagGuids': [],
            'functionalDataGuids': [],
        })
        response_variant_json = response_json['savedVariantsByGuid'][variant_guid]
        notes = [response_json['variantNotesByGuid'][note_guid] for note_guid in response_variant_json.pop('noteGuids')]
        self.assertDictEqual(variant_json, response_variant_json)
        self.assertListEqual(['A promising SV'], [note['note'] for note in notes])
        self.assertDictEqual(response_json['genesById'], {'ENSG00000240361': {'notes': [mock.ANY]}})
        self.assertEqual(response_json['genesById']['ENSG00000240361']['notes'][0]['note'], 'A promising SV')
        self.assertDictEqual(response_json['variantTagsByGuid'], {})
        self.assertDictEqual(response_json['variantFunctionalDataByGuid'], {})

    def test_create_saved_compound_hets(self):
        create_saved_compound_hets_url = reverse(create_saved_variant_handler)
        self.check_collaborator_login(create_saved_compound_hets_url, request_data={'familyGuid': 'F000001_1'})

        request_body = {
            'searchHash': 'fe451c0cdf0ee1634e4dcaff7a49a59e',
            'familyGuid': 'F000001_1',
            'tags': [{'name': 'Review'}],
            'notes': [],
            'functionalData': [],
            'variant': [COMPOUND_HET_3_JSON, COMPOUND_HET_4_JSON]
        }

        response = self.client.post(create_saved_compound_hets_url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)

        new_compound_het_3_guid = next(guid for guid, variant_json in response.json()['savedVariantsByGuid'].items()
                                       if variant_json['xpos'] == 15062456358)
        new_compound_het_4_guid = next(guid for guid, variant_json in response.json()['savedVariantsByGuid'].items()
                                       if variant_json['xpos'] == 15062456406)

        saved_compound_het_3 = SavedVariant.objects.get(guid=new_compound_het_3_guid, family__guid='F000001_1')
        saved_compound_het_4 = SavedVariant.objects.get(guid=new_compound_het_4_guid, family__guid='F000001_1')
        self.assertDictEqual(COMPOUND_HET_3_JSON, saved_compound_het_3.saved_variant_json)
        self.assertDictEqual(COMPOUND_HET_4_JSON, saved_compound_het_4.saved_variant_json)

        expected_compound_het_3_json = {
            'variantGuid': new_compound_het_3_guid,
            'selectedMainTranscriptId': None,
            'noteGuids': [],
            'functionalDataGuids': [],
        }
        expected_compound_het_3_json.update(COMPOUND_HET_3_JSON)
        expected_compound_het_4_json = {
            'variantGuid': new_compound_het_4_guid,
            'selectedMainTranscriptId': None,
            'noteGuids': [],
            'functionalDataGuids': [],
        }
        expected_compound_het_4_json.update(COMPOUND_HET_4_JSON)
        response_json = response.json()
        response_compound_het_3_json = response_json['savedVariantsByGuid'][new_compound_het_3_guid]
        response_compound_het_4_json = response_json['savedVariantsByGuid'][new_compound_het_4_guid]
        compound_het_3_tags = [response_json['variantTagsByGuid'][tag_guid] for tag_guid in response_compound_het_3_json.pop('tagGuids')]
        compound_het_4_tags = [response_json['variantTagsByGuid'][tag_guid] for tag_guid in response_compound_het_4_json.pop('tagGuids')]
        self.assertDictEqual(expected_compound_het_3_json, response_compound_het_3_json)
        self.assertDictEqual(expected_compound_het_4_json, response_compound_het_4_json)

        self.assertListEqual(["Review"], [vt['name'] for vt in compound_het_3_tags])
        self.assertListEqual(["Review"], [vt['name'] for vt in compound_het_4_tags])
        self.assertListEqual(["Review"], [vt.variant_tag_type.name for vt in VariantTag.objects.filter(
            saved_variants__guid__contains=new_compound_het_3_guid)])
        self.assertListEqual(["Review"], [vt.variant_tag_type.name for vt in VariantTag.objects.filter(
            saved_variants__guid__contains=new_compound_het_4_guid)])

    def test_create_update_and_delete_variant_note(self):
        create_variant_note_url = reverse(create_variant_note_handler, args=[VARIANT_GUID])
        self.check_collaborator_login(create_variant_note_url, request_data={'familyGuid': 'F000001_1'})

        response = self.client.post(create_variant_note_url, content_type='application/json', data=json.dumps(
            {'familyGuid': 'F000001_1'}
        ))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Note is required')

        # send valid request to create variant_note
        response = self.client.post(create_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new_variant_note', 'report': True, 'familyGuid': 'F000001_1'}
        ))

        self.assertEqual(response.status_code, 200)
        new_note_guid = response.json()['savedVariantsByGuid'][VARIANT_GUID]['noteGuids'][0]
        new_note_response = response.json()['variantNotesByGuid'][new_note_guid]
        self.assertEqual(new_note_response['note'], 'new_variant_note')
        self.assertEqual(new_note_response['report'], True)

        new_variant_note = VariantNote.objects.filter(guid=new_note_guid).first()
        self.assertIsNotNone(new_variant_note)
        self.assertEqual(new_variant_note.note, new_note_response['note'])
        self.assertEqual(new_variant_note.report, new_note_response['report'])

        # save variant_note as gene_note
        response = self.client.post(create_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new_variant_note_as_gene_note', 'saveAsGeneNote': True, 'familyGuid': 'F000001_1'}
        ))
        self.assertEqual(response.status_code, 200)
        new_variant_note_guid = next(
            guid for guid in response.json()['savedVariantsByGuid'][VARIANT_GUID]['noteGuids'] if guid != new_note_guid)
        new_variant_note_response = response.json()['variantNotesByGuid'][new_variant_note_guid]
        self.assertEqual(new_variant_note_response['note'], 'new_variant_note_as_gene_note')
        new_gene_note_response = response.json()['genesById'][GENE_GUID]['notes'][0]
        self.assertEqual(new_gene_note_response['note'], 'new_variant_note_as_gene_note')

        # save variant_note as gene_note for user selected main gene
        create_variant_note_seetced_gene_url = reverse(create_variant_note_handler, args=[VARIANT_GUID])
        response = self.client.post(create_variant_note_seetced_gene_url, content_type='application/json', data=json.dumps(
            {'note': 'new user-selected gene note', 'saveAsGeneNote': True, 'familyGuid': 'F000001_1'}
        ))
        self.assertEqual(response.status_code, 200)
        new_variant_note_response = next(iter(response.json()['variantNotesByGuid'].values()))
        self.assertEqual(new_variant_note_response['note'], 'new user-selected gene note')
        new_gene_note_response = response.json()['genesById'][GENE_GUID]['notes'][1]
        self.assertEqual(new_gene_note_response['note'], 'new user-selected gene note')

        # save variant_note as gene_note for SV
        create_sv_variant_note_url = reverse(create_variant_note_handler, args=['SV0000007_prefix_19107_DEL_r00'])
        response = self.client.post(create_sv_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'SV gene note', 'saveAsGeneNote': True, 'familyGuid': 'F000011_11'}))
        self.assertEqual(response.status_code, 200)
        new_variant_note_response = next(iter(response.json()['variantNotesByGuid'].values()))
        self.assertEqual(new_variant_note_response['note'], 'SV gene note')
        new_gene_note_response = response.json()['genesById'][GENE_GUID]['notes'][2]
        self.assertEqual(new_gene_note_response['note'], 'SV gene note')

        # update the variant_note
        update_variant_note_url = reverse(update_variant_note_handler, args=[VARIANT_GUID, new_note_guid])
        response = self.client.post(update_variant_note_url, content_type='application/json',  data=json.dumps(
            {'note': 'updated_variant_note', 'report': False}))

        self.assertEqual(response.status_code, 200)

        updated_note_response = response.json()['variantNotesByGuid'][new_note_guid]
        self.assertEqual(updated_note_response['note'], 'updated_variant_note')
        self.assertEqual(updated_note_response['report'], False)

        updated_variant_note = VariantNote.objects.filter(guid=updated_note_response['noteGuid']).first()
        self.assertIsNotNone(updated_variant_note)
        self.assertEqual(updated_variant_note.note, updated_note_response['note'])
        self.assertEqual(updated_variant_note.report, updated_note_response['report'])

        # delete the variant_note
        delete_variant_note_url = reverse(delete_variant_note_handler, args=[VARIANT_GUID, updated_variant_note.guid])
        response = self.client.post(delete_variant_note_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)

        # check that variant_note was deleted
        new_variant_note = VariantNote.objects.filter(guid=updated_note_response['noteGuid'])
        self.assertEqual(len(new_variant_note), 0)

    def test_create_partially_saved_compound_het_variant_note(self):
        # compound het 5 is not saved, whereas compound het 1 is saved
        create_saved_variant_url = reverse(create_saved_variant_handler)
        self.check_collaborator_login(create_saved_variant_url, request_data={'familyGuid': 'F000001_1'})

        request_body = {
            'variant': [COMPOUND_HET_5_JSON, {
                'variantId': '21-3343353-GAGA-G', 'xpos': 21003343353, 'ref': 'GAGA', 'alt': 'G',
                'variantGuid': 'SV0000001_2103343353_r0390_100',
                'tagGuids': ['VT1708633_2103343353_r0390_100', 'VT1726961_2103343353_r0390_100'], 'noteGuids': []},
            ],
            'note': 'one_saved_one_not_saved_compount_hets_note',
            'report': True,
            'familyGuid': 'F000001_1',
        }
        response = self.client.post(create_saved_variant_url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.json()['savedVariantsByGuid']), 2)
        compound_het_guids = list(response.json()['savedVariantsByGuid'].keys())
        compound_het_guids.remove(VARIANT_GUID)
        compound_het_5_guid = compound_het_guids[0]

        saved_compound_het_5 = SavedVariant.objects.get(guid=compound_het_5_guid, family__guid='F000001_1')
        self.assertDictEqual(COMPOUND_HET_5_JSON, saved_compound_het_5.saved_variant_json)

        expected_compound_het_5_json = {
            'variantGuid': compound_het_5_guid,
            'selectedMainTranscriptId': None,
            'tagGuids': [],
            'functionalDataGuids': [],
        }
        expected_compound_het_5_json.update(COMPOUND_HET_5_JSON)
        response_json = response.json()
        response_compound_het_5_json = response_json['savedVariantsByGuid'][compound_het_5_guid]
        note_guids = response_compound_het_5_json.pop('noteGuids')
        self.assertDictEqual(expected_compound_het_5_json, response_compound_het_5_json)
        self.assertListEqual(note_guids, response_json['savedVariantsByGuid'][VARIANT_GUID]['noteGuids'])
        self.assertEqual(len(note_guids), 1)

        self.assertEqual(
            'one_saved_one_not_saved_compount_hets_note', response_json['variantNotesByGuid'][note_guids[0]]['note'],
        )

    def test_create_update_and_delete_compound_hets_variant_note(self):
        # send valid request to create variant_note for compound hets
        create_comp_hets_variant_note_url = reverse(create_variant_note_handler, args=[','.join([COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])])
        self.check_collaborator_login(create_comp_hets_variant_note_url, request_data={'familyGuid': 'F000001_1'})

        invalid_comp_hets_variant_note_url = reverse(
            create_variant_note_handler, args=['not_variant,{}'.format(COMPOUND_HET_1_GUID)])
        response = self.client.post(invalid_comp_hets_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new_compound_hets_variant_note', 'report': True, 'familyGuid': 'F000001_1'}
        ))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Unable to find the following variant(s): not_variant'})

        response = self.client.post(create_comp_hets_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new_compound_hets_variant_note', 'report': True, 'familyGuid': 'F000001_1'}
        ))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        for note in response.json()['variantNotesByGuid'].values():
            self.assertEqual(note['note'], 'new_compound_hets_variant_note')
            self.assertEqual(note['report'], True)

        self.assertEqual(
            response_json['savedVariantsByGuid'][COMPOUND_HET_1_GUID]['noteGuids'][0],
            response_json['savedVariantsByGuid'][COMPOUND_HET_2_GUID]['noteGuids'][0],
        )
        new_note_guid = response_json['savedVariantsByGuid'][COMPOUND_HET_1_GUID]['noteGuids'][0]
        new_variant_note = VariantNote.objects.get(guid=new_note_guid)
        self.assertEqual(new_variant_note.note, response_json['variantNotesByGuid'][new_note_guid]['note'])
        self.assertEqual(
            new_variant_note.report, response_json['variantNotesByGuid'][new_note_guid]['report']
        )

        # update the variants_note for both compound hets
        update_variant_note_url = reverse(update_variant_note_handler,
                                          args=[','.join([COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID]), new_note_guid])
        response = self.client.post(update_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'updated_variant_note', 'report': False}))

        self.assertEqual(response.status_code, 200)

        updated_note_response = response.json()['variantNotesByGuid'][new_note_guid]
        self.assertEqual(updated_note_response['note'], 'updated_variant_note')
        self.assertEqual(updated_note_response['report'], False)

        updated_variant_note = VariantNote.objects.get(guid=new_note_guid)
        self.assertEqual(updated_variant_note.note, updated_note_response['note'])
        self.assertEqual(updated_variant_note.report, updated_note_response['report'])

        # save variant_note as gene_note for both compound hets
        response = self.client.post(
            create_comp_hets_variant_note_url, content_type='application/json', data=json.dumps({
                'note': 'new_compound_hets_variant_note_as_gene_note', 'saveAsGeneNote': True, 'familyGuid': 'F000001_1'
            }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        note_guids = response_json['savedVariantsByGuid'][COMPOUND_HET_1_GUID]['noteGuids']
        self.assertListEqual(
            note_guids,
            response_json['savedVariantsByGuid'][COMPOUND_HET_2_GUID]['noteGuids']
        )
        self.assertTrue(new_note_guid in note_guids)
        new_gene_note_guid = next(guid for guid in note_guids if guid != new_note_guid)
        self.assertEqual(
            response_json['variantNotesByGuid'][new_gene_note_guid]['note'],
            'new_compound_hets_variant_note_as_gene_note',
        )
        new_gene_note_response = response.json()['genesById'][GENE_GUID_2]['notes'][0]
        self.assertEqual(new_gene_note_response['note'], 'new_compound_hets_variant_note_as_gene_note')

        # delete the variant_note for both compound hets
        delete_variant_note_url = reverse(delete_variant_note_handler,
                                          args=[','.join([COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID]), new_note_guid])
        response = self.client.post(delete_variant_note_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'savedVariantsByGuid': {
                COMPOUND_HET_1_GUID: {'noteGuids': [new_gene_note_guid]},
                COMPOUND_HET_2_GUID: {'noteGuids': [new_gene_note_guid]}
            },
            'variantNotesByGuid': {new_note_guid: None}})

        # check that variant_note was deleted
        new_variant_note = VariantNote.objects.filter(guid=new_note_guid)
        self.assertEqual(len(new_variant_note), 0)

        # delete the last variant_note for both compound hets
        delete_variant_note_url = reverse(delete_variant_note_handler,
                                          args=[','.join([COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID]), new_gene_note_guid])
        response = self.client.post(delete_variant_note_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'savedVariantsByGuid': {COMPOUND_HET_1_GUID: None, COMPOUND_HET_2_GUID: None},
            'variantNotesByGuid': {new_gene_note_guid: None}})

        # check that variant_note and saved variants was deleted
        new_variant_note = VariantNote.objects.filter(guid=new_gene_note_guid)
        self.assertEqual(len(new_variant_note), 0)
        variants = SavedVariant.objects.filter(guid__in=[COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])
        self.assertEqual(len(variants), 0)

    def test_update_variant_tags(self):
        variant_tags = VariantTag.objects.filter(saved_variants__guid__contains=VARIANT_GUID)
        self.assertSetEqual({"Review", "Tier 1 - Novel gene and phenotype"}, {vt.variant_tag_type.name for vt in variant_tags})

        update_variant_tags_url = reverse(update_variant_tags_handler, args=[VARIANT_GUID])
        self.check_collaborator_login(update_variant_tags_url, request_data={'familyGuid': 'F000001_1'})

        review_guid = 'VT1708633_2103343353_r0390_100'
        response = self.client.post(update_variant_tags_url, content_type='application/json', data=json.dumps({
            'tags': [
                {'tagGuid': review_guid, 'name': 'Review', 'metadata': 'An updated note'},
                {'name': 'Excluded', 'metadata': 'Bad fit'}],
            'familyGuid': 'F000001_1'
        }))
        self.assertEqual(response.status_code, 200)

        tags = response.json()['variantTagsByGuid']
        self.assertEqual(len(tags), 3)
        self.assertIsNone(tags.pop('VT1726961_2103343353_r0390_100'))
        excluded_guid = next(tag for tag in tags if tag != review_guid)
        self.assertEqual('Excluded', tags[excluded_guid]['name'])
        self.assertEqual('Bad fit', tags[excluded_guid]['metadata'])
        self.assertEqual('An updated note', tags[review_guid]['metadata'])
        self.assertSetEqual(
            {excluded_guid, review_guid}, set(response.json()['savedVariantsByGuid'][VARIANT_GUID]['tagGuids'])
        )
        self.assertSetEqual(
            {"Review", "Excluded"}, {vt.variant_tag_type.name for vt in
                                     VariantTag.objects.filter(saved_variants__guid__contains=VARIANT_GUID)})

        # test delete all - with MME submission
        response = self.client.post(update_variant_tags_url, content_type='application/json', data=json.dumps({
            'tags': [],
            'familyGuid': 'F000001_1'
        }))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'variantTagsByGuid': {excluded_guid: None, 'VT1708633_2103343353_r0390_100': None},
            'savedVariantsByGuid': {VARIANT_GUID: {'tagGuids': []}},
        })
        self.assertEqual(VariantTag.objects.filter(saved_variants__guid__contains=VARIANT_GUID).count(), 0)
        self.assertEqual(SavedVariant.objects.filter(guid=VARIANT_GUID).count(), 1)

        # test delete all - no MME submission
        update_no_submission_variant_tags_url = reverse(update_variant_tags_handler, args=[COMPOUND_HET_1_GUID])
        response = self.client.post(update_no_submission_variant_tags_url, content_type='application/json', data=json.dumps({
            'tags': [],
            'familyGuid': 'F000001_1'
        }))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'savedVariantsByGuid': {COMPOUND_HET_1_GUID: None}, 'variantTagsByGuid': {},
        })
        self.assertEqual(VariantTag.objects.filter(saved_variants__guid__contains=COMPOUND_HET_1_GUID).count(), 0)
        self.assertEqual(SavedVariant.objects.filter(guid=COMPOUND_HET_1_GUID).count(), 0)

    def test_update_variant_functional_data(self):
        variant_functional_data = VariantFunctionalData.objects.filter(saved_variants__guid__contains=VARIANT_GUID)
        self.assertSetEqual(
            {'Biochemical Function', 'Genome-wide Linkage', 'Additional Unrelated Kindreds w/ Causal Variants in Gene',
             'Kindreds w/ Overlapping SV & Similar Phenotype'},
            {vt.functional_data_tag for vt in variant_functional_data})
        self.assertSetEqual({"A note", "2"}, {vt.metadata for vt in variant_functional_data})

        update_variant_tags_url = reverse(update_variant_functional_data_handler, args=[VARIANT_GUID])
        self.check_collaborator_login(update_variant_tags_url, request_data={'familyGuid': 'F000001_1'})

        response = self.client.post(update_variant_tags_url, content_type='application/json', data=json.dumps({
            'functionalData': [
                {'tagGuid': 'VFD0000023_1248367227_r0390_10', 'name': 'Biochemical Function',
                 'metadata': 'An updated note'},
                {'name': 'Bonferroni corrected p-value', 'metadata': 0.05}
            ],
            'familyGuid': 'F000001_1'
        }))
        self.assertEqual(response.status_code, 200)

        functional_data_guids = response.json()['savedVariantsByGuid'][VARIANT_GUID]['functionalDataGuids']
        self.assertEqual(len(functional_data_guids), 2)
        new_guid = next(guid for guid in functional_data_guids if guid != 'VFD0000023_1248367227_r0390_10')

        functional_data = response.json()['variantFunctionalDataByGuid']
        self.assertIsNone(functional_data['VFD0000024_1248367227_r0390_10'])
        self.assertEqual(functional_data['VFD0000023_1248367227_r0390_10']['name'], 'Biochemical Function')
        self.assertEqual(functional_data['VFD0000023_1248367227_r0390_10']['metadata'], 'An updated note')
        self.assertEqual(functional_data[new_guid]['name'], 'Bonferroni corrected p-value')
        self.assertEqual(functional_data[new_guid]['metadata'], '0.05')

        variant_functional_data = VariantFunctionalData.objects.filter(saved_variants__guid__contains=VARIANT_GUID)
        self.assertSetEqual(
            {"Biochemical Function", "Bonferroni corrected p-value"},
            {vt.functional_data_tag for vt in variant_functional_data})
        self.assertSetEqual({"An updated note", "0.05"}, {vt.metadata for vt in variant_functional_data})

    def test_update_compound_hets_variant_tags(self):
        variant_tags = VariantTag.objects.filter(saved_variants__guid__in=[COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])
        self.assertEqual(len(variant_tags), 0)

        update_variant_tags_url = reverse(
            update_variant_tags_handler, args=[','.join([COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])])
        self.check_collaborator_login(update_variant_tags_url, request_data={'familyGuid': 'F000001_1'})

        response = self.client.post(update_variant_tags_url, content_type='application/json', data=json.dumps({
            'tags': [{'name': 'Review'}, {'name': 'Excluded'}],
            'familyGuid': 'F000001_1'
        }))
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        compound_het_1_tag_guids = response_json['savedVariantsByGuid'][COMPOUND_HET_1_GUID]['tagGuids']
        compound_het_2_tag_guids = response_json['savedVariantsByGuid'][COMPOUND_HET_2_GUID]['tagGuids']
        self.assertEqual(len(compound_het_1_tag_guids), 2)
        self.assertEqual(len(compound_het_2_tag_guids), 2)
        self.assertSetEqual({"Review", "Excluded"}, {
            vt['name'] for vt in response_json['variantTagsByGuid'].values()
            if vt['tagGuid'] in compound_het_1_tag_guids
        })
        self.assertSetEqual({"Review", "Excluded"}, {
            vt['name'] for vt in response_json['variantTagsByGuid'].values()
            if vt['tagGuid'] in compound_het_2_tag_guids
        })
        self.assertSetEqual(
            {"Review", "Excluded"},
            {vt.variant_tag_type.name for vt in VariantTag.objects.filter(
                saved_variants__guid__in=[COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])})

        invalid_url = reverse(update_variant_tags_handler, args=['not_variant,{}'.format(COMPOUND_HET_1_GUID)])
        response = self.client.post(invalid_url, content_type='application/json', data=json.dumps({
            'tags': [{'name': 'Review'}, {'name': 'Excluded'}],
            'familyGuid': 'F000001_1'
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Unable to find the following variant(s): not_variant'})

    def test_update_compound_hets_variant_functional_data(self):
        variant_functional_data = VariantFunctionalData.objects.filter(
            saved_variants__guid__in=[COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])
        self.assertEqual(len(variant_functional_data), 0)

        # send valid request to creat variant_tag for compound hets
        update_variant_tags_url = reverse(
            update_variant_functional_data_handler, args=[','.join([COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])])
        self.check_collaborator_login(update_variant_tags_url, request_data={'familyGuid': 'F000001_1'})

        response = self.client.post(update_variant_tags_url, content_type='application/json', data=json.dumps({
            'functionalData': [
                {'name': 'Biochemical Function',
                 'metadata': 'An updated note'},
                {'name': 'Bonferroni corrected p-value', 'metadata': '0.05'}
            ],
            'familyGuid': 'F000001_1'
        }))
        self.assertEqual(response.status_code, 200)

        compound_het_1_functional_data_guids = response.json()['savedVariantsByGuid'][COMPOUND_HET_1_GUID]['functionalDataGuids']
        compound_het_2_functional_data_guids = response.json()['savedVariantsByGuid'][COMPOUND_HET_2_GUID]['functionalDataGuids']
        self.assertEqual(len(compound_het_1_functional_data_guids), 2)
        self.assertEqual(len(compound_het_2_functional_data_guids), 2)
        self.assertSetEqual(
            {"Biochemical Function", "Bonferroni corrected p-value"},
            {vt['name'] for vt in response.json()['variantFunctionalDataByGuid'].values()})
        self.assertSetEqual(
            {"An updated note", '0.05'},
            {vt['metadata'] for vt in response.json()['variantFunctionalDataByGuid'].values()})
        variant_functional_data = VariantFunctionalData.objects.filter(
            saved_variants__guid__in=[COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])
        self.assertSetEqual(
            {"Biochemical Function", "Bonferroni corrected p-value"},
            {vt.functional_data_tag for vt in variant_functional_data})
        self.assertSetEqual({"An updated note", "0.05"}, {vt.metadata for vt in variant_functional_data})

        invalid_url = reverse(update_variant_functional_data_handler, args=['not_variant,{}'.format(COMPOUND_HET_1_GUID)])
        response = self.client.post(invalid_url, content_type='application/json', data=json.dumps({
            'functionalData': [],
            'familyGuid': 'F000001_1'
        }))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Unable to find the following variant(s): not_variant'})

    @mock.patch('seqr.views.utils.variant_utils.MAX_VARIANTS_FETCH', 2)
    @mock.patch('seqr.utils.search.utils.es_backend_enabled')
    @mock.patch('seqr.views.apis.saved_variant_api.logger')
    @mock.patch('seqr.views.utils.variant_utils.get_variants_for_variant_ids')
    def test_update_saved_variant_json(self, mock_get_variants, mock_logger, mock_es_enabled):
        mock_es_enabled.return_value = True
        mock_get_variants.side_effect = lambda families, variant_ids, **kwargs: \
            [{'variantId': variant_id, 'familyGuids': [family.guid for family in families]}
             for variant_id in variant_ids]

        url = reverse(update_saved_variant_json, args=['R0001_1kg'])
        self.check_manager_login(url)

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

        self.assertDictEqual(
            response.json(),
            {'SV0000002_1248367227_r0390_100': None, 'SV0000001_2103343353_r0390_100': None,
            'SV0059956_11560662_f019313_1': None}
        )

        families = [Family.objects.get(guid='F000001_1'), Family.objects.get(guid='F000002_2')]
        mock_get_variants.assert_has_calls([
            mock.call(families, ['1-248367227-TC-T', '1-46859832-G-A'], user=self.manager_user, user_email=None),
            mock.call(families, ['21-3343353-GAGA-G'], user=self.manager_user, user_email=None),
        ])
        mock_logger.error.assert_not_called()

        # Test handles update error
        mock_get_variants.side_effect = Exception('Unable to fetch variants')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        mock_logger.error.assert_called_with('Unable to reset saved variant json for R0001_1kg: Unable to fetch variants')

        mock_es_enabled.return_value = False
        response = self.client.post(url)
        self.assertEqual(response.status_code, 500)

    def test_update_variant_main_transcript(self):
        transcript_id = 'ENST00000438943'
        update_main_transcript_url = reverse(update_variant_main_transcript, args=[VARIANT_GUID, transcript_id])
        self.check_manager_login(update_main_transcript_url)

        response = self.client.post(update_main_transcript_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'savedVariantsByGuid': {VARIANT_GUID: {'selectedMainTranscriptId': transcript_id}}})

        saved_variants = SavedVariant.objects.filter(guid=VARIANT_GUID)
        self.assertEqual(len(saved_variants), 1)
        self.assertEqual(saved_variants.first().selected_main_transcript_id, transcript_id)
        self.assertEqual(get_json_for_saved_variants(saved_variants, add_details=True)[0]['selectedMainTranscriptId'], transcript_id)

    def test_update_variant_acmg_classification(self):
        update_variant_acmg_classification_url = reverse(update_variant_acmg_classification_handler, args=[VARIANT_GUID])
        self.check_collaborator_login(update_variant_acmg_classification_url)

        variant = {
            'variant': {
                'acmgClassification': {
                    'classify': 'Uncertain',
                    'criteria': ['PM2_P'],
                    'score': 1
                },
            }
        }

        response = self.client.post(update_variant_acmg_classification_url, content_type='application/json', data=json.dumps(variant))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'savedVariantsByGuid': {VARIANT_GUID: {'acmgClassification': variant['variant']['acmgClassification']}}})


# Tests for AnVIL access disabled
class LocalSavedVariantAPITest(AuthenticationTestCase, SavedVariantAPITest):
    fixtures = ['users', '1kg_project', 'reference_data']


def assert_no_list_ws_has_al(self, acl_call_count):
    self.mock_list_workspaces.assert_not_called()
    self.mock_get_ws_access_level.assert_called_with(mock.ANY,
        'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de')
    self.assertEqual(self.mock_get_ws_access_level.call_count, acl_call_count)
    self.assert_no_extra_anvil_calls()


# Test for permissions from AnVIL only
class AnvilSavedVariantAPITest(AnvilAuthenticationTestCase, SavedVariantAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']

    def test_saved_variant_data(self, *args):
        super(AnvilSavedVariantAPITest, self).test_saved_variant_data(*args)
        self.mock_list_workspaces.assert_called_with(self.analyst_user)
        self.mock_get_ws_access_level.assert_called_with(
            mock.ANY, 'ext-data', 'empty')
        self.mock_get_ws_access_level.assert_any_call(
            mock.ANY, 'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de')
        self.assertEqual(self.mock_get_ws_access_level.call_count, 17)
        self.mock_get_groups.assert_has_calls([mock.call(self.collaborator_user), mock.call(self.analyst_user)])
        self.assertEqual(self.mock_get_groups.call_count, 11)
        self.mock_get_ws_acl.assert_not_called()
        self.mock_get_group_members.assert_not_called()

    def test_create_saved_variant(self):
        super(AnvilSavedVariantAPITest, self).test_create_saved_variant()
        assert_no_list_ws_has_al(self, 4)

    def test_create_saved_sv_variant(self):
        super(AnvilSavedVariantAPITest, self).test_create_saved_sv_variant()
        assert_no_list_ws_has_al(self, 2)

    def test_create_saved_compound_hets(self):
        super(AnvilSavedVariantAPITest, self).test_create_saved_compound_hets()
        assert_no_list_ws_has_al(self, 2)

    def test_create_update_and_delete_variant_note(self):
        super(AnvilSavedVariantAPITest, self).test_create_update_and_delete_variant_note()
        assert_no_list_ws_has_al(self, 8)

    def test_create_partially_saved_compound_het_variant_note(self):
        super(AnvilSavedVariantAPITest, self).test_create_partially_saved_compound_het_variant_note()
        assert_no_list_ws_has_al(self, 2)

    def test_create_update_and_delete_compound_hets_variant_note(self):
        super(AnvilSavedVariantAPITest, self).test_create_update_and_delete_compound_hets_variant_note()
        assert_no_list_ws_has_al(self, 7)

    def test_update_variant_tags(self):
        super(AnvilSavedVariantAPITest, self).test_update_variant_tags()
        assert_no_list_ws_has_al(self, 4)

    def test_update_variant_functional_data(self):
        super(AnvilSavedVariantAPITest, self).test_update_variant_functional_data()
        assert_no_list_ws_has_al(self, 2)

    def test_update_compound_hets_variant_tags(self):
        super(AnvilSavedVariantAPITest, self).test_update_compound_hets_variant_tags()
        assert_no_list_ws_has_al(self, 3)

    def test_update_compound_hets_variant_functional_data(self):
        super(AnvilSavedVariantAPITest, self).test_update_compound_hets_variant_functional_data()
        assert_no_list_ws_has_al(self, 3)

    def test_update_saved_variant_json(self, *args):
        super(AnvilSavedVariantAPITest, self).test_update_saved_variant_json(*args)
        assert_no_list_ws_has_al(self, 3)

    def test_update_variant_main_transcript(self):
        super(AnvilSavedVariantAPITest, self).test_update_variant_main_transcript()
        assert_no_list_ws_has_al(self, 2)

    def test_update_variant_acmg_classification(self):
        super(AnvilSavedVariantAPITest, self).test_update_variant_acmg_classification()
        assert_no_list_ws_has_al(self, 2)
