import json

import responses
from django.urls.base import reverse

from seqr.models import LocusList
from seqr.views.apis.locus_list_api import locus_lists, locus_list_info, add_project_locus_lists, \
    delete_project_locus_lists
from seqr.views.utils.test_utils import AuthenticationTestCase, LOCUS_LIST_FIELDS
from settings import PANEL_APP_API_URL

PROJECT_GUID = 'R0001_1kg'

LOCUS_LIST_GUID = 'LL00049_pid_genes_autosomal_do'
PRIVATE_LOCUS_LIST_GUID = 'LL00005_retina_proteome'
PA_LOCUS_LIST_GUID = 'LL01705_sarcoma'

PA_LOCUS_LIST_FIELDS = {'paLocusList'}
PA_LOCUS_LIST_FIELDS.update(LOCUS_LIST_FIELDS)

PA_LOCUS_LIST_DETAIL_FIELDS = {'items', 'intervalGenomeVersion'}
PA_LOCUS_LIST_DETAIL_FIELDS.update(PA_LOCUS_LIST_FIELDS)
PA_GENE_FIELDS = {'biotype', 'confidenceLevel', 'modeOfPathogenicity', 'penetrance', 'rawData'}


def _get_json_from_file(filepath):
    with open(filepath, 'r') as file:
        filedata = file.read()

    return json.loads(filedata)


class PaLocusListAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'panelapp', 'reference_data']

    def test_locus_lists(self):
        url = reverse(locus_lists)
        self.check_require_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        locus_lists_dict = response.json()['locusListsByGuid']
        self.assertSetEqual(set(locus_lists_dict.keys()), {LOCUS_LIST_GUID, PA_LOCUS_LIST_GUID})

        locus_list = locus_lists_dict[PA_LOCUS_LIST_GUID]
        fields = {'numProjects'}
        fields.update(PA_LOCUS_LIST_FIELDS)
        self.assertSetEqual(set(locus_list.keys()), fields)

        self.login_analyst_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        locus_lists_dict = response.json()['locusListsByGuid']
        self.assertSetEqual(set(locus_lists_dict.keys()),
                            {LOCUS_LIST_GUID, PRIVATE_LOCUS_LIST_GUID, PA_LOCUS_LIST_GUID})

    def test_public_locus_list_info(self):
        url = reverse(locus_list_info, args=[PA_LOCUS_LIST_GUID])
        self.check_require_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        locus_lists_dict = response_json['locusListsByGuid']
        self.assertListEqual(list(locus_lists_dict.keys()), [PA_LOCUS_LIST_GUID])

        locus_list = locus_lists_dict[PA_LOCUS_LIST_GUID]
        self.assertSetEqual(set(locus_list.keys()), PA_LOCUS_LIST_DETAIL_FIELDS)
        self.assertSetEqual(
            {item['geneId'] for item in locus_list['items'] if item.get('geneId')},
            set(response_json['genesById'].keys())
        )
        self.assertSetEqual(
            {item['geneId'] for item in locus_list['items'] if item.get('geneId')},
            set(response_json['pagenesById'].keys())
        )
        self.assertTrue(all(
            {set(pagene.keys()) == PA_GENE_FIELDS for pagene in response_json['pagenesById'].values()}
        ))

    def test_private_locus_list_info(self):
        url = reverse(locus_list_info, args=[PRIVATE_LOCUS_LIST_GUID])
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        locus_lists_dict = response_json['locusListsByGuid']
        self.assertListEqual(list(locus_lists_dict.keys()), [PRIVATE_LOCUS_LIST_GUID])

    def test_add_and_remove_project_locus_lists(self):
        existing_guid = 'LL00005_retina_proteome'

        # add a locus list to project
        url = reverse(add_project_locus_lists, args=[PROJECT_GUID])
        self.check_collaborator_login(url)

        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps({'locusListGuids': [PA_LOCUS_LIST_GUID]}))
        self.assertEqual(response.status_code, 200)
        self.assertSetEqual(set(response.json()['locusListGuids']), {PA_LOCUS_LIST_GUID, existing_guid})
        ll_projects = LocusList.objects.get(guid=PA_LOCUS_LIST_GUID).projects.all()
        self.assertEqual(ll_projects.count(), 2)
        self.assertTrue(PROJECT_GUID in {p.guid for p in ll_projects})

        # remove previously added locus list from project
        url = reverse(delete_project_locus_lists, args=[PROJECT_GUID])
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps({'locusListGuids': [PA_LOCUS_LIST_GUID]}))
        self.assertEqual(response.status_code, 403)

        self.login_data_manager_user()
        response = self.client.post(url, content_type='application/json',
                                    data=json.dumps({'locusListGuids': [PA_LOCUS_LIST_GUID]}))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.json()['locusListGuids'], [existing_guid])
        ll_projects = LocusList.objects.get(guid=PA_LOCUS_LIST_GUID).projects.all()
        self.assertEqual(ll_projects.count(), 1)
        self.assertFalse(PROJECT_GUID in {p.guid for p in ll_projects})

    @responses.activate
    def test_import_all_panels(self):
        # Given all PanelApp gene lists and associated genes
        panels_p1_url = '{}/panels/?page=1'.format(PANEL_APP_API_URL)
        panels_p2_url = '{}/panels/?page=2'.format(PANEL_APP_API_URL)
        genes_260_url = '{}/panels/{}/genes/?page=1'.format(PANEL_APP_API_URL, 260)
        genes_3069_url = '{}/panels/{}/genes/?page=1'.format(PANEL_APP_API_URL, 3069)
        panels_p1_json = _get_json_from_file('panelapp/test_resources/panelapp_panels_p1.json')
        panels_p2_json = _get_json_from_file('panelapp/test_resources/panelapp_panels_p2.json')
        genes_260_json = _get_json_from_file('panelapp/test_resources/panel_260_genes.json')
        genes_3069_json = _get_json_from_file('panelapp/test_resources/panel_3069_genes.json')
        responses.add(responses.GET, panels_p1_url, json=panels_p1_json, status=200)
        responses.add(responses.GET, panels_p2_url, json=panels_p2_json, status=200)
        responses.add(responses.GET, genes_260_url, json=genes_260_json, status=200)
        responses.add(responses.GET, genes_3069_url, json=genes_3069_json, status=200)

        # when import all panels is called
        url = reverse('panelapp:import_panelapp_handler')
        self.login_data_manager_user()
        response = self.client.post(url, content_type='application/json')

        # then import has no errors
        self.assertEqual(response.status_code, 200)

        # and lists from PanelApp are created
        self._assert_lists_imported()

        # and list 260 contains expected two genes
        url260 = reverse(locus_list_info, args=['LL00004_hereditary_haemorrhagi'])
        response = self.client.get(url260)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json['pagenesById'].keys()), {'ENSG00000106991', 'ENSG00000139567'})

        # and list 3069 contains only one gene because the other one was skipped during import
        url3069 = reverse(locus_list_info, args=['LL00005_hereditary_neuropathy_'])
        response = self.client.get(url3069)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json['pagenesById'].keys()), {'ENSG00000090861'})

        # and import is idempotent
        url = reverse('panelapp:import_panelapp_handler')
        self.login_data_manager_user()
        response = self.client.post(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self._assert_lists_imported()

    def _assert_lists_imported(self):
        locuslists_url = reverse(locus_lists)
        self.login_base_user()
        response = self.client.get(locuslists_url)
        self.assertEqual(response.status_code, 200)
        locus_lists_dict = response.json()['locusListsByGuid']

        # both existing and new lists are present
        self.assertSetEqual(set(locus_lists_dict.keys()),
                            {LOCUS_LIST_GUID, PA_LOCUS_LIST_GUID, 'LL00004_hereditary_haemorrhagi',
                             'LL00005_hereditary_neuropathy_'})
