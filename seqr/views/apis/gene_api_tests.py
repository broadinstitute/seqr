import json
import mock
from copy import deepcopy

from django.test import TransactionTestCase
from django.urls.base import reverse

from seqr.models import GeneNote
from seqr.views.apis.gene_api import gene_info, create_gene_note_handler, update_gene_note_handler, delete_gene_note_handler
from seqr.views.utils.test_utils import _check_login


GENE_ID = 'ENSG00000155657'

MOCK_GENE = {'geneId': GENE_ID, 'geneName': 'TTN'}


class GeneAPITest(TransactionTestCase):
    fixtures = ['users']

    @mock.patch('seqr.views.apis.gene_api.get_reference')
    def test_gene_info(self, mock_reference):
        mock_reference.return_value.get_gene.return_value = deepcopy(MOCK_GENE)
        mock_reference.return_value.get_tissue_expression_display_values.return_value = []

        url = reverse(gene_info, args=[GENE_ID])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        gene = response.json()[GENE_ID]
        self.assertDictEqual(gene,  dict(expression=[], notes=[], **MOCK_GENE))

    def test_create_update_and_delete_gene_note(self):
        create_gene_note_url = reverse(create_gene_note_handler, args=[GENE_ID])
        _check_login(self, create_gene_note_url)

        # send valid request to create gene_note
        response = self.client.post(create_gene_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new_gene_note'}
        ))

        self.assertEqual(response.status_code, 200)
        new_note_response = response.json()[GENE_ID]['notes'][0]
        self.assertEqual(new_note_response['note'], 'new_gene_note')

        new_gene_note = GeneNote.objects.filter(guid=new_note_response['noteGuid']).first()
        self.assertIsNotNone(new_gene_note)
        self.assertEqual(new_gene_note.note, new_note_response['note'])

        # update the gene_note
        update_gene_note_url = reverse(update_gene_note_handler, args=[GENE_ID, new_gene_note.guid])
        response = self.client.post(update_gene_note_url, content_type='application/json',  data=json.dumps(
            {'note': 'updated_gene_note'}))

        self.assertEqual(response.status_code, 200)

        updated_note_response = response.json()[GENE_ID]['notes'][0]
        self.assertEqual(updated_note_response['note'], 'updated_gene_note')

        updated_gene_note = GeneNote.objects.filter(guid=updated_note_response['noteGuid']).first()
        self.assertIsNotNone(updated_gene_note)
        self.assertEqual(updated_gene_note.note, updated_note_response['note'])

        # delete the gene_note
        delete_gene_note_url = reverse(delete_gene_note_handler, args=[GENE_ID, updated_gene_note.guid])
        response = self.client.post(delete_gene_note_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)

        # check that gene_note was deleted
        new_gene_note = GeneNote.objects.filter(guid=updated_note_response['noteGuid'])
        self.assertEqual(len(new_gene_note), 0)
