import json
from collections import defaultdict

import mock
import responses
import tenacity
from django.core.management import call_command, CommandError
from django.urls.base import reverse
from requests import Response
from urllib3.exceptions import MaxRetryError

from panelapp.panelapp_utils import _get_all_genes
from seqr.views.apis.locus_list_api import locus_lists, locus_list_info
from seqr.views.apis.locus_list_api_tests import BaseLocusListAPITest
from seqr.views.utils.test_utils import AuthenticationTestCase, LOCUS_LIST_FIELDS

PROJECT_GUID = 'R0001_1kg'

LOCUS_LIST_GUID = 'LL00049_pid_genes_autosomal_do'
PRIVATE_LOCUS_LIST_GUID = 'LL00005_retina_proteome'
EXISTING_AU_PA_LOCUS_LIST_GUID = 'LL01705_sarcoma'
EXISTING_UK_PA_LOCUS_LIST_GUID = 'LL02064_autosomal_recessive_pr'
NEW_AU_PA_LOCUS_LIST_GUID = 'LL00008_hereditary_neuropathy_'
NEW_UK_PA_LOCUS_LIST_GUID = 'LL00009_auditory_neuropathy_sp'

PA_LOCUS_LIST_FIELDS = {'paLocusList'}
PA_LOCUS_LIST_FIELDS.update(LOCUS_LIST_FIELDS)

PA_LOCUS_LIST_DETAIL_FIELDS = {'items', 'intervalGenomeVersion'}
PA_LOCUS_LIST_DETAIL_FIELDS.update(PA_LOCUS_LIST_FIELDS)
PA_GENE_FIELDS = {'confidenceLevel', 'modeOfInheritance'}

PANEL_APP_API_URL_AU = 'https://panelapp-aus.org/api/v1'
PANEL_APP_API_URL_UK = 'https://panelapp.genomicsengland.co.uk/api/v1'


def _get_json_from_file(filepath):
    with open(filepath, 'r') as file:
        filedata = file.read()

    return json.loads(filedata)


class PaLocusListAPITest(AuthenticationTestCase, BaseLocusListAPITest):
    fixtures = ['users', '1kg_project', 'panelapp', 'reference_data']

    EXISTING_LOCUS_LISTS = [EXISTING_AU_PA_LOCUS_LIST_GUID, EXISTING_UK_PA_LOCUS_LIST_GUID, 'LL00005_mendeliome', 'LL00006_incidentalome']
    EXPECTED_LOCUS_LISTS = {LOCUS_LIST_GUID, *EXISTING_LOCUS_LISTS}
    MAIN_LIST_GUID = EXISTING_AU_PA_LOCUS_LIST_GUID
    DETAIL_FIELDS = PA_LOCUS_LIST_DETAIL_FIELDS

    def _test_expected_locus_list(self, locus_lists_dict):
        locus_list = locus_lists_dict[EXISTING_AU_PA_LOCUS_LIST_GUID]
        fields = {'numProjects', 'geneNames'}
        fields.update(PA_LOCUS_LIST_FIELDS)
        self.assertSetEqual(set(locus_list.keys()), fields)

    @mock.patch('seqr.models.random.randint')
    @responses.activate
    def test_import_all_panels(self, mock_random):
        mock_random.side_effect = [7, 8, 9]

        # Given all PanelApp gene lists and associated genes
        au_panels_p1_url = '{}/panels/?page=1'.format(PANEL_APP_API_URL_AU)
        au_panels_p2_url = '{}/panels/?page=2'.format(PANEL_APP_API_URL_AU)
        au_genes_url_260 = '{}/panels/260/genes'.format(PANEL_APP_API_URL_AU)
        au_genes_url_3069 = '{}/panels/3069/genes'.format(PANEL_APP_API_URL_AU)
        au_panels_p1_json = _get_json_from_file('panelapp/test_resources/au_panelapp_panels_p1.json')
        au_panels_p2_json = _get_json_from_file('panelapp/test_resources/au_panelapp_panels_p2.json')
        au_genes_json = _get_json_from_file('panelapp/test_resources/au_panelapp_genes.json')
        au_genes_json_260 = {
            **au_genes_json,
            'results': au_genes_json['results'][:2]
        }
        au_genes_json_3069 = {
            **au_genes_json,
            'results': au_genes_json['results'][2:]
        }

        uk_panels_p1_url = '{}/panels/?page=1'.format(PANEL_APP_API_URL_UK)
        uk_genes_url = '{}/panels/260/genes'.format(PANEL_APP_API_URL_UK)
        uk_panels_p1_json = _get_json_from_file('panelapp/test_resources/uk_panelapp_panels_p1.json')
        uk_genes_json = _get_json_from_file('panelapp/test_resources/uk_panelapp_genes.json')

        responses.add(responses.GET, au_panels_p1_url, json=au_panels_p1_json, status=200)
        responses.add(responses.GET, au_panels_p2_url, json=au_panels_p2_json, status=200)
        responses.add(responses.GET, au_genes_url_260, status=429)
        responses.add(responses.GET, au_genes_url_260, json=au_genes_json_260, status=200)
        responses.add(responses.GET, au_genes_url_3069, json=au_genes_json_3069, status=200)
        responses.add(responses.GET, uk_panels_p1_url, json=uk_panels_p1_json, status=200)
        responses.add(responses.GET, uk_genes_url, json=uk_genes_json, status=200)

        # test required usage
        with self.assertRaises(CommandError) as err:
            call_command('import_all_panels')
        self.assertEqual(str(err.exception), 'Error: the following arguments are required: source')
        with self.assertRaises(CommandError) as err:
            call_command('import_all_panels', 'MY_SOURCE')
        self.assertEqual(str(err.exception), "Error: argument source: invalid choice: 'MY_SOURCE' (choose from 'AU', 'UK')")

        # when import_all_panels()
        call_command('import_all_panels', 'AU')
        call_command('import_all_panels', 'UK')

        # then lists from PanelApp are created
        self._assert_lists_imported()

        # and AU list 260 contains expected two genes
        url_au260 = reverse(locus_list_info, args=['LL00007_hereditary_haemorrhagi'])
        response = self.client.get(url_au260)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000106991', 'ENSG00000139567'})

        # and list 3069 contains only one gene because the other one was skipped during import
        url3069 = reverse(locus_list_info, args=['LL00008_hereditary_neuropathy_'])
        response = self.client.get(url3069)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000090861'})

        # and UK list 260 contains expected one gene
        url_uk260 = reverse(locus_list_info, args=['LL00009_auditory_neuropathy_sp'])
        response = self.client.get(url_uk260)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000139734'})

        # and has expected logs
        self.assertEqual(len(responses.calls), 7)
        self.assert_json_logs(None, [
            ('Updating PanelAppAU', None),
            ('Found 2 new and 0 existing panels to load', None),
            ('create 2 LocusLists', {'dbUpdate': {
                'dbEntity': 'LocusList',
                'entityIds': ['LL00007_hereditary_haemorrhagi', 'LL00008_hereditary_neuropathy_'],
                'updateType': 'bulk_create',
            }}),
            ('Importing panel id 260', None),
            ('update PaLocusList 7', {'dbUpdate': {
                'dbEntity': 'PaLocusList',
                'entityId': 7,
                'updateType': 'update',
                'updateFields': ['disease_group', 'status', 'version', 'version_created'],
            }}),
            ('Bulk updating genes for list Hereditary Haemorrhagic Telangiectasia', None),
            ('Importing panel id 3069', None),
            ('update PaLocusList 8', {'dbUpdate': {
                'dbEntity': 'PaLocusList',
                'entityId': 8,
                'updateType': 'update',
                'updateFields': ['disease_group', 'status', 'version', 'version_created'],
            }}),
            ("Genes found in panel 3069 but not in reference data, ignoring genes ['ENSG00000104728']", {'severity': 'WARNING'}),
            ('Bulk updating genes for list Hereditary Neuropathy_CMT - isolated', None),
            ('update 2 LocusLists', {'dbUpdate': {
                'dbEntity': 'LocusList',
                'entityIds': ['LL00007_hereditary_haemorrhagi', 'LL00008_hereditary_neuropathy_'],
                'updateFields': ['description'],
                'updateType': 'bulk_update',
            }}),
            ('Done', None),
            ('Loaded 2 PanelAppAU records', None),
            ('Updating PanelAppUK', None),
            ('Found 1 new and 0 existing panels to load', None),
            ('create 1 LocusLists', {'dbUpdate': {
                'dbEntity': 'LocusList',
                'entityIds': ['LL00009_auditory_neuropathy_sp'],
                'updateType': 'bulk_create',
            }}),
            ('Importing panel id 260', None),
            ('update PaLocusList 9', {'dbUpdate': {
                'dbEntity': 'PaLocusList',
                'entityId': 9,
                'updateType': 'update',
                'updateFields': ['disease_group', 'disease_sub_group', 'status', 'version', 'version_created'],
            }}),
            ('Bulk updating genes for list Auditory Neuropathy Spectrum Disorde', None),
            ('update 1 LocusLists', {'dbUpdate': {
                'dbEntity': 'LocusList',
                'entityIds': ['LL00009_auditory_neuropathy_sp'],
                'updateFields': ['description'],
                'updateType': 'bulk_update',
            }}),
            ('Done', None),
            ('Loaded 1 PanelAppUK records', None),
        ])

        # and import is idempotent
        self.reset_logs()
        responses.calls.reset()
        call_command('import_all_panels', 'AU')
        call_command('import_all_panels', 'UK')
        self._assert_lists_imported()

        self.assertEqual(len(responses.calls), 3)
        self.assert_json_logs(None, [
            ('Updating PanelAppAU', None),
            ('Found 0 new and 0 existing panels to load', None),
            ('Done', None),
            ('Loaded 0 PanelAppAU records', None),
            ('Updating PanelAppUK', None),
            ('Found 0 new and 0 existing panels to load', None),
            ('Done', None),
            ('Loaded 0 PanelAppUK records', None),
        ])

    def _assert_lists_imported(self):
        locuslists_url = reverse(locus_lists)
        self.login_base_user()
        response = self.client.get(locuslists_url)
        self.assertEqual(response.status_code, 200)
        locus_lists_dict = response.json()['locusListsByGuid']

        # both existing and new lists are present
        self.assertSetEqual(set(locus_lists_dict.keys()),
                            {LOCUS_LIST_GUID, *self.EXISTING_LOCUS_LISTS,
                             'LL00007_hereditary_haemorrhagi', NEW_AU_PA_LOCUS_LIST_GUID, NEW_UK_PA_LOCUS_LIST_GUID})

        new_au_response = self.client.get(reverse(locus_list_info, args=[NEW_AU_PA_LOCUS_LIST_GUID]))
        self.assertDictEqual(new_au_response.json()['locusListsByGuid'][NEW_AU_PA_LOCUS_LIST_GUID], {
            'locusListGuid': NEW_AU_PA_LOCUS_LIST_GUID,
            'name': 'Hereditary Neuropathy_CMT - isolated',
            'description': 'PanelApp_AU_3069_0.199_Neurology and neurodevelopmental disorders',
            'items': [{'geneId': 'ENSG00000090861', 'pagene': {
                'confidenceLevel': '3', 'modeOfInheritance': 'MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown',
            }}],
            'paLocusList': {'source': 'AU', 'panelAppId': 3069},
            'numEntries': 1, 'isPublic': True, 'createdBy': None,
            'canEdit': False, 'createdDate': mock.ANY, 'lastModifiedDate': mock.ANY, 'intervalGenomeVersion': None,
        })
        new_uk_response = self.client.get(reverse(locus_list_info, args=[NEW_UK_PA_LOCUS_LIST_GUID]))
        self.assertDictEqual(new_uk_response.json()['locusListsByGuid'][NEW_UK_PA_LOCUS_LIST_GUID], {
            'locusListGuid': NEW_UK_PA_LOCUS_LIST_GUID,
            'name': 'Auditory Neuropathy Spectrum Disorde',
            'description': 'PanelApp_UK_260_1.8_Hearing and ear disorders;Non-syndromic hearing loss',
            'items': [{'geneId': 'ENSG00000139734', 'pagene': {
                'confidenceLevel': '2', 'modeOfInheritance': 'BOTH monoallelic and biallelic, autosomal or pseudoautosomal',
            }}],
            'paLocusList': {'source': 'UK', 'panelAppId': 260},
            'numEntries': 1, 'isPublic': True, 'createdBy': None,
            'canEdit': False, 'createdDate': mock.ANY, 'lastModifiedDate': mock.ANY, 'intervalGenomeVersion': None,
        })

    @mock.patch("panelapp.panelapp_utils.requests.get")
    def test_get_all_genes_exhausts_retries(self, mock_get_request):
        url = '{}/panels/123/genes/?page=1'.format(PANEL_APP_API_URL_UK)
        request_error = MaxRetryError(pool=mock.MagicMock(), url=url)
        mock_get_request.side_effect = [request_error] * 5
        with self.assertRaises(tenacity.RetryError):
            _get_all_genes(123, url, defaultdict(list))

    @mock.patch("panelapp.panelapp_utils.requests.get")
    def test_get_all_genes_retries_success(self, mock_get_request):
        url = '{}/panels/1207/genes/?page=1'.format(PANEL_APP_API_URL_UK)
        request_error = MaxRetryError(pool=mock.MagicMock(), url=url)
        page_1 = Response()
        page_1.status_code = 200
        page_1._content = (b'{"next":"https://test-panelapp.url.uk/api/v1/genes/?page=2","results": [{"panel":'
                           b'{"id": 1207, "name": "Acute intermittent porphyria"}}]}')
        page_2 = Response()
        page_2.status_code = 200
        page_2._content = b'{"results": [{"panel": {"id": 1141, "name": "Acute rhabdomyolysis"}}]}'
        mock_get_request.side_effect = [request_error] * 4 + [page_1] + [request_error] * 4 + [page_2]
        expected_res = {
            1207: [{'panel': {'id': 1207, 'name': 'Acute intermittent porphyria'}}, {'panel': {'id': 1141, 'name': 'Acute rhabdomyolysis'}}],
            1141: [{'panel': {'id': 1141, 'name': 'Acute rhabdomyolysis'}}],
        }
        self.assertEqual(_get_all_genes(1207, url, defaultdict(list)), expected_res)
