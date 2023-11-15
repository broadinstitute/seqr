import mock
from django.urls.base import reverse
from seqr.views.apis.awesomebar_api import awesomebar_autocomplete_handler
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase


@mock.patch('seqr.views.utils.permissions_utils.safe_redis_get_json', lambda *args: None)
class AwesomebarAPITest(object):

    @mock.patch('seqr.views.apis.awesomebar_api.MAX_STRING_LENGTH', 20)
    @mock.patch('seqr.views.apis.awesomebar_api.MAX_RESULTS_PER_CATEGORY', 5)
    def test_awesomebar_autocomplete_handler(self):
        url = reverse(awesomebar_autocomplete_handler)
        self.check_require_login(url)

        response = self.client.get(url + "?q=")
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'matches': {}})

        response = self.client.get(url+"?q=1")
        self.assertEqual(response.status_code, 200)
        # No objects returned as user has no access
        self.assertSetEqual(
            set(response.json()['matches'].keys()), {'genes'}
        )

        self.login_collaborator()
        response = self.client.get(url + "?q=%201%20")
        self.assertEqual(response.status_code, 200)
        matches = response.json()['matches']
        self.assertSetEqual(set(matches.keys()), {'projects', 'families', 'analysis_groups', 'individuals', 'genes'})

        projects = matches['projects']['results']
        self.assertEqual(len(projects), 1)
        self.assertDictEqual(projects[0], {
            'key': 'R0001_1kg',
            'title':  '1kg project nåme wit',
            'description': '',
            'href': '/project/R0001_1kg/project_page',
        })

        families = matches['families']['results']
        self.assertEqual(len(families), 5)
        self.assertListEqual([f['title'] for f in families], ['1', '10', '11', '12-a', '2_1'])
        self.assertDictEqual(families[0], {
            'key': 'F000001_1',
            'title': '1',
            'description': '(1kg project nåme with uniçøde)',
            'href': '/project/R0001_1kg/family_page/F000001_1',
        })
        self.assertDictEqual(families[4], {
            'key': 'F000002_2',
            'title': '2_1',
            'description': '(1kg project nåme with uniçøde)',
            'href': '/project/R0001_1kg/family_page/F000002_2',
        })

        individuals = matches['individuals']['results']
        self.assertEqual(len(individuals), 5)
        self.assertListEqual(
            [i['title'] for i in individuals], ['NA19678', 'NA19679', 'NA20881', 'NA19675_1', 'HG00731_a'])
        self.assertDictEqual(individuals[3], {
            'key': 'I000001_na19675',
            'title': 'NA19675_1',
            'description': '(1kg project nåme with uniçøde: family 1)',
            'href': '/project/R0001_1kg/family_page/F000001_1',
        })
        self.assertDictEqual(individuals[4], {
            'key': 'I000004_hg00731',
            'title': 'HG00731_a',
            'description': '(1kg project nåme with uniçøde: family 2_1)',
            'href': '/project/R0001_1kg/family_page/F000002_2',
        })

        analysis_groups = matches['analysis_groups']['results']
        self.assertEqual(len(analysis_groups), 1)
        self.assertDictEqual(analysis_groups[0], {
            'key': 'AG0000183_test_group',
            'title': 'Test Group 1',
            'description': '(1kg project nåme with uniçøde)',
            'href': '/project/R0001_1kg/analysis_group/AG0000183_test_group',
        })

        genes = matches['genes']['results']
        self.assertEqual(len(genes), 5)
        self.assertListEqual(
            [g['title'] for g in genes],
            ['ENSG00000135953', 'ENSG00000177000', 'ENSG00000186092', 'ENSG00000185097', 'DDX11L1'],
        )
        self.assertDictEqual(genes[2], {
            'key': 'ENSG00000186092',
            'title': 'ENSG00000186092',
            'description': '(OR4F5)',
            'href': '/summary_data/gene_info/ENSG00000186092',
        })
        self.assertDictEqual(genes[4], {
            'key': 'ENSG00000223972',
            'title': 'DDX11L1',
            'description': '(ENSG00000223972)',
            'href': '/summary_data/gene_info/ENSG00000223972',
        })

        response = self.client.get(url + "?q=T&categories=project_groups,projects,hpo_terms,omim")
        self.assertEqual(response.status_code, 200)
        matches = response.json()['matches']
        self.assertSetEqual(set(matches.keys()), {'projects', 'project_groups', 'omim', 'hpo_terms'})

        project_groups = matches['project_groups']['results']
        self.assertEqual(len(project_groups), 1)
        self.assertDictEqual(project_groups[0], {
            'key': 'PC000002_categry_with_unicde',
            'title': 'cåtegøry with uniçød',
            'description': '',
            'href': 'PC000002_categry_with_unicde',
        })

        omim = matches['omim']['results']
        self.assertEqual(len(omim), 1)
        self.assertDictEqual(omim[0], {
            'key': 615120,
            'title': 'Myasthenic syndrome, congenital, 8, with pre- and postsynaptic defects',
            'description': '(615120)',
        })

        hpo_terms = matches['hpo_terms']['results']
        self.assertEqual(len(hpo_terms), 5)
        self.assertListEqual([h['title'] for h in hpo_terms], [
            'Tetralogy of Fallot', 'Arrhythmia',  'Autosomal dominant inheritance', 'Complete atrioventricular canal defect',
            'Defect in the atrial septum',
        ])
        self.assertDictEqual(hpo_terms[0], {
            'key': 'HP:0001636',
            'title': 'Tetralogy of Fallot',
            'description': '(HP:0001636)',
            'category': 'HP:0033127',
        })

        # Test fuzzy matching
        response = self.client.get(url + "?q=2-&categories=families")
        self.assertEqual(response.status_code, 200)
        families = response.json()['matches']['families']['results']
        self.assertEqual(len(families), 3)
        self.assertListEqual([f['title'] for f in families], ['12-a', '2_1', '42'])


# Tests for AnVIL access disabled
class LocalAwesomebarAPITest(AuthenticationTestCase, AwesomebarAPITest):
    fixtures = ['users', '1kg_project', 'reference_data']


# Test for permissions from AnVIL only
class AnvilAwesomebarAPITest(AnvilAuthenticationTestCase, AwesomebarAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data']

    def test_awesomebar_autocomplete_handler(self):
        super(AnvilAwesomebarAPITest, self).test_awesomebar_autocomplete_handler()
        calls = [
            mock.call(self.no_access_user),
            mock.call(self.collaborator_user),
            mock.call(self.collaborator_user),
        ]
        self.mock_list_workspaces.assert_has_calls(calls)
        self.assert_no_extra_anvil_calls()
        self.mock_get_ws_access_level.assert_not_called()
