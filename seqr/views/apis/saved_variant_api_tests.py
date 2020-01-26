import json
import mock

from django.test import TransactionTestCase
from django.urls.base import reverse

from seqr.models import SavedVariant, VariantNote, VariantTag, VariantFunctionalData
from seqr.views.apis.saved_variant_api import saved_variant_data, create_variant_note_handler, create_saved_variant_handler, \
    update_variant_note_handler, delete_variant_note_handler, update_variant_tags_handler, update_saved_variant_json, \
    update_variant_main_transcript, update_variant_functional_data_handler
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


class ProjectAPITest(TransactionTestCase):
    fixtures = ['users', '1kg_project']

    def test_saved_variant_data(self):
        url = reverse(saved_variant_data, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {
            'variantTagsByGuid', 'variantNotesByGuid', 'variantFunctionalDataByGuid', 'savedVariantsByGuid', 'genesById'
        })

        variants = response_json['savedVariantsByGuid']
        self.assertSetEqual(set(variants.keys()), {'SV0000002_1248367227_r0390_100', 'SV0000001_2103343353_r0390_100'})

        variant = variants['SV0000001_2103343353_r0390_100']
        self.assertSetEqual(
            set(variant.keys()),
            {'variantId', 'variantGuid', 'xpos', 'ref', 'alt', 'chrom', 'pos', 'genomeVersion', 'liftedOverGenomeVersion',
             'liftedOverChrom', 'liftedOverPos', 'familyGuids', 'tagGuids', 'functionalDataGuids', 'noteGuids',
             'originalAltAlleles', 'mainTranscriptId', 'selectedMainTranscriptId', 'genotypes', 'hgmd', 'transcripts',
             'locusListGuids', 'populations', 'predictions', 'rsid', 'genotypeFilters', 'clinvar',}
        )
        self.assertSetEqual(set(variant['genotypes'].keys()), {'I000003_na19679', 'I000001_na19675', 'I000002_na19678'})
        self.assertSetEqual(
            set(variant['tagGuids']), {'VT1708633_2103343353_r0390_100', 'VT1726961_2103343353_r0390_100'},
        )

        tag = response_json['variantTagsByGuid']['VT1708633_2103343353_r0390_100']
        self.assertSetEqual(
            set(tag.keys()),
            {'tagGuid', 'searchHash', 'lastModifiedDate', 'createdBy', 'variantGuids', 'category', 'color', 'name'}
        )

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
            'variant': variant_json,
        }

        response = self.client.post(create_saved_variant_url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.json()['savedVariantsByGuid']), 1)
        variant_guid = response.json()['savedVariantsByGuid'].keys()[0]

        saved_variant = SavedVariant.objects.get(guid=variant_guid, family__guid='F000001_1')
        variant_json.update({'xpos': 2061413835})
        self.assertDictEqual(variant_json, saved_variant.saved_variant_json)

        variant_json.update({
            'variantGuid': variant_guid,
            'familyGuids': ['F000001_1'],
            'selectedMainTranscriptId': None,
            'noteGuids': [],
            'functionalDataGuids': [],
        })
        response_json = response.json()
        response_variant_json = response_json['savedVariantsByGuid'][variant_guid]
        tags = [response_json['variantTagsByGuid'][tag_guid] for tag_guid in response_variant_json.pop('tagGuids')]
        self.assertDictEqual(variant_json, response_variant_json)

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
            'variant': [COMPOUND_HET_3_JSON, COMPOUND_HET_4_JSON]
        }

        response = self.client.post(create_saved_compound_hets_url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)

        new_compound_het_3_guid = response.json()['savedVariantsByGuid'].keys()[1]
        new_compound_het_4_guid = response.json()['savedVariantsByGuid'].keys()[0]

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
        _check_login(self, create_variant_note_url)

        # send valid request to create variant_note
        response = self.client.post(create_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new_variant_note', 'submitToClinvar': True, 'familyGuid': 'F000001_1'}
        ))

        self.assertEqual(response.status_code, 200)
        new_note_guid = response.json()['savedVariantsByGuid'][VARIANT_GUID]['noteGuids'][0]
        new_note_response = response.json()['variantNotesByGuid'][new_note_guid]
        self.assertEqual(new_note_response['note'], 'new_variant_note')
        self.assertEqual(new_note_response['submitToClinvar'], True)

        new_variant_note = VariantNote.objects.filter(guid=new_note_guid).first()
        self.assertIsNotNone(new_variant_note)
        self.assertEqual(new_variant_note.note, new_note_response['note'])
        self.assertEqual(new_variant_note.submit_to_clinvar, new_note_response['submitToClinvar'])

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
        create_variant_note_seetced_gene_url = reverse(create_variant_note_handler, args=['SV0000003_2246859832_r0390_100'])
        response = self.client.post(create_variant_note_seetced_gene_url, content_type='application/json', data=json.dumps(
            {'note': 'new user-selected gene note', 'saveAsGeneNote': True, 'familyGuid': 'F000001_1'}
        ))
        self.assertEqual(response.status_code, 200)
        new_variant_note_response = response.json()['variantNotesByGuid'].values()[0]
        self.assertEqual(new_variant_note_response['note'], 'new user-selected gene note')
        new_gene_note_response = response.json()['genesById'][GENE_GUID]['notes'][1]
        self.assertEqual(new_gene_note_response['note'], 'new user-selected gene note')

        # update the variant_note
        update_variant_note_url = reverse(update_variant_note_handler, args=[VARIANT_GUID, new_note_guid])
        response = self.client.post(update_variant_note_url, content_type='application/json',  data=json.dumps(
            {'note': 'updated_variant_note', 'submitToClinvar': False}))

        self.assertEqual(response.status_code, 200)

        updated_note_response = response.json()['variantNotesByGuid'][new_note_guid]
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
        create_saved_variant_url = reverse(create_saved_variant_handler)
        _check_login(self, create_saved_variant_url)

        request_body = {
            'variant': [COMPOUND_HET_5_JSON, {'variantId': 'abc123', 'xpos': 21003343353, 'ref': 'GAGA', 'alt': 'G'}],
            'note': 'one_saved_one_not_saved_compount_hets_note',
            'submitToClinvar': True,
            'familyGuid': 'F000001_1',
        }
        response = self.client.post(create_saved_variant_url, content_type='application/json', data=json.dumps(request_body))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.json()['savedVariantsByGuid']), 2)
        compound_het_guids = response.json()['savedVariantsByGuid'].keys()
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
        create_compound_hets_variant_note_url = reverse(create_variant_note_handler, args=[','.join([COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])])
        _check_login(self, create_compound_hets_variant_note_url)

        response = self.client.post(create_compound_hets_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new_compound_hets_variant_note', 'submitToClinvar': True, 'familyGuid': 'F000001_1'}
        ))

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        for note in response.json()['variantNotesByGuid'].values():
            self.assertEqual(note['note'], 'new_compound_hets_variant_note')
            self.assertEqual(note['submitToClinvar'], True)

        self.assertEqual(
            response_json['savedVariantsByGuid'][COMPOUND_HET_1_GUID]['noteGuids'][0],
            response_json['savedVariantsByGuid'][COMPOUND_HET_2_GUID]['noteGuids'][0],
        )
        new_note_guid = response_json['savedVariantsByGuid'][COMPOUND_HET_1_GUID]['noteGuids'][0]
        new_variant_note = VariantNote.objects.get(guid=new_note_guid)
        self.assertEqual(new_variant_note.note, response_json['variantNotesByGuid'][new_note_guid]['note'])
        self.assertEqual(
            new_variant_note.submit_to_clinvar, response_json['variantNotesByGuid'][new_note_guid]['submitToClinvar']
        )

        # update the variants_note for both compound hets
        update_variant_note_url = reverse(update_variant_note_handler,
                                          args=[','.join([COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID]), new_note_guid])
        response = self.client.post(update_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'updated_variant_note', 'submitToClinvar': False}))

        self.assertEqual(response.status_code, 200)

        updated_note_response = response.json()['variantNotesByGuid'][new_note_guid]
        self.assertEqual(updated_note_response['note'], 'updated_variant_note')
        self.assertEqual(updated_note_response['submitToClinvar'], False)

        updated_variant_note = VariantNote.objects.get(guid=new_note_guid)
        self.assertEqual(updated_variant_note.note, updated_note_response['note'])
        self.assertEqual(updated_variant_note.submit_to_clinvar, updated_note_response['submitToClinvar'])

        # delete the variant_note for both compound hets
        delete_variant_note_url = reverse(delete_variant_note_handler,
                                          args=[','.join([COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID]), new_note_guid])
        response = self.client.post(delete_variant_note_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'savedVariantsByGuid': {COMPOUND_HET_1_GUID: {'noteGuids': []}, COMPOUND_HET_2_GUID: {'noteGuids': []}},
            'variantNotesByGuid': {new_note_guid: None}})

        # check that variant_note was deleted
        new_variant_note = VariantNote.objects.filter(guid=new_note_guid)
        self.assertEqual(len(new_variant_note), 0)

        # save variant_note as gene_note for both compound hets
        response = self.client.post(
            create_compound_hets_variant_note_url, content_type='application/json', data=json.dumps({
                'note': 'new_compound_hets_variant_note_as_gene_note', 'saveAsGeneNote': True, 'familyGuid': 'F000001_1'
            }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        new_gene_note_guid = response_json['savedVariantsByGuid'][COMPOUND_HET_1_GUID]['noteGuids'][0]
        self.assertEqual(new_gene_note_guid, response_json['savedVariantsByGuid'][COMPOUND_HET_2_GUID]['noteGuids'][0])

        self.assertEqual(
            response_json['variantNotesByGuid'][new_gene_note_guid]['note'],
            'new_compound_hets_variant_note_as_gene_note',
        )
        new_gene_note_response = response.json()['genesById'][GENE_GUID_2]['notes'][0]
        self.assertEqual(new_gene_note_response['note'], 'new_compound_hets_variant_note_as_gene_note')

    def test_update_variant_tags(self):
        variant_tags = VariantTag.objects.filter(saved_variants__guid__contains=VARIANT_GUID)
        self.assertSetEqual({"Review", "Tier 1 - Novel gene and phenotype"}, {vt.variant_tag_type.name for vt in variant_tags})

        update_variant_tags_url = reverse(update_variant_tags_handler, args=[VARIANT_GUID])
        _check_login(self, update_variant_tags_url)

        response = self.client.post(update_variant_tags_url, content_type='application/json', data=json.dumps({
            'tags': [{'tagGuid': 'VT1708633_2103343353_r0390_100', 'name': 'Review'}, {'name': 'Excluded'}],
            'familyGuid': 'F000001_1'
        }))
        self.assertEqual(response.status_code, 200)

        tags = response.json()['variantTagsByGuid']
        self.assertEqual(len(tags), 2)
        self.assertIsNone(tags.pop('VT1726961_2103343353_r0390_100'))
        excluded_guid = tags.keys()[0]
        self.assertEqual('Excluded', tags[excluded_guid]['name'])
        self.assertSetEqual(
            {excluded_guid, 'VT1708633_2103343353_r0390_100'},
            set(response.json()['savedVariantsByGuid'][VARIANT_GUID]['tagGuids'])
        )
        self.assertSetEqual(
            {"Review", "Excluded"}, {vt.variant_tag_type.name for vt in
                                     VariantTag.objects.filter(saved_variants__guid__contains=VARIANT_GUID)})

    def test_update_variant_functional_data(self):
        variant_functional_data = VariantFunctionalData.objects.filter(saved_variants__guid__contains=VARIANT_GUID)
        self.assertSetEqual(
            {"Biochemical Function", "Genome-wide Linkage"}, {vt.functional_data_tag for vt in variant_functional_data})
        self.assertSetEqual({"A note", "2"}, {vt.metadata for vt in variant_functional_data})

        update_variant_tags_url = reverse(update_variant_functional_data_handler, args=[VARIANT_GUID])
        _check_login(self, update_variant_tags_url)

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
        self.assertEqual(functional_data[new_guid]['metadata'], 0.05)

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
        _check_login(self, update_variant_tags_url)

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

    def test_update_compound_hets_variant_functional_data(self):
        variant_functional_data = VariantFunctionalData.objects.filter(
            saved_variants__guid__in=[COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])
        self.assertEqual(len(variant_functional_data), 0)

        # send valid request to creat variant_tag for compound hets
        update_variant_tags_url = reverse(
            update_variant_functional_data_handler, args=[','.join([COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])])
        _check_login(self, update_variant_tags_url)

        response = self.client.post(update_variant_tags_url, content_type='application/json', data=json.dumps({
            'functionalData': [
                {'name': 'Biochemical Function',
                 'metadata': 'An updated note'},
                {'name': 'Bonferroni corrected p-value', 'metadata': 0.05}
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
            {"An updated note", 0.05},
            {vt['metadata'] for vt in response.json()['variantFunctionalDataByGuid'].values()})
        variant_functional_data = VariantFunctionalData.objects.filter(
            saved_variants__guid__in=[COMPOUND_HET_1_GUID, COMPOUND_HET_2_GUID])
        self.assertSetEqual(
            {"Biochemical Function", "Bonferroni corrected p-value"},
            {vt.functional_data_tag for vt in variant_functional_data})
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


