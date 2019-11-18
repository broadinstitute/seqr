import json
from django.test import TransactionTestCase
from django.urls.base import reverse

from seqr.models import GeneNote
from seqr.views.apis.gene_api import gene_info, create_gene_note_handler, update_gene_note_handler, delete_gene_note_handler
from seqr.views.utils.test_utils import _check_login


GENE_ID = 'ENSG00000223972'


class GeneAPITest(TransactionTestCase):
    fixtures = ['users', 'reference_data']
    multi_db = True

    def test_gene_info(self):
        url = reverse(gene_info, args=[GENE_ID])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        gene = response.json()['genesById'][GENE_ID]
        self.assertSetEqual(set(gene.keys()), {
            'chromGrch37', 'chromGrch38', 'codingRegionSizeGrch37', 'codingRegionSizeGrch38', 'constraints',
            'diseaseDesc', 'endGrch37', 'endGrch38', 'functionDesc', 'gencodeGeneType', 'geneId', 'geneSymbol',
            'omimPhenotypes', 'mimNumber', 'startGrch37', 'startGrch38', 'notes', 'mgiMarkerId', 'geneNames',
        })

    def test_create_update_and_delete_gene_note(self):
        create_gene_note_url = reverse(create_gene_note_handler, args=[GENE_ID])
        _check_login(self, create_gene_note_url)

        # send valid request to create gene_note
        response = self.client.post(create_gene_note_url, content_type='application/json', data=json.dumps(
            {'note': 'new_gene_note'}
        ))

        self.assertEqual(response.status_code, 200)
        new_note_response = response.json()['genesById'][GENE_ID]['notes'][0]
        self.assertEqual(new_note_response['note'], 'new_gene_note')

        new_gene_note = GeneNote.objects.filter(guid=new_note_response['noteGuid']).first()
        self.assertIsNotNone(new_gene_note)
        self.assertEqual(new_gene_note.note, new_note_response['note'])

        # update the gene_note
        update_gene_note_url = reverse(update_gene_note_handler, args=[GENE_ID, new_gene_note.guid])
        response = self.client.post(update_gene_note_url, content_type='application/json',  data=json.dumps(
            {'note': 'updated_gene_note'}))

        self.assertEqual(response.status_code, 200)

        updated_note_response = response.json()['genesById'][GENE_ID]['notes'][0]
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
