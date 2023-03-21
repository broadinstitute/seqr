import json
import mock

from django.urls.base import reverse
from copy import deepcopy
from seqr.models import LocusList
from seqr.views.apis.locus_list_api import locus_lists, locus_list_info, create_locus_list_handler, \
    update_locus_list_handler, delete_locus_list_handler, add_project_locus_lists, delete_project_locus_lists, \
    all_locus_list_options
from seqr.views.utils.test_utils import AuthenticationTestCase, LOCUS_LIST_DETAIL_FIELDS, PA_LOCUS_LIST_FIELDS, LOCUS_LIST_FIELDS


LOCUS_LIST_GUID = 'LL00049_pid_genes_autosomal_do'
PRIVATE_LOCUS_LIST_GUID = 'LL00005_retina_proteome'
PROJECT_GUID = 'R0001_1kg'

PUBLIC_LOCUS_LIST_FIELDS = deepcopy(LOCUS_LIST_DETAIL_FIELDS)
PUBLIC_LOCUS_LIST_FIELDS.update(PA_LOCUS_LIST_FIELDS)

OPTION_LOCUS_LIST_FIELDS = deepcopy(LOCUS_LIST_FIELDS)
OPTION_LOCUS_LIST_FIELDS.update(PA_LOCUS_LIST_FIELDS)


class BaseLocusListAPITest(object):

    EXPECTED_LOCUS_LISTS = {LOCUS_LIST_GUID}
    MAIN_LIST_GUID = LOCUS_LIST_GUID
    DETAIL_FIELDS = PUBLIC_LOCUS_LIST_FIELDS

    def test_locus_lists(self):
        url = reverse(locus_lists)
        self.check_require_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        locus_lists_dict = response.json()['locusListsByGuid']
        self.assertSetEqual(set(locus_lists_dict.keys()), self.EXPECTED_LOCUS_LISTS)
        self._test_expected_locus_list(locus_lists_dict)

        self.login_analyst_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        locus_lists_dict = response.json()['locusListsByGuid']
        self.assertSetEqual(set(locus_lists_dict.keys()), self.EXPECTED_LOCUS_LISTS.union({PRIVATE_LOCUS_LIST_GUID}))

    def _test_expected_locus_list(self, locus_lists_dict):
        locus_list = locus_lists_dict[LOCUS_LIST_GUID]
        fields = {'numProjects', 'geneNames'}
        fields.update(OPTION_LOCUS_LIST_FIELDS)
        self.assertSetEqual(set(locus_list.keys()), fields)
        self.assertSetEqual(set(locus_list['geneNames']), {'WASH7P', 'DDX11L1', 'MIR1302-2HG'})

    def test_public_locus_list_info(self):
        url = reverse(locus_list_info, args=[self.MAIN_LIST_GUID])
        self.check_require_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        locus_lists_dict = response_json['locusListsByGuid']
        self.assertListEqual(list(locus_lists_dict.keys()), [self.MAIN_LIST_GUID])

        locus_list = locus_lists_dict[self.MAIN_LIST_GUID]
        self.assertSetEqual(set(locus_list.keys()), self.DETAIL_FIELDS)
        self.assertSetEqual(
            {item['geneId'] for item in locus_list['items'] if item.get('geneId')},
            set(response_json['genesById'].keys())
        )

    def test_private_locus_list_info(self):
        url = reverse(locus_list_info, args=[PRIVATE_LOCUS_LIST_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        locus_lists_dict = response_json['locusListsByGuid']
        self.assertListEqual(list(locus_lists_dict.keys()), [PRIVATE_LOCUS_LIST_GUID])

        # Removing the locus list from projects removes user access
        LocusList.objects.get(guid=PRIVATE_LOCUS_LIST_GUID).projects.clear()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # The list creator should still have access
        self.login_analyst_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def _test_project_locus_list_response(self, response, has_main_list):
        self.assertEqual(response.status_code, 200)
        expected_guids = {LOCUS_LIST_GUID, PRIVATE_LOCUS_LIST_GUID, self.MAIN_LIST_GUID}
        if not has_main_list:
            expected_guids.remove(self.MAIN_LIST_GUID)
        self.assertSetEqual(set(response.json()['locusListGuids']), expected_guids)
        ll_projects = LocusList.objects.get(guid=self.MAIN_LIST_GUID).projects.all()
        self.assertEqual(ll_projects.count(), 2 if has_main_list else 1)
        self.assertEqual(PROJECT_GUID in {p.guid for p in ll_projects}, has_main_list)

    def test_add_and_remove_project_locus_lists(self):

        # add a locus list
        url = reverse(add_project_locus_lists, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({'locusListGuids': [self.MAIN_LIST_GUID]}))
        self._test_project_locus_list_response(response, has_main_list=True)

        # remove a locus list
        url = reverse(delete_project_locus_lists, args=[PROJECT_GUID])
        response = self.client.post(url, content_type='application/json', data=json.dumps({'locusListGuids': [self.MAIN_LIST_GUID]}))
        self.assertEqual(response.status_code, 403)

        self.login_manager()
        response = self.client.post(url, content_type='application/json', data=json.dumps({'locusListGuids': [self.MAIN_LIST_GUID]}))
        self._test_project_locus_list_response(response, has_main_list=False)


class LocusListAPITest(AuthenticationTestCase, BaseLocusListAPITest):
    fixtures = ['users', '1kg_project', 'reference_data']

    def test_all_locus_list_options(self):
        url = reverse(all_locus_list_options)
        self.check_require_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertSetEqual(set(response.json().keys()), {'locusListsByGuid'})
        locus_lists_dict = response.json()['locusListsByGuid']
        self.assertSetEqual(set(locus_lists_dict.keys()), {LOCUS_LIST_GUID})

        locus_list = locus_lists_dict[LOCUS_LIST_GUID]
        self.assertSetEqual(set(locus_list.keys()), OPTION_LOCUS_LIST_FIELDS)

        self.login_collaborator()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(set(response.json()['locusListsByGuid'].keys()), {LOCUS_LIST_GUID, 'LL00005_retina_proteome'})

    def test_create_locus_list(self):
        create_locus_list_url = reverse(create_locus_list_handler)
        self.check_require_login(create_locus_list_url)

        # send invalid requests to create locus_list
        response = self.client.post(create_locus_list_url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, '"Name" is required')

        response = self.client.post(create_locus_list_url, content_type='application/json', data=json.dumps({
            'name': 'new_locus_list', 'isPublic': True, 'rawItems': 'DDX11L1, foo  10:10-1  chr100:1-10 \n2:1234-5678',
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'This list contains invalid genes/ intervals. Update them, or select the "Ignore invalid genes and intervals" checkbox to ignore.')
        self.assertListEqual(response.json()['invalidLocusListItems'], ['chr10:10-1', 'chr100:1-10', 'foo'])

        # send valid request to create locus_list
        body = {
            'name': 'new_locus_list', 'isPublic': True, 'ignoreInvalidItems': True,
            'rawItems': 'DDX11L1, foo   chr100:1-1 \nchr2:1234-5678',
        }
        response = self.client.post(create_locus_list_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        new_locus_list_response = response.json()
        self.assertEqual(len(new_locus_list_response['locusListsByGuid']), 1)
        new_locus_list = list(new_locus_list_response['locusListsByGuid'].values())[0]
        self.assertEqual(new_locus_list['name'], 'new_locus_list')
        self.assertEqual(new_locus_list['isPublic'], True)

        self.assertSetEqual(
            {item['geneId'] for item in new_locus_list['items'] if item.get('geneId')},
            set(new_locus_list_response['genesById'].keys())
        )
        self.assertListEqual(
            new_locus_list['items'],
            [
                {'geneId': 'ENSG00000223972', 'pagene': None},
                {'chrom': '2', 'start': 1234, 'end': 5678, 'genomeVersion': '37', 'locusListIntervalGuid': mock.ANY}
            ]
        )

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

        # Re-creating the same list throws an error
        response = self.client.post(create_locus_list_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'This list already exists')

    def test_create_update_and_delete_locus_list(self):
        update_locus_list_url = reverse(update_locus_list_handler, args=[LOCUS_LIST_GUID])
        self.check_manager_login(update_locus_list_url)

        response = self.client.post(update_locus_list_url, content_type='application/json', data=json.dumps(
            {'name': 'updated_locus_list', 'isPublic': False, 'rawItems': 'DDX11L1 FAM138A NOT_GENE'}))
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'invalidLocusListItems': ['NOT_GENE']})
        self.assertEqual(
            response.reason_phrase,
            'This list contains invalid genes/ intervals. Update them, or select the "Ignore invalid genes and intervals" checkbox to ignore.'
        )

        response = self.client.post(update_locus_list_url, content_type='application/json',  data=json.dumps(
            {'name': 'updated_locus_list', 'isPublic': False, 'rawItems': 'DDX11L1 FAM138A'}))

        self.assertEqual(response.status_code, 200)
        updated_locus_list_response = response.json()
        self.assertEqual(len(updated_locus_list_response['locusListsByGuid']), 1)
        updated_locus_list = list(updated_locus_list_response['locusListsByGuid'].values())[0]
        self.assertEqual(updated_locus_list['name'], 'updated_locus_list')
        self.assertEqual(updated_locus_list['isPublic'], False)

        existing_gene_id = 'ENSG00000223972'
        new_gene_id = 'ENSG00000237613'
        self.assertSetEqual(set(updated_locus_list_response['genesById'].keys()), {new_gene_id, existing_gene_id})
        self.assertSetEqual({item['geneId'] for item in updated_locus_list['items']}, {new_gene_id, existing_gene_id})

        updated_locus_list_model = LocusList.objects.filter(guid=LOCUS_LIST_GUID).first()
        self.assertIsNotNone(updated_locus_list_model)
        self.assertEqual(updated_locus_list_model.name, updated_locus_list['name'])
        self.assertEqual(updated_locus_list_model.is_public, updated_locus_list['isPublic'])

        self.assertEqual(updated_locus_list_model.locuslistgene_set.count(), 2)
        self.assertEqual(updated_locus_list_model.locuslistgene_set.first().gene_id, existing_gene_id)
        self.assertEqual(updated_locus_list_model.locuslistgene_set.first().guid, 'LLG0000011_nmd_nclensg00000171')
        self.assertEqual(updated_locus_list_model.locuslistgene_set.last().gene_id, new_gene_id)
        self.assertEqual(updated_locus_list_model.locuslistinterval_set.count(), 0)

    def test_delete_locus_list(self):
        delete_locus_list_url = reverse(delete_locus_list_handler, args=[LOCUS_LIST_GUID])
        self.check_manager_login(delete_locus_list_url)

        response = self.client.post(delete_locus_list_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)

        # check that locus_list was deleted
        new_locus_list = LocusList.objects.filter(guid=LOCUS_LIST_GUID)
        self.assertEqual(len(new_locus_list), 0)
