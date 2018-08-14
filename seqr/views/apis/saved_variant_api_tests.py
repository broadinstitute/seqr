import json
import mock

from django.test import TransactionTestCase
from django.urls.base import reverse

from seqr.models import VariantNote, VariantTag, VariantFunctionalData
from seqr.views.apis.saved_variant_api import saved_variant_data, saved_variant_transcripts, create_variant_note_handler, \
    update_variant_note_handler, delete_variant_note_handler, update_variant_tags_handler
from seqr.views.utils.test_utils import _check_login


VARIANT_GUID = 'SV0000001_2103343353_r0390_100'


class ProjectAPITest(TransactionTestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.utils.gene_utils.get_reference')
    def test_saved_variant_data(self, mock_reference):
        mock_reference.return_value.get_genes.side_effect = lambda gene_ids: {gene_id: {'geneId': gene_id} for gene_id in gene_ids}

        url = reverse(saved_variant_data, args=['R0001_1kg'])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        variants = response.json()['savedVariants']
        self.assertSetEqual(set(variants.keys()), {'SV0000002_1248367227_r0390_100', 'SV0000001_2103343353_r0390_100'})

        variant = variants['SV0000001_2103343353_r0390_100']
        self.assertSetEqual(
            set(variant.keys()),
            {'variantId', 'xpos', 'ref', 'alt', 'chrom', 'pos', 'genomeVersion', 'liftedOverGenomeVersion',
             'liftedOverChrom', 'liftedOverPos', 'familyGuid', 'tags', 'functionalData', 'notes', 'clinvar',
             'origAltAlleles', 'geneIds', 'genotypes', 'hgmd', 'annotation', 'transcripts', 'locusLists'}
        )

        # filter by family
        response = self.client.get('{}?family=F000002_2'.format(url))
        self.assertEqual(response.status_code, 200)

        self.assertSetEqual(set(response.json()['savedVariants'].keys()), {'SV0000002_1248367227_r0390_100'})

        # filter by variant guid
        response = self.client.get('{}{}'.format(url, VARIANT_GUID))
        self.assertEqual(response.status_code, 200)

        self.assertSetEqual(set(response.json()['savedVariants'].keys()), {VARIANT_GUID})

        # filter by invalid variant guid
        response = self.client.get('{}foo'.format(url))
        self.assertEqual(response.status_code, 404)

    @mock.patch('seqr.views.apis.saved_variant_api.find_matching_xbrowse_model')
    @mock.patch('seqr.views.apis.saved_variant_api.get_datastore')
    def test_saved_variant_transcripts(self, mock_datastore, mock_xbrowse_model):
        mock_datastore.get_single_variant.return_value.annotation = {'vep_annotation': []}
        url = reverse(saved_variant_transcripts, args=[VARIANT_GUID])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {VARIANT_GUID: {'transcripts': {}}})

        invalid_url = reverse(saved_variant_transcripts, args=['not_a_guid'])
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json().get('message'), 'SavedVariant matching query does not exist.')

    def test_create_update_and_delete_variant_note(self):
        create_variant_note_url = reverse(create_variant_note_handler, args=[VARIANT_GUID])
        _check_login(self, create_variant_note_url)

        # send valid request to create variant_note
        response = self.client.post(create_variant_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new_variant_note', 'submitToClinvar': True}
        ))

        self.assertEqual(response.status_code, 200)
        new_note_response = response.json()[VARIANT_GUID]['notes'][0]
        self.assertEqual(new_note_response['note'], 'new_variant_note')
        self.assertEqual(new_note_response['submitToClinvar'], True)

        new_variant_note = VariantNote.objects.filter(guid=new_note_response['noteGuid']).first()
        self.assertIsNotNone(new_variant_note)
        self.assertEqual(new_variant_note.note, new_note_response['note'])
        self.assertEqual(new_variant_note.submit_to_clinvar, new_note_response['submitToClinvar'])

        # update the variant_note
        update_variant_note_url = reverse(update_variant_note_handler, args=[VARIANT_GUID, new_variant_note.guid])
        response = self.client.post(update_variant_note_url, content_type='application/json',  data=json.dumps(
            {'note': 'updated_variant_note', 'submitToClinvar': False}))

        self.assertEqual(response.status_code, 200)

        updated_note_response = response.json()[VARIANT_GUID]['notes'][0]
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

    def test_update_variant_tags(self):
        variant_tags = VariantTag.objects.filter(saved_variant__guid=VARIANT_GUID)
        self.assertListEqual(["Review", "Tier 1 - Novel gene and phenotype"], [vt.variant_tag_type.name for vt in variant_tags])
        variant_functional_data = VariantFunctionalData.objects.filter(saved_variant__guid=VARIANT_GUID)
        self.assertListEqual(["Biochemical Function", "Genome-wide Linkage"], [vt.functional_data_tag for vt in variant_functional_data])
        self.assertListEqual(["A note", "2"], [vt.metadata for vt in variant_functional_data])

        update_variant_tags_url = reverse(update_variant_tags_handler, args=[VARIANT_GUID])
        _check_login(self, update_variant_tags_url)

        response = self.client.post(update_variant_tags_url, content_type='application/json', data=json.dumps({
            'tags': [{'tagGuid': 'VT1708633_2103343353_r0390_100', 'name': 'Review'}, {'name': 'Excluded'}],
            'functionalData': [
                {'tagGuid': 'VFD0000023_1248367227_r0390_10', 'name': 'Biochemical Function', 'metadata': 'An updated note'},
                {'name': 'Bonferroni corrected p-value', 'metadata': 0.05}
            ]
        }))
        self.assertEqual(response.status_code, 200)

        tags = response.json()[VARIANT_GUID]['tags']
        self.assertEqual(len(tags), 2)
        self.assertListEqual(["Review", "Excluded"], [vt['name'] for vt in tags])
        self.assertListEqual(["Review", "Excluded"], [vt.variant_tag_type.name for vt in VariantTag.objects.filter(saved_variant__guid=VARIANT_GUID)])

        functionalData = response.json()[VARIANT_GUID]['functionalData']
        self.assertEqual(len(functionalData), 2)
        self.assertListEqual(["Biochemical Function", "Bonferroni corrected p-value"], [vt['name'] for vt in functionalData])
        self.assertListEqual(["An updated note", "0.05"], [vt['metadata'] for vt in functionalData])
        variant_functional_data = VariantFunctionalData.objects.filter(saved_variant__guid=VARIANT_GUID)
        self.assertListEqual(["Biochemical Function", "Bonferroni corrected p-value"], [vt.functional_data_tag for vt in variant_functional_data])
        self.assertListEqual(["An updated note", "0.05"], [vt.metadata for vt in variant_functional_data])


