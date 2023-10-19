import json
from django.urls.base import reverse

from seqr.models import GeneNote
from seqr.views.apis.gene_api import gene_info, genes_info, create_gene_note_handler, update_gene_note_handler, \
    delete_gene_note_handler
from seqr.views.utils.test_utils import AuthenticationTestCase, GENE_DETAIL_FIELDS


GENE_ID = 'ENSG00000223972'


class GeneAPITest(AuthenticationTestCase):
    fixtures = ['users', 'reference_data']

    def test_gene_info(self):
        url = reverse(gene_info, args=[GENE_ID])
        self.check_require_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        gene = response.json()['genesById'][GENE_ID]
        self.assertSetEqual(set(gene.keys()), GENE_DETAIL_FIELDS)

    def test_genes_info(self):
        url = reverse(genes_info)
        self.check_require_login(url)

        response = self.client.get('{}?geneIds={},ENSG00000269981,foo'.format(url, GENE_ID))
        self.assertEqual(response.status_code, 200)

        genes = response.json()['genesById']
        self.assertSetEqual(set(genes.keys()), {GENE_ID, 'ENSG00000269981'})
        self.assertSetEqual(set(genes[GENE_ID].keys()), GENE_DETAIL_FIELDS)
        self.assertDictEqual(genes[GENE_ID], {
            'chromGrch37': '1',
            'chromGrch38': '1',
            'clinGen': {'haploinsufficiency': 'No Evidence', 'href': 'https://dosage.clinicalgenome.org/clingen_gene.cgi?sym=', 'triplosensitivity': ''},
            'cnSensitivity': {'phi': 0.90576, 'pts': 0.7346},
            'codingRegionSizeGrch37': 0,
            'codingRegionSizeGrch38': 0,
            'constraints': {'louef': 1.606, 'louefRank': 0, 'misZ': -0.7773, 'misZRank': 1, 'pli': 0.00090576, 'pliRank': 1, 'totalGenes': 1},
            'diseaseDesc': '',
            'endGrch37': 14409,
            'endGrch38': 14409,
            'functionDesc': '',
            'genCc': {'hgncId': 'HGNC:943', 'classifications': [
                {'classification': 'Strong', 'date': '7/29/19 19:04', 'disease': 'dystonia 16', 'moi': 'Autosomal recessive', 'submitter': 'Laboratory for Molecular Medicine'},
                {'classification': 'Supportive', 'date': '9/14/21 0:00', 'disease': 'dystonia 16', 'moi': 'Autosomal recessive', 'submitter': 'Orphanet'},
            ]},
            'gencodeGeneType': 'transcribed_unprocessed_pseudogene',
            'geneId': 'ENSG00000223972',
            'geneNames': '',
            'geneSymbol': 'DDX11L1',
            'mgiMarkerId': None,
            'mimNumber': 147571,
            'notes': [],
            'omimPhenotypes': [{'mimNumber': 147571, 'phenotypeDescription': 'Immunodeficiency 38', 'phenotypeInheritance': 'Autosomal recessive', 'phenotypeMimNumber': 616126}],
            'primateAi': {'percentile25': 0.587214291096, 'percentile75': 0.821286439896},
            'sHet': {'postMean': 0.90576},
            'startGrch37': 11869,
            'startGrch38': 11869,
        })


    def test_create_update_and_delete_gene_note(self):
        create_gene_note_url = reverse(create_gene_note_handler, args=[GENE_ID])
        self.check_require_login(create_gene_note_url)

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

        # test other users cannot modify the note
        self.login_collaborator()
        response = self.client.post(update_gene_note_url, content_type='application/json', data=json.dumps(
            {'note': 'updated_gene_note'}))
        self.assertEqual(response.status_code, 403)

        # delete the gene_note
        delete_gene_note_url = reverse(delete_gene_note_handler, args=[GENE_ID, updated_gene_note.guid])

        response = self.client.post(delete_gene_note_url, content_type='application/json')
        self.assertEqual(response.status_code, 403)

        self.login_base_user()
        response = self.client.post(delete_gene_note_url, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # check that gene_note was deleted
        new_gene_note = GeneNote.objects.filter(guid=updated_note_response['noteGuid'])
        self.assertEqual(len(new_gene_note), 0)
