import json
import mock

from django.test import TransactionTestCase
from django.urls.base import reverse

from seqr.models import LocusList, Project
from seqr.views.apis.locus_list_api import locus_lists, locus_list_info, create_locus_list_handler, \
    update_locus_list_handler, delete_locus_list_handler, add_project_locus_lists, delete_project_locus_lists, \
    get_project_locus_list_models
from seqr.views.utils.test_utils import _check_login


LOCUS_LIST_GUID = 'LL00049_pid_genes_autosomal_do'
PROJECT_GUID = 'R0001_1kg'


class LocusListAPITest(TransactionTestCase):
    fixtures = ['users', '1kg_project']

    def test_locus_lists(self):
        url = reverse(locus_lists)
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        locus_lists_dict = response.json()['locusListsByGuid']
        self.assertSetEqual(set(locus_lists_dict.keys()), {'LL00049_pid_genes_autosomal_do', 'LL00005_retina_proteome'})

        locus_list = locus_lists_dict[LOCUS_LIST_GUID]
        self.assertSetEqual(
            set(locus_list.keys()),
            {'locusListGuid', 'description', 'lastModifiedDate', 'numEntries', 'isPublic', 'createdBy', 'createdDate',
             'canEdit', 'name'}
        )

    @mock.patch('seqr.views.utils.gene_utils.get_reference')
    def test_locus_list_info(self, mock_reference):
        mock_reference.return_value.get_genes.side_effect = lambda gene_ids: {gene_id: {} for gene_id in gene_ids}

        url = reverse(locus_list_info, args=[LOCUS_LIST_GUID])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        locus_lists_dict = response_json['locusListsByGuid']
        self.assertListEqual(locus_lists_dict.keys(), [LOCUS_LIST_GUID])

        locus_list = locus_lists_dict[LOCUS_LIST_GUID]
        self.assertSetEqual(
            set(locus_list.keys()),
            {'locusListGuid', 'description', 'lastModifiedDate', 'numEntries', 'isPublic', 'createdBy', 'createdDate',
             'canEdit', 'name', 'items', 'intervalGenomeVersion'}
        )
        self.assertSetEqual(
            {item['geneId'] for item in locus_list['items'] if item.get('geneId')},
            set(response_json['genesById'].keys())
        )

    @mock.patch('seqr.views.utils.gene_utils.get_reference')
    def test_create_update_and_delete_locus_lust(self, mock_reference):
        mock_reference.return_value.get_genes.side_effect = lambda gene_ids: {gene_id: {'geneId': gene_id} for gene_id in gene_ids}
        mock_reference.return_value.get_gene_id_from_symbol.side_effect = lambda symbol: symbol if symbol != 'foo' else None

        create_locus_list_url = reverse(create_locus_list_handler)
        _check_login(self, create_locus_list_url)

        # send invalid requests to create locus_list
        response = self.client.post(create_locus_list_url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, '"Name" is required')

        response = self.client.post(create_locus_list_url, content_type='application/json', data=json.dumps({
            'name': 'new_locus_list', 'isPublic': True, 'parsedItems': {'items': [
                {'symbol': 'TTN'}, {'symbol': 'foo'}, {'chrom': '100', 'start': '1', 'end': '1'},
                {'chrom': '2', 'start': '1234', 'end': '5678', 'genomeVersion': '37'},
            ]},
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'This list contains invalid genes/ intervals. Update them, or select the "Ignore invalid genes and intervals" checkbox to ignore.')
        self.assertListEqual(response.json()['invalidLocusListItems'], ['chr100:1-1', 'foo'])

        # send valid request to create locus_list
        response = self.client.post(create_locus_list_url, content_type='application/json', data=json.dumps({
            'name': 'new_locus_list', 'isPublic': True, 'ignoreInvalidItems': True, 'parsedItems': {'items': [
                {'symbol': 'TTN'}, {'symbol': 'foo'}, {'chrom': '100', 'start': '1', 'end': '1'},
                {'chrom': '2', 'start': '1234', 'end': '5678', 'genomeVersion': '37'},
            ]},
        }))
        self.assertEqual(response.status_code, 200)
        new_locus_list_response = response.json()
        self.assertEqual(len(new_locus_list_response['locusListsByGuid']), 1)
        new_locus_list = new_locus_list_response['locusListsByGuid'].values()[0]
        self.assertEqual(new_locus_list['name'], 'new_locus_list')
        self.assertEqual(new_locus_list['isPublic'], True)

        self.assertSetEqual(
            {item['geneId'] for item in new_locus_list['items'] if item.get('geneId')},
            set(new_locus_list_response['genesById'].keys())
        )
        self.assertListEqual(
            new_locus_list['items'],
            [
                {'geneId': 'TTN'},
                {'chrom': '2', 'start': 1234, 'end': 5678, 'genomeVersion': '37', 'locusListIntervalGuid': mock.ANY}
            ]
        )
        self.assertListEqual(new_locus_list_response['invalidLocusListItems'], ['chr100:1-1', 'foo'])

        guid = new_locus_list['locusListGuid']
        gene_id = new_locus_list['items'][0]['geneId']
        new_locus_list_model = LocusList.objects.filter(guid=guid).first()
        self.assertIsNotNone(new_locus_list_model)
        self.assertEqual(new_locus_list_model.name, new_locus_list['name'])
        self.assertEqual(new_locus_list_model.is_public, new_locus_list['isPublic'])

        self.assertEqual(new_locus_list_model.locuslistgene_set.count(), 1)
        self.assertEqual(new_locus_list_model.locuslistgene_set.first().gene_id, gene_id)
        self.assertEqual(new_locus_list_model.locuslistinterval_set.count(), 1)
        new_interval = new_locus_list_model.locuslistinterval_set.first()
        self.assertEqual(new_interval.chrom, '2')
        self.assertEqual(new_interval.start, 1234)

        # update the locus_list
        update_locus_list_url = reverse(update_locus_list_handler, args=[guid])
        response = self.client.post(update_locus_list_url, content_type='application/json',  data=json.dumps(
            {'name': 'updated_locus_list', 'isPublic': False,
             'parsedItems': {'items': [{'symbol': 'TTN', 'geneId': gene_id}, {'symbol': 'G6PC'}]}}))

        self.assertEqual(response.status_code, 200)
        updated_locus_list_response = response.json()
        self.assertEqual(len(updated_locus_list_response['locusListsByGuid']), 1)
        updated_locus_list = updated_locus_list_response['locusListsByGuid'].values()[0]
        self.assertEqual(updated_locus_list['name'], 'updated_locus_list')
        self.assertEqual(updated_locus_list['isPublic'], False)

        self.assertEqual(len(updated_locus_list_response['genesById']), 1)
        new_gene_id = updated_locus_list_response['genesById'].keys()[0]
        self.assertSetEqual({item['geneId'] for item in updated_locus_list['items']}, {new_gene_id, gene_id})

        updated_locus_list_model = LocusList.objects.filter(guid=guid).first()
        self.assertIsNotNone(updated_locus_list_model)
        self.assertEqual(updated_locus_list_model.name, updated_locus_list['name'])
        self.assertEqual(updated_locus_list_model.is_public, updated_locus_list['isPublic'])

        self.assertEqual(updated_locus_list_model.locuslistgene_set.count(), 2)
        self.assertEqual(updated_locus_list_model.locuslistgene_set.last().gene_id, new_gene_id)
        self.assertEqual(updated_locus_list_model.locuslistinterval_set.count(), 0)

        # delete the locus_list
        delete_locus_list_url = reverse(delete_locus_list_handler, args=[guid])
        response = self.client.post(delete_locus_list_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)

        # check that locus_list was deleted
        new_locus_list = LocusList.objects.filter(guid=guid)
        self.assertEqual(len(new_locus_list), 0)

    def test_add_and_remove_project_locus_lists(self):
        project = Project.objects.get(guid=PROJECT_GUID)
        self.assertListEqual(list(get_project_locus_list_models(project)), [])

        # add a locus list
        url = reverse(add_project_locus_lists, args=[PROJECT_GUID])
        _check_login(self, url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({'locusListGuids': [LOCUS_LIST_GUID]}))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.json()['locusListGuids'], [LOCUS_LIST_GUID])
        self.assertListEqual(list(get_project_locus_list_models(project)), [LocusList.objects.get(guid=LOCUS_LIST_GUID)])

        # remove a locus list
        url = reverse(delete_project_locus_lists, args=[PROJECT_GUID])
        response = self.client.post(url, content_type='application/json', data=json.dumps({'locusListGuids': [LOCUS_LIST_GUID]}))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.json()['locusListGuids'], [])
        self.assertListEqual(list(get_project_locus_list_models(project)), [])
