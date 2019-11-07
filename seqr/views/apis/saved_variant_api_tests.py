import json
import mock

from django.test import TransactionTestCase
from django.urls.base import reverse

from seqr.models import SavedVariant, VariantNote, VariantTag, VariantFunctionalData
from seqr.views.apis.saved_variant_api import saved_variant_data, create_variant_note_handler, create_saved_variant_handler, \
    update_variant_note_handler, delete_variant_note_handler, update_variant_tags_handler, update_saved_variant_json, \
    update_variant_main_transcript
from seqr.views.utils.test_utils import _check_login


VARIANT_GUID = 'SV0000001_2103343353_r0390_100'
GENE_GUID = 'ENSG00000135953'
VARIANT_GUID_2 = 'SV0000002_1248367227_r0390_100'

COMPOUND_HET_1_GUID = 'SV0059956_11560662_f019313_1'
COMPOUND_HET_2_GUID = 'SV0059957_11562437_f019313_1'
GENE_GUID_2 = 'ENSG00000197530'

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
}
COMPOUND_HET_3_GUID = 'SV0000007_1562456358_f000001_1'

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
}
COMPOUND_HET_4_GUID = 'SV0000006_1562456406_f000001_1'

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
}
COMPOUND_HET_5_GUID = 'SV0000006_1631096164_f000001_1'


class ProjectAPITest(TransactionTestCase):
    fixtures = ['users', '1kg_project']

    def test_saved_variant_data(self):
        url = reverse(saved_variant_data, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        variants = response.json()['savedVariantsByGuid']
        self.assertSetEqual(set(variants.keys()), {'SV0000002_1248367227_r0390_100', 'SV0000001_2103343353_r0390_100'})

        variant = variants['SV0000001_2103343353_r0390_100']
        self.assertSetEqual(
            set(variant.keys()),
            {'variantId', 'variantGuid', 'xpos', 'ref', 'alt', 'chrom', 'pos', 'genomeVersion', 'liftedOverGenomeVersion',
             'liftedOverChrom', 'liftedOverPos', 'familyGuids', 'tags', 'functionalData', 'notes', 'clinvar',
             'originalAltAlleles', 'mainTranscriptId', 'selectedMainTranscriptId', 'genotypes', 'hgmd', 'transcripts',
             'locusListGuids', 'populations', 'predictions', 'rsid', 'genotypeFilters'}
        )
        self.assertSetEqual(set(variant['genotypes'].keys()), {'I000003_na19679', 'I000001_na19675', 'I000002_na19678'})

        # filter by family
        response = self.client.get('{}?families=F000002_2'.format(url))
        self.assertEqual(response.status_code, 200)

        self.assertSetEqual(set(response.json()['savedVariantsByGuid'].keys()), {'SV0000002_1248367227_r0390_100'})

        # filter by variant guid
        response = self.client.get('{}{}'.format(url, VARIANT_GUID))
        self.assertEqual(response.status_code, 200)

        self.assertSetEqual(set(response.json()['savedVariantsByGuid'].keys()), {VARIANT_GUID})

        # filter by invalid variant guid
        response = self.client.get('{}foo'.format(url))
        self.assertEqual(response.status_code, 404)

    def test_create_saved_variant(self):
        create_saved_variant_url = reverse(create_saved_variant_handler)
        _check_login(self, create_saved_variant_url)

        variant_json = {
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
            'xpos': 2061413835,
            'projectGuid': 'R0001_1kg',
            'familyGuids': ['F000001_1', 'F000002_2'],
            'variantId': '2-61413835-AAAG-A',
        }

        request_body = {
            'searchHash': 'd380ed0fd28c3127d07a64ea2ba907d7',
            'familyGuid': 'F000001_1',
            'tags': [{'name': 'Review'}],
            'notes': [],
            'functionalData': [],
        }
        request_body.update(variant_json)

        response = self.client.post(create_saved_variant_url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.json()['savedVariantsByGuid']), 1)
        variant_guid = response.json()['savedVariantsByGuid'].keys()[0]

        saved_variant = SavedVariant.objects.get(guid=variant_guid, family__guid='F000001_1')
        self.assertDictEqual(variant_json, saved_variant.saved_variant_json)

        expected_variant_json = {k: variant_json.pop(k, None) for k in ['xpos', 'alt', 'ref', 'notes']}
        expected_variant_json.update({
            'variantId': '2-61413835-AAAG-A',
            'variantGuid': variant_guid,
            'familyGuids': ['F000001_1'],
            'selectedMainTranscriptId': None,
            'notes': [],
            'functionalData': [],
        })
        response_variant_json = response.json()['savedVariantsByGuid'][variant_guid]
        tags = response_variant_json.pop('tags')
        self.assertDictEqual(expected_variant_json, response_variant_json)

        self.assertListEqual(["Review"], [vt['name'] for vt in tags])
        self.assertListEqual(["Review"], [vt.variant_tag_type.name for vt in VariantTag.objects.filter(saved_variants__guid__contains=variant_guid)])

    def test_create_saved_compound_hets(self):
        create_saved_compound_hets_url = reverse(create_saved_variant_handler)
        _check_login(self, create_saved_compound_hets_url)

        request_body = {
            'searchHash': 'fe451c0cdf0ee1634e4dcaff7a49a59e',
            'familyGuid': 'F000001_1',
            'tags': [{'name': 'Review'}],
            'notes': [],
            'functionalData': [],
        }

        request_body.update({0: COMPOUND_HET_3_JSON, 1: COMPOUND_HET_4_JSON})
        response = self.client.post(create_saved_compound_hets_url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.json()['savedVariantsByGuid']), 2)
        compound_het_3_guid = response.json()['savedVariantsByGuid'].keys()[0]
        compound_het_4_guid = response.json()['savedVariantsByGuid'].keys()[1]

        saved_compound_het_3 = SavedVariant.objects.get(guid=compound_het_3_guid, family__guid='F000001_1')
        saved_compound_het_4 = SavedVariant.objects.get(guid=compound_het_4_guid, family__guid='F000001_1')
        self.assertDictEqual(COMPOUND_HET_3_JSON, saved_compound_het_3.saved_variant_json)
        self.assertDictEqual(COMPOUND_HET_4_JSON, saved_compound_het_4.saved_variant_json)

        expected_compound_het_3_json = {k: COMPOUND_HET_3_JSON.pop(k, None) for k in ['xpos', 'alt', 'ref']}
        expected_compound_het_3_json.update({
            'variantId': '15-62456358-A-C',
            'variantGuid': compound_het_3_guid,
            'familyGuids': ['F000001_1'],
            'selectedMainTranscriptId': None,
            'notes': [],
            'functionalData': [],
        })
        expected_compound_het_4_json = {k: COMPOUND_HET_4_JSON.pop(k, None) for k in ['xpos', 'alt', 'ref']}
        expected_compound_het_4_json.update({
            'variantId': '15-62456406-G-A',
            'variantGuid': compound_het_4_guid,
            'familyGuids': ['F000001_1'],
            'selectedMainTranscriptId': None,
            'notes': [],
            'functionalData': [],
        })
        response_compound_het_3_json = response.json()['savedVariantsByGuid'][compound_het_3_guid]
        response_compound_het_4_json = response.json()['savedVariantsByGuid'][compound_het_4_guid]
        compound_het_3_tags = response_compound_het_3_json.pop('tags')
        compound_het_4_tags = response_compound_het_4_json.pop('tags')
        self.assertDictEqual(expected_compound_het_3_json, response_compound_het_3_json)
        self.assertDictEqual(expected_compound_het_4_json, response_compound_het_4_json)

        self.assertListEqual(["Review"], [vt['name'] for vt in compound_het_3_tags])
        self.assertListEqual(["Review"], [vt['name'] for vt in compound_het_4_tags])
        self.assertListEqual(["Review"], [vt.variant_tag_type.name for vt in VariantTag.objects.filter(saved_variants__guid__contains=compound_het_3_guid)])
        self.assertListEqual(["Review"], [vt.variant_tag_type.name for vt in VariantTag.objects.filter(saved_variants__guid__contains=compound_het_4_guid)])

    def test_create_update_and_delete_variant_note(self):
        create_variant_note_url = reverse(create_variant_note_handler, args=[VARIANT_GUID])
        _check_login(self, create_variant_note_url)

        # send valid request to create variant_note
        response = self.client.post(create_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new_variant_note', 'submitToClinvar': True, 'familyGuid': 'F000001_1'}
        ))

        self.assertEqual(response.status_code, 200)
        new_note_response = response.json()['savedVariantsByGuid'][VARIANT_GUID]['notes'][0]
        self.assertEqual(new_note_response['note'], 'new_variant_note')
        self.assertEqual(new_note_response['submitToClinvar'], True)

        new_variant_note = VariantNote.objects.filter(guid=new_note_response['noteGuid']).first()
        self.assertIsNotNone(new_variant_note)
        self.assertEqual(new_variant_note.note, new_note_response['note'])
        self.assertEqual(new_variant_note.submit_to_clinvar, new_note_response['submitToClinvar'])

        # save variant_note as gene_note
        response = self.client.post(create_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new_variant_note_as_gene_note', 'saveAsGeneNote': True, 'familyGuid': 'F000001_1'}
        ))
        self.assertEqual(response.status_code, 200)
        new_variant_note_response = response.json()['savedVariantsByGuid'][VARIANT_GUID]['notes'][1]
        self.assertEqual(new_variant_note_response['note'], 'new_variant_note_as_gene_note')
        new_gene_note_response = response.json()['genesById'][GENE_GUID]['notes'][0]
        self.assertEqual(new_gene_note_response['note'], 'new_variant_note_as_gene_note')

        # save variant_note as gene_note for user selected main gene
        create_variant_note_seetced_gene_url = reverse(create_variant_note_handler, args=['SV0000003_2246859832_r0390_100'])
        response = self.client.post(create_variant_note_seetced_gene_url, content_type='application/json', data=json.dumps(
            {'note': 'new user-selected gene note', 'saveAsGeneNote': True, 'familyGuid': 'F000001_1'}
        ))
        self.assertEqual(response.status_code, 200)
        new_variant_note_response = response.json()['savedVariantsByGuid']['SV0000003_2246859832_r0390_100']['notes'][0]
        self.assertEqual(new_variant_note_response['note'], 'new user-selected gene note')
        new_gene_note_response = response.json()['genesById'][GENE_GUID]['notes'][1]
        self.assertEqual(new_gene_note_response['note'], 'new user-selected gene note')

        # update the variant_note
        update_variant_note_url = reverse(update_variant_note_handler, args=[VARIANT_GUID, new_variant_note.guid])
        response = self.client.post(update_variant_note_url, content_type='application/json',  data=json.dumps(
            {'note': 'updated_variant_note', 'submitToClinvar': False}))

        self.assertEqual(response.status_code, 200)

        updated_note_response = response.json()['savedVariantsByGuid'][VARIANT_GUID]['notes'][1]
        self.assertEqual(updated_note_response['note'], 'updated_variant_note')
        self.assertEqual(updated_note_response['submitToClinvar'], False)

        updated_variant_note = VariantNote.objects.filter(guid=updated_note_response['noteGuid']).first()
        self.assertIsNotNone(updated_variant_note)
        self.assertEqual(updated_variant_note.note, updated_note_response['note'])
        self.assertEqual(updated_variant_note.submit_to_clinvar, updated_note_response['submitToClinvar'])

        # delete the variant_note
        delete_variant_note_url = reverse(delete_variant_note_handler, args=[VARIANT_GUID, updated_variant_note.guid])
        response = self.client.post(delete_variant_note_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)

        # check that variant_note was deleted
        new_variant_note = VariantNote.objects.filter(guid=updated_note_response['noteGuid'])
        self.assertEqual(len(new_variant_note), 0)

    def test_create_partially_saved_compound_het_variant_note(self):
        # compound het 5 is not saved, whereas compound het 1 is saved
        create_variant_note_url = reverse(create_variant_note_handler, args=[VARIANT_GUID])
        _check_login(self, create_variant_note_url)

        request_body = {0: COMPOUND_HET_5_JSON, 'note': 'one_saved_one_not_saved_compount_hets_note', 'submitToClinvar': True, 'familyGuid': 'F000001_1'}
        response = self.client.post(create_variant_note_url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.json()['savedVariantsByGuid']), 2)
        compound_het_guids = response.json()['savedVariantsByGuid'].keys()
        compound_het_guids.remove(VARIANT_GUID)
        compound_het_5_guid = compound_het_guids[0]
        self.assertEqual(compound_het_5_guid, COMPOUND_HET_5_GUID)

        saved_compound_het_5 = SavedVariant.objects.get(guid=compound_het_5_guid, family__guid='F000001_1')
        self.assertDictEqual(COMPOUND_HET_5_JSON, saved_compound_het_5.saved_variant_json)

        expected_compound_het_5_json = {k: COMPOUND_HET_5_JSON.pop(k, None) for k in ['xpos', 'alt', 'ref']}
        expected_compound_het_5_json.update({
            'variantId': '16-31096164-G-C',
            'variantGuid': compound_het_5_guid,
            'familyGuids': ['F000001_1'],
            'selectedMainTranscriptId': None,
            'tags': [],
            'functionalData': [],
        })
        response_compound_het_5_json = response.json()['savedVariantsByGuid'][compound_het_5_guid]
        response_variant_json = response.json()['savedVariantsByGuid'][VARIANT_GUID]
        compound_het_5_notes = response_compound_het_5_json.pop('notes')
        variant_notes = response_variant_json.pop('notes')
        self.assertDictEqual(expected_compound_het_5_json, response_compound_het_5_json)

        self.assertListEqual(["one_saved_one_not_saved_compount_hets_note"], [vn['note'] for vn in compound_het_5_notes])
        self.assertListEqual(["one_saved_one_not_saved_compount_hets_note"], [vn['note'] for vn in variant_notes])

    def test_create_update_and_delete_compound_hets_variant_note(self):
        # send valid request to create variant_note for compound hets
        create_compound_hets_variant_note_url = reverse(create_variant_note_handler, args=[','.join([COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])])
        _check_login(self, create_compound_hets_variant_note_url)

        response = self.client.post(create_compound_hets_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new_compound_hets_variant_note', 'submitToClinvar': True, 'familyGuid': 'F000001_1'}
        ))

        self.assertEqual(response.status_code, 200)
        compound_het_1_new_note_response = response.json()['savedVariantsByGuid'][COMPOUND_HET_1_GUID]['notes'][0]
        compound_het_2_new_note_response = response.json()['savedVariantsByGuid'][COMPOUND_HET_2_GUID]['notes'][0]
        self.assertEqual(compound_het_1_new_note_response['note'], 'new_compound_hets_variant_note')
        self.assertEqual(compound_het_2_new_note_response['note'], 'new_compound_hets_variant_note')
        self.assertEqual(compound_het_1_new_note_response['submitToClinvar'], True)
        self.assertEqual(compound_het_2_new_note_response['submitToClinvar'], True)

        compound_het_1_new_variant_note = VariantNote.objects.filter(guid=compound_het_1_new_note_response['noteGuid']).first()
        compound_het_2_new_variant_note = VariantNote.objects.filter(guid=compound_het_2_new_note_response['noteGuid']).first()
        self.assertIsNotNone(compound_het_1_new_variant_note)
        self.assertIsNotNone(compound_het_2_new_variant_note)
        self.assertEqual(compound_het_1_new_variant_note.note, compound_het_1_new_note_response['note'])
        self.assertEqual(compound_het_2_new_variant_note.note, compound_het_2_new_note_response['note'])
        self.assertEqual(compound_het_1_new_variant_note.submit_to_clinvar, compound_het_1_new_note_response['submitToClinvar'])
        self.assertEqual(compound_het_2_new_variant_note.submit_to_clinvar, compound_het_2_new_note_response['submitToClinvar'])

        # save variant_note as gene_note for both compound hets
        response = self.client.post(create_compound_hets_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new_compound_hets_variant_note_as_gene_note', 'saveAsGeneNote': True, 'familyGuid': 'F000001_1'}
        ))
        self.assertEqual(response.status_code, 200)
        compound_het_1_new_variant_note_as_gene_note_response = response.json()['savedVariantsByGuid'][COMPOUND_HET_1_GUID]['notes'][1]
        compound_het_2_new_variant_note_as_gene_note_response = response.json()['savedVariantsByGuid'][COMPOUND_HET_2_GUID]['notes'][1]
        self.assertEqual(compound_het_1_new_variant_note_as_gene_note_response['note'], 'new_compound_hets_variant_note_as_gene_note')
        self.assertEqual(compound_het_2_new_variant_note_as_gene_note_response['note'], 'new_compound_hets_variant_note_as_gene_note')
        new_gene_note_response_1 = response.json()['genesById'][GENE_GUID_2]['notes'][0]
        new_gene_note_response_2 = response.json()['genesById'][GENE_GUID_2]['notes'][0]
        self.assertEqual(new_gene_note_response_1['note'], 'new_compound_hets_variant_note_as_gene_note')
        self.assertEqual(new_gene_note_response_2['note'], 'new_compound_hets_variant_note_as_gene_note')

        # update the variants_note for both compound hets
        update_variant_note_url = reverse(update_variant_note_handler,
                                          args=[','.join([COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID]), compound_het_1_new_variant_note.guid])
        response = self.client.post(update_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'updated_variant_note', 'submitToClinvar': False}))

        self.assertEqual(response.status_code, 200)

        updated_note_response_1 = response.json()['savedVariantsByGuid'][COMPOUND_HET_1_GUID]['notes'][0]
        updated_note_response_2 = response.json()['savedVariantsByGuid'][COMPOUND_HET_2_GUID]['notes'][0]
        self.assertEqual(updated_note_response_1['note'], 'new_compound_hets_variant_note_as_gene_note')
        self.assertEqual(updated_note_response_2['note'], 'new_compound_hets_variant_note_as_gene_note')
        self.assertEqual(updated_note_response_1['submitToClinvar'], False)
        self.assertEqual(updated_note_response_2['submitToClinvar'], False)

        updated_variant_note = VariantNote.objects.filter(guid=updated_note_response_1['noteGuid']).first()
        self.assertIsNotNone(updated_variant_note)
        self.assertEqual(updated_variant_note.note, updated_note_response_1['note'])
        self.assertEqual(updated_variant_note.note, updated_note_response_2['note'])
        self.assertEqual(updated_variant_note.submit_to_clinvar, updated_note_response_1['submitToClinvar'])
        self.assertEqual(updated_variant_note.submit_to_clinvar, updated_note_response_2['submitToClinvar'])

        # delete the variant_note for both compound hets
        delete_variant_note_url = reverse(delete_variant_note_handler, args=[','.join([COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID]), updated_variant_note.guid])
        response = self.client.post(delete_variant_note_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)

        # check that variant_note was deleted for both compound hets
        new_variant_note_1 = VariantNote.objects.filter(guid=updated_note_response_1['noteGuid'])
        new_variant_note_2 = VariantNote.objects.filter(guid=updated_note_response_2['noteGuid'])
        self.assertEqual(len(new_variant_note_1), 0)
        self.assertEqual(len(new_variant_note_2), 0)

    def test_update_variant_tags(self):
        variant_tags = VariantTag.objects.filter(saved_variants__guid__contains=VARIANT_GUID)
        self.assertSetEqual({"Review", "Tier 1 - Novel gene and phenotype"}, {vt.variant_tag_type.name for vt in variant_tags})
        variant_functional_data = VariantFunctionalData.objects.filter(saved_variants__guid__contains=VARIANT_GUID)
        self.assertSetEqual({"Biochemical Function", "Genome-wide Linkage"}, {vt.functional_data_tag for vt in variant_functional_data})
        self.assertSetEqual({"A note", "2"}, {vt.metadata for vt in variant_functional_data})

        update_variant_tags_url = reverse(update_variant_tags_handler, args=[VARIANT_GUID])
        _check_login(self, update_variant_tags_url)

        response = self.client.post(update_variant_tags_url, content_type='application/json', data=json.dumps({
            'tags': [{'tagGuid': 'VT1708633_2103343353_r0390_100', 'name': 'Review'}, {'name': 'Excluded'}],
            'functionalData': [
                {'tagGuid': 'VFD0000023_1248367227_r0390_10', 'name': 'Biochemical Function', 'metadata': 'An updated note'},
                {'name': 'Bonferroni corrected p-value', 'metadata': 0.05}
            ],
            'familyGuid': 'F000001_1'
        }))
        self.assertEqual(response.status_code, 200)

        tags = response.json()['savedVariantsByGuid'][VARIANT_GUID]['tags']
        self.assertEqual(len(tags), 2)
        self.assertSetEqual({"Review", "Excluded"}, {vt['name'] for vt in tags})
        self.assertSetEqual({"Review", "Excluded"},
                            {vt.variant_tag_type.name for vt in VariantTag.objects.filter(saved_variants__guid__contains=VARIANT_GUID)})

        functionalData = response.json()['savedVariantsByGuid'][VARIANT_GUID]['functionalData']
        self.assertEqual(len(functionalData), 2)
        self.assertSetEqual({"Biochemical Function", "Bonferroni corrected p-value"}, {vt['name'] for vt in functionalData})
        self.assertSetEqual({"An updated note", "0.05"}, {vt['metadata'] for vt in functionalData})
        variant_functional_data = VariantFunctionalData.objects.filter(saved_variants__guid__contains=VARIANT_GUID)
        self.assertSetEqual({"Biochemical Function", "Bonferroni corrected p-value"}, {vt.functional_data_tag for vt in variant_functional_data})
        self.assertSetEqual({"An updated note", "0.05"}, {vt.metadata for vt in variant_functional_data})

    def test_update_compound_hets_variant_tags(self):
        # check no tags or functional data exists in the compound hets
        variant_tags = VariantTag.objects.filter(saved_variants__guid__in=[COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])
        self.assertEqual(len(variant_tags), 0)
        variant_functional_data = VariantFunctionalData.objects.filter(saved_variants__guid__in=[COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])
        self.assertEqual(len(variant_functional_data), 0)

        # send valid request to creat variant_tag for compound hets
        update_variant_tags_url = reverse(update_variant_tags_handler, args=[','.join([COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])])
        _check_login(self, update_variant_tags_url)

        response = self.client.post(update_variant_tags_url, content_type='application/json', data=json.dumps({
            'tags': [{'name': 'Review'}, {'name': 'Excluded'}],
            'functionalData': [
                {'name': 'Biochemical Function',
                 'metadata': 'An updated note'},
                {'name': 'Bonferroni corrected p-value', 'metadata': 0.05}
            ],
            'familyGuid': 'F000001_1'
        }))
        self.assertEqual(response.status_code, 200)

        compound_het_1_tags = response.json()['savedVariantsByGuid'][COMPOUND_HET_1_GUID]['tags']
        compound_het_2_tags = response.json()['savedVariantsByGuid'][COMPOUND_HET_2_GUID]['tags']
        self.assertEqual(len(compound_het_1_tags), 2)
        self.assertEqual(len(compound_het_2_tags), 2)
        self.assertSetEqual({"Review", "Excluded"}, {vt['name'] for vt in compound_het_1_tags})
        self.assertSetEqual({"Review", "Excluded"}, {vt['name'] for vt in compound_het_2_tags})
        self.assertSetEqual({"Review", "Excluded"},
                            {vt.variant_tag_type.name for vt in VariantTag.objects.filter(saved_variants__guid__in=[COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])})

        compound_het_1_functional_data = response.json()['savedVariantsByGuid'][COMPOUND_HET_1_GUID]['functionalData']
        compound_het_2_functional_data = response.json()['savedVariantsByGuid'][COMPOUND_HET_2_GUID]['functionalData']
        self.assertEqual(len(compound_het_1_functional_data), 2)
        self.assertEqual(len(compound_het_2_functional_data), 2)
        self.assertSetEqual({"Biochemical Function", "Bonferroni corrected p-value"}, {vt['name'] for vt in compound_het_1_functional_data})
        self.assertSetEqual({"Biochemical Function", "Bonferroni corrected p-value"}, {vt['name'] for vt in compound_het_2_functional_data})
        self.assertSetEqual({"An updated note", "0.05"}, {vt['metadata'] for vt in compound_het_1_functional_data})
        self.assertSetEqual({"An updated note", "0.05"}, {vt['metadata'] for vt in compound_het_2_functional_data})
        variant_functional_data = VariantFunctionalData.objects.filter(saved_variants__guid__in=[COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])
        self.assertSetEqual({"Biochemical Function", "Bonferroni corrected p-value"}, {vt.functional_data_tag for vt in variant_functional_data})
        self.assertSetEqual({"An updated note", "0.05"}, {vt.metadata for vt in variant_functional_data})

    @mock.patch('seqr.views.utils.variant_utils._retrieve_saved_variants_json')
    def test_update_saved_variant_json(self, mock_retrieve_variants):
        mock_retrieve_variants.side_effect = lambda project, variant_tuples: \
            [{'xpos': var[0], 'ref': var[1], 'alt': var[2], 'familyGuids': [var[3].guid]} for var in variant_tuples]

        url = reverse(update_saved_variant_json, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertSetEqual(
            set(response.json().keys()),
            {'SV0000002_1248367227_r0390_100', 'SV0000001_2103343353_r0390_100',
             'SV0000003_2246859832_r0390_100', 'SV0059957_11562437_f019313_1', 'SV0059956_11560662_f019313_1'}
        )

    def test_update_variant_main_transcript(self):
        transcript_id = 'ENST00000438943'
        update_main_transcript_url = reverse(update_variant_main_transcript, args=[VARIANT_GUID, transcript_id])
        _check_login(self, update_main_transcript_url)

        response = self.client.get(update_main_transcript_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'savedVariantsByGuid': {VARIANT_GUID: {'selectedMainTranscriptId': transcript_id}}})

        saved_variant = SavedVariant.objects.get(guid=VARIANT_GUID)
        self.assertEqual(saved_variant.selected_main_transcript_id, transcript_id)


