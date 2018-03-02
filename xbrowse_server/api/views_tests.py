from django.test import TestCase
from seqr.views.utils.test_utils import _check_login

from xbrowse_server.base.models import GeneNote


class APIViewsTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_create_update_and_delete_gene_note(self):
        add_or_edit_url = '/api/add-or-edit-gene-note'
        delete_url = '/api/delete-gene-note/1'
        _check_login(self, add_or_edit_url)

        # check validation of bad requests
        response = self.client.get(add_or_edit_url)
        self.assertTrue(response.json()['is_error'])

        response = self.client.get(add_or_edit_url, {'gene_id': 'ENSG00000008735', 'note_text': 'test note', 'note_id': 1})
        self.assertTrue(response.json()['is_error'])

        response = self.client.get(delete_url)
        self.assertTrue(response.json()['is_error'])

        # check that create works
        response = self.client.get(add_or_edit_url, {'gene_id': 'ENSG00000008735', 'note_text': 'test note'})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_error'])

        gene_notes = GeneNote.objects.all()
        self.assertEqual(len(gene_notes), 1)
        self.assertEqual(gene_notes[0].note, 'test note')
        self.assertEqual(gene_notes[0].gene_id, 'ENSG00000008735')
        self.assertEqual(gene_notes[0].user.username, 'test_user')
        initial_date_saved = gene_notes[0].date_saved

        # check that edit works
        response = self.client.get(add_or_edit_url, {'gene_id': 'ENSG00000008735', 'note_text': 'edited test note', 'note_id': 1})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_error'])

        gene_notes = GeneNote.objects.all()
        self.assertEqual(len(gene_notes), 1)
        self.assertEqual(gene_notes[0].note, 'edited test note')
        self.assertGreater(gene_notes[0].date_saved, initial_date_saved)

        # check that edit does not change the gene
        response = self.client.get(add_or_edit_url, {'gene_id': 'ENSG00000000001', 'note_text': 'test note', 'note_id': 1})
        self.assertTrue(response.json()['is_error'])

        # check that delete works
        response = self.client.get(delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_error'])

        gene_notes = GeneNote.objects.all()
        self.assertEqual(len(gene_notes), 0)
