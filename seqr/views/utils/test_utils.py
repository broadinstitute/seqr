# Utilities used for unit and integration tests.
from django.contrib.auth.models import User, Group
from django.test import TestCase
from guardian.shortcuts import assign_perm
import json
import mock
import re
from urllib.parse import quote_plus, urlparse
from urllib3_mock import Responses

from seqr.models import Project, CAN_VIEW, CAN_EDIT

WINDOW_REGEX_TEMPLATE = 'window\.{key}=(?P<value>[^)<]+)'

def _initialize_users(cls):
    cls.super_user = User.objects.get(username='test_superuser')
    cls.analyst_user = User.objects.get(username='test_user')
    cls.pm_user = User.objects.get(username='test_pm_user')
    cls.data_manager_user = User.objects.get(username='test_data_manager')
    cls.manager_user = User.objects.get(username='test_user_manager')
    cls.collaborator_user = User.objects.get(username='test_user_collaborator')
    cls.no_access_user = User.objects.get(username='test_user_no_access')
    cls.inactive_user = User.objects.get(username='test_user_inactive')
    cls.no_policy_user = User.objects.get(username='test_user_no_policies')

class AuthenticationTestCase(TestCase):
    databases = '__all__'
    SUPERUSER = 'superuser'
    ANALYST = 'analyst'
    PM = 'project_manager'
    DATA_MANAGER = 'data_manager'
    MANAGER = 'manager'
    COLLABORATOR = 'collaborator'
    AUTHENTICATED_USER = 'authenticated'
    NO_POLICY_USER = 'no_policy'

    super_user = None
    analyst_user = None
    pm_user = None
    data_manager_user = None
    manager_user = None
    collaborator_user = None
    no_access_user = None
    inactive_user = None
    no_policy_user = None

    def setUp(self):
        patcher = mock.patch('seqr.views.utils.permissions_utils.SEQR_PRIVACY_VERSION', 2.1)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.permissions_utils.SEQR_TOS_VERSION', 1.3)
        patcher.start()
        self.addCleanup(patcher.stop)

    @classmethod
    def setUpTestData(cls):
        _initialize_users(cls)

        edit_group = Group.objects.get(pk=2)
        view_group = Group.objects.get(pk=3)
        edit_group.user_set.add(cls.manager_user)
        view_group.user_set.add(cls.manager_user, cls.collaborator_user)
        assign_perm(user_or_group=edit_group, perm=CAN_EDIT, obj=Project.objects.filter(can_edit_group=edit_group))
        assign_perm(user_or_group=edit_group, perm=CAN_VIEW, obj=Project.objects.filter(can_view_group=edit_group))
        assign_perm(user_or_group=view_group, perm=CAN_VIEW, obj=Project.objects.filter(can_view_group=view_group))

    def check_require_login(self, url, **request_kwargs):
        self._check_login(url, self.AUTHENTICATED_USER, **request_kwargs)

    def check_require_login_no_policies(self, url, **request_kwargs):
        self._check_login(url, self.NO_POLICY_USER, **request_kwargs)

    def check_collaborator_login(self, url, **request_kwargs):
        self._check_login(url, self.COLLABORATOR, **request_kwargs)

    def check_manager_login(self, url, **request_kwargs):
        return self._check_login(url, self.MANAGER, **request_kwargs)

    def check_analyst_login(self, url):
        self._check_login(url, self.ANALYST)

    def check_pm_login(self, url):
        self._check_login(url, self.PM)

    def check_data_manager_login(self, url):
        self._check_login(url, self.DATA_MANAGER)

    def check_superuser_login(self, url, **request_kwargs):
        self._check_login(url, self.SUPERUSER, **request_kwargs)

    def login_base_user(self):
        self.client.force_login(self.no_access_user)

    def login_collaborator(self):
        self.client.force_login(self.collaborator_user)

    def login_manager(self):
        self.client.force_login(self.manager_user)

    def login_analyst_user(self):
        self.client.force_login(self.analyst_user)

    def login_pm_user(self):
        self.client.force_login(self.pm_user)

    def login_data_manager_user(self):
        self.client.force_login(self.data_manager_user)

    def _check_login(self, url, permission_level, request_data=None, login_redirect_url='/api/login-required-error',
                     policy_redirect_url='/api/policy-required-error', permission_denied_error=403):
        """For integration tests of django views that can only be accessed by a logged-in user,
        the 1st step is to authenticate. This function checks that the given url redirects requests
        if the user isn't logged-in, and then authenticates a test user.

        Args:
            test_case (object): the django.TestCase or unittest.TestCase object
            url (string): The url of the django view being tested.
            permission_level (string): what level of permission this url requires
         """
        # check that it redirects if you don't login
        parsed_url = urlparse(url)
        next_query = quote_plus('?{}'.format(parsed_url.query)) if parsed_url.query else ''
        next_url = 'next={}{}'.format('/'.join(map(quote_plus, parsed_url.path.split('/'))), next_query)
        login_required_url = '{}?{}'.format(login_redirect_url, next_url)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, login_required_url)

        self.client.force_login(self.inactive_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, permission_denied_error)

        self.client.force_login(self.no_policy_user)
        if permission_level == self.NO_POLICY_USER:
            return

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '{}?{}'.format(policy_redirect_url, next_url))

        self.client.force_login(self.no_access_user)
        if permission_level == self.AUTHENTICATED_USER:
            return

        # check that users without view permission users can't access collaborator URLs
        if permission_level == self.COLLABORATOR:
            if request_data:
                response = self.client.post(url, content_type='application/json', data=json.dumps(request_data))
            else:
                response = self.client.get(url)
            self.assertEqual(response.status_code, permission_denied_error)

        self.login_collaborator()
        if permission_level == self.COLLABORATOR:
            return

        response = self.client.get(url)
        self.assertEqual(response.status_code, permission_denied_error)

        self.client.force_login(self.manager_user)
        if permission_level == self.MANAGER:
            return response

        response = self.client.get(url)
        self.assertEqual(response.status_code, permission_denied_error)

        self.login_analyst_user()
        if permission_level in self.ANALYST:
            return

        response = self.client.get(url)
        self.assertEqual(response.status_code, permission_denied_error)

        self.login_pm_user()
        if permission_level in self.PM:
            return

        response = self.client.get(url)
        self.assertEqual(response.status_code, permission_denied_error)

        self.login_data_manager_user()
        if permission_level in self.DATA_MANAGER:
            return

        response = self.client.get(url)
        self.assertEqual(response.status_code, permission_denied_error)

        self.client.force_login(self.super_user)

    def get_initial_page_window(self, key, response):
        content = response.content.decode('utf-8')
        regex = WINDOW_REGEX_TEMPLATE.format(key=key)
        self.assertRegex(content, regex)
        m = re.search(regex, content)
        return json.loads(m.group('value'))

    def get_initial_page_json(self, response):
        return self.get_initial_page_window('initialJSON', response)

TEST_WORKSPACE_NAMESPACE = 'my-seqr-billing'
TEST_WORKSPACE_NAME = 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de'
TEST_WORKSPACE_NAME1 = 'anvil-project 1000 Genomes Demo'
TEST_NO_PROJECT_WORKSPACE_NAME = 'anvil-no-project-workspace1'
TEST_NO_PROJECT_WORKSPACE_NAME2 = 'anvil-no-project-workspace2'

TEST_SERVICE_ACCOUNT = 'test_account@my-seqr.iam.gserviceaccount.com'

ANVIL_WORKSPACES = [{
    'workspace_namespace': TEST_WORKSPACE_NAMESPACE,
    'workspace_name': TEST_WORKSPACE_NAME,
    'public': False,
    'acl': {
        'Test_User_Manager@test.com': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": True,
            "canCompute": True
        },
        'test_user_collaborator@test.com': {
            "accessLevel": "READER",
            "pending": False,
            "canShare": True,
            "canCompute": True
        },
        TEST_SERVICE_ACCOUNT: {
            "accessLevel": "READER",
            "pending": False,
            "canShare": False,
            "canCompute": True
        },
        'test_user_not_registered@test.com': {
            "accessLevel": "READER",
            "pending": True,
            "canShare": False,
            "canCompute": True
        },
        'test_user_pure_anvil@test.com': {
            "accessLevel": "READER",
            "pending": False,
            "canShare": False,
            "canCompute": True
        }
    },
    'workspace': {
        'bucketName': 'test_bucket'
    },
}, {
    'workspace_namespace': TEST_WORKSPACE_NAMESPACE,
    'workspace_name': TEST_WORKSPACE_NAME1,
    'public': False,
    'acl': {
        'test_user_manager@test.com': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": True,
            "canCompute": True
        },
        'test_user_collaborator@test.com': {
            "accessLevel": "READER",
            "pending": False,
            "canShare": True,
            "canCompute": False
        }
    },
    'workspace': {
        'bucketName': 'test_bucket'
    },
}, {
    'workspace_namespace': TEST_WORKSPACE_NAMESPACE,
    'workspace_name': TEST_NO_PROJECT_WORKSPACE_NAME,
    'public': True,
    'acl': {
        'test_user_manager@test.com': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": True,
            "canCompute": True
        },
        'test_user_collaborator@test.com': {
            "accessLevel": "READER",
            "pending": False,
            "canShare": False,
            "canCompute": True
        }
    },
    'workspace': {
        'bucketName': 'test_bucket'
    },
}, {
    'workspace_namespace': TEST_WORKSPACE_NAMESPACE,
    'workspace_name': TEST_NO_PROJECT_WORKSPACE_NAME2,
    'public': False,
    'acl': {
        'test_user_manager@test.com': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": True,
            "canCompute": True
        },
        'test_pm_user@test.com': {
            "accessLevel": "WRITER",
            "pending": False,
            "canShare": False,
            "canCompute": False
        },
    },
    'workspace': {
        'bucketName': 'test_bucket'
    },
}
]


TEST_TERRA_API_ROOT_URL =  'https://terra.api/'
TEST_OAUTH2_KEY = 'abc123'

# the time must the same as that in 'auth_time' in the social_auth fixture data
TOKEN_AUTH_TIME = 1603287741
REGISTER_RESPONSE = '{"enabled":{"ldap":true,"allUsersGroup":true,"google":true},"userInfo": {"userEmail":"test@test.com","userSubjectId":"123456"}}'


def get_ws_acl_side_effect(user, workspace_namespace, workspace_name):
    wss = filter(lambda x: x['workspace_namespace'] == workspace_namespace and x['workspace_name'] == workspace_name, ANVIL_WORKSPACES)
    wss = list(wss)
    return wss[0]['acl'] if wss else {}


def get_ws_al_side_effect(user, workspace_namespace, workspace_name, meta_fields=None):
    wss = filter(lambda x: x['workspace_namespace'] == workspace_namespace and x['workspace_name'] == workspace_name, ANVIL_WORKSPACES)
    wss = list(wss)
    acl = wss[0]['acl'] if wss else {}
    user_acl = next((v for k, v in acl.items() if user.email.lower() == k.lower()), None)
    access_level = {
        'accessLevel': user_acl['accessLevel'],
        'canShare': user_acl['canShare'],
    } if user_acl else {}
    if meta_fields and 'workspace.bucketName' in meta_fields:
        access_level['workspace'] = {'bucketName': wss[0]['workspace']['bucketName']}
    return access_level


def get_workspaces_side_effect(user):
    return [
        {
            'public': ws['public'],
            'workspace':{
                'namespace': ws['workspace_namespace'],
                'name': ws['workspace_name']
            }
        } for ws in ANVIL_WORKSPACES if any(user.email.lower() == k.lower() for k in ws['acl'].keys())
    ]


class AnvilAuthenticationTestCase(AuthenticationTestCase):
    @classmethod
    def setUpTestData(cls):
        _initialize_users(cls)

    # mock the terra apis
    def setUp(self):
        patcher = mock.patch('seqr.views.utils.terra_api_utils.TERRA_API_ROOT_URL', TEST_TERRA_API_ROOT_URL)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.terra_api_utils.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY', TEST_OAUTH2_KEY)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.orm_to_json_utils.SERVICE_ACCOUNT_FOR_ANVIL', TEST_SERVICE_ACCOUNT)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.terra_api_utils.time')
        patcher.start().return_value = TOKEN_AUTH_TIME + 10
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.permissions_utils.list_anvil_workspaces')
        self.mock_list_workspaces = patcher.start()
        self.mock_list_workspaces.side_effect = get_workspaces_side_effect
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.permissions_utils.user_get_workspace_acl')
        self.mock_get_ws_acl = patcher.start()
        self.mock_get_ws_acl.side_effect = get_ws_acl_side_effect
        self.addCleanup(patcher.stop)
        patcher = mock.patch('seqr.views.utils.permissions_utils.user_get_workspace_access_level')
        self.mock_get_ws_access_level = patcher.start()
        self.mock_get_ws_access_level.side_effect = get_ws_al_side_effect
        self.addCleanup(patcher.stop)
        super(AnvilAuthenticationTestCase, self).setUp()


# inherit AnvilAuthenticationTestCase for the mocks of AnVIL permissions.
class MixAuthenticationTestCase(AnvilAuthenticationTestCase):
    LOCAL_USER = 'local_user'

    # use the local permissions set-up by AuthenticationTestCase
    @classmethod
    def setUpTestData(cls):
        AuthenticationTestCase.setUpTestData()
        cls.local_user = User.objects.get(username = 'test_local_user')
        view_group = Group.objects.get(pk=3)
        view_group.user_set.add(cls.local_user)


# The responses library for mocking requests does not work with urllib3 (which is used by elasticsearch)
# The urllib3_mock library works for those requests, but it has limited functionality, so this extension adds helper
# methods for easier usage
class Urllib3Responses(Responses):
    def add_json(self, url, json_response, method=None, match_querystring=True, **kwargs):
        if not method:
            method = self.GET
        body = json.dumps(json_response)
        self.add(method, url, match_querystring=match_querystring, content_type='application/json', body=body, **kwargs)

    def replace_json(self, url, *args, **kwargs):
        existing_index = next(i for i, match in enumerate(self._urls) if match['url'] == url)
        self.add_json(url, *args, **kwargs)
        self._urls[existing_index] = self._urls.pop()

    def call_request_json(self, index=-1):
        return json.loads(self.calls[index].request.body)


urllib3_responses = Urllib3Responses()


USER_FIELDS = {
    'dateJoined', 'email', 'firstName', 'lastLogin', 'lastName', 'username', 'displayName', 'id',  'isActive', 'isAnvil',
    'isAnalyst', 'isDataManager', 'isPm', 'isSuperuser',
}
PROJECT_FIELDS = {
    'projectGuid', 'projectCategoryGuids', 'canEdit', 'name', 'description', 'createdDate', 'lastModifiedDate',
    'lastAccessedDate',  'mmeContactUrl', 'genomeVersion', 'mmePrimaryDataOwner', 'mmeContactInstitution',
    'isMmeEnabled', 'workspaceName', 'workspaceNamespace', 'hasCaseReview', 'enableHgmd', 'isDemo', 'allUserDemo',
    'userIsCreator',
}

ANALYSIS_GROUP_FIELDS = {'analysisGroupGuid', 'description', 'name', 'projectGuid', 'familyGuids'}

FAMILY_FIELDS = {
    'projectGuid', 'familyGuid', 'analysedBy', 'pedigreeImage', 'familyId', 'displayName', 'description',
    'analysisStatus', 'pedigreeImage', 'createdDate', 'assignedAnalyst', 'codedPhenotype', 'postDiscoveryOmimNumber',
    'pedigreeDataset', 'analysisStatusLastModifiedDate', 'analysisStatusLastModifiedBy'
}
CASE_REVIEW_FAMILY_FIELDS = {
    'caseReviewNotes', 'caseReviewSummary'
}
INTERNAL_FAMILY_FIELDS = {
    'individualGuids', 'successStory', 'successStoryTypes', 'pubmedIds',
}
INTERNAL_FAMILY_FIELDS.update(FAMILY_FIELDS)

FAMILY_NOTE_FIELDS = {'noteGuid', 'note', 'noteType', 'lastModifiedDate', 'createdBy', 'familyGuid'}

INDIVIDUAL_FIELDS_NO_FEATURES = {
    'projectGuid', 'familyGuid', 'individualGuid', 'individualId',
    'paternalId', 'maternalId', 'sex', 'affected', 'displayName', 'notes', 'createdDate', 'lastModifiedDate',
    'paternalGuid', 'maternalGuid', 'popPlatformFilters', 'filterFlags', 'population', 'birthYear', 'deathYear',
    'onsetAge', 'maternalEthnicity', 'paternalEthnicity', 'consanguinity', 'affectedRelatives', 'expectedInheritance',
    'disorders', 'candidateGenes', 'rejectedGenes', 'arFertilityMeds', 'arIui', 'arIvf', 'arIcsi', 'arSurrogacy',
    'arDonoregg', 'arDonorsperm', 'svFlags',
}

INDIVIDUAL_FIELDS = {'features', 'absentFeatures', 'nonstandardFeatures', 'absentNonstandardFeatures'}
INDIVIDUAL_FIELDS.update(INDIVIDUAL_FIELDS_NO_FEATURES)

INTERNAL_INDIVIDUAL_FIELDS = {
    'caseReviewStatus', 'caseReviewDiscussion', 'caseReviewStatusLastModifiedDate', 'caseReviewStatusLastModifiedBy',
    'probandRelationship',
}
INTERNAL_INDIVIDUAL_FIELDS.update(INDIVIDUAL_FIELDS)

SAMPLE_FIELDS = {
    'projectGuid', 'familyGuid', 'individualGuid', 'sampleGuid', 'createdDate', 'sampleType', 'sampleId', 'isActive',
    'loadedDate', 'datasetType', 'elasticsearchIndex',
}

IGV_SAMPLE_FIELDS = {
    'projectGuid', 'familyGuid', 'individualGuid', 'sampleGuid', 'filePath', 'sampleId', 'sampleType',
}

SAVED_VARIANT_FIELDS = {'variantGuid', 'variantId', 'familyGuids', 'xpos', 'ref', 'alt', 'selectedMainTranscriptId', 'acmgClassification'}

TAG_FIELDS = {
    'tagGuid', 'name', 'category', 'color', 'searchHash', 'metadata', 'lastModifiedDate', 'createdBy', 'variantGuids',
}

VARIANT_NOTE_FIELDS = {'noteGuid', 'note', 'submitToClinvar', 'lastModifiedDate', 'createdBy', 'variantGuids'}

FUNCTIONAL_FIELDS = {
    'tagGuid', 'name', 'color', 'metadata', 'metadataTitle', 'lastModifiedDate', 'createdBy', 'variantGuids',
}

SAVED_SEARCH_FIELDS = {'savedSearchGuid', 'name', 'order', 'search', 'createdById'}

LOCUS_LIST_FIELDS = {
    'locusListGuid', 'description', 'lastModifiedDate', 'numEntries', 'isPublic', 'createdBy', 'createdDate', 'canEdit',
    'name',
}
PA_LOCUS_LIST_FIELDS = {'paLocusList'}
LOCUS_LIST_DETAIL_FIELDS = {'items', 'intervalGenomeVersion'}
LOCUS_LIST_DETAIL_FIELDS.update(LOCUS_LIST_FIELDS)

MATCHMAKER_SUBMISSION_FIELDS = {
    'submissionGuid', 'individualGuid', 'createdDate', 'lastModifiedDate', 'deletedDate',
}

TAG_TYPE_FIELDS = {
    'variantTagTypeGuid', 'name', 'category', 'description', 'color', 'order', 'metadataTitle',
}

GENE_FIELDS = {
    'chromGrch37', 'chromGrch38', 'codingRegionSizeGrch37', 'codingRegionSizeGrch38',  'endGrch37', 'endGrch38',
    'gencodeGeneType', 'geneId', 'geneSymbol', 'startGrch37', 'startGrch38',
}
GENE_VARIANT_DISPLAY_FIELDS = {
    'constraints', 'omimPhenotypes', 'mimNumber', 'cnSensitivity', 'genCc', 'clinGen',
}
GENE_VARIANT_DISPLAY_FIELDS.update(GENE_FIELDS)
GENE_VARIANT_FIELDS = {
    'diseaseDesc', 'functionDesc', 'geneNames', 'primateAi',
}
GENE_VARIANT_FIELDS.update(GENE_VARIANT_DISPLAY_FIELDS)

GENE_DETAIL_FIELDS = {'notes', 'mgiMarkerId'}
GENE_DETAIL_FIELDS.update(GENE_VARIANT_FIELDS)

VARIANTS = [
    {
        'alt': 'G',
        'ref': 'GAGA',
        'chrom': '21',
        'pos': 3343400,
        'xpos': 21003343400,
        'genomeVersion': '38',
        'liftedOverChrom': '21',
        'liftedOverPos': 3343353,
        'liftedOverGenomeVersion': '37',
        'variantId': '21-3343400-GAGA-G',
        'mainTranscriptId': 'ENST00000623083',
        'transcripts': {
            'ENSG00000227232': [
                {
                    'aminoAcids': 'G/S',
                    'geneSymbol': 'WASH7P',
                    'biotype': 'protein_coding',
                    'category': 'missense',
                    'cdnaEnd': 1075,
                    'cdnaStart': 1075,
                    'codons': 'Ggt/Agt',
                    'consequenceTerms': ['missense_variant'],
                    'hgvs': 'ENSP00000485442.1:p.Gly359Ser',
                    'hgvsc': 'ENST00000623083.3:c.1075G>A',
                    'hgvsp': 'ENSP00000485442.1:p.Gly359Ser',
                    'majorConsequence': 'missense_variant',
                    'majorConsequenceRank': 11,
                    'proteinId': 'ENSP00000485442',
                    'transcriptId': 'ENST00000623083',
                    'transcriptRank': 0
                }
            ],
            'ENSG00000268903': [
                {
                    'aminoAcids': 'G/S',
                    'biotype': 'protein_coding',
                    'category': 'missense',
                    'cdnaEnd': 1338,
                    'cdnaStart': 1338,
                    'codons': 'Ggt/Agt',
                    'consequenceTerms': ['missense_variant'],
                    'geneId': 'ENSG00000268903',
                    'hgvs': 'ENSP00000485351.1:p.Gly368Ser',
                    'hgvsc': 'ENST00000624735.1:c.1102G>A',
                    'hgvsp': 'ENSP00000485351.1:p.Gly368Ser',
                    'majorConsequence': 'missense_variant',
                    'majorConsequenceRank': 11,
                    'proteinId': 'ENSP00000485351',
                    'transcriptId': 'ENST00000624735',
                    'transcriptRank': 1
                }
            ]
        },
        'familyGuids': ['F000001_1', 'F000002_2'],
        'genotypes': {
            'NA19675': {
                'sampleId': 'NA19675',
                'ab': 0.702127659574,
                'gq': 46.0,
                'numAlt': 1,
                'dp': '50',
                'ad': '14,33'
            },
            'NA19679': {
                'sampleId': 'NA19679',
                'ab': 0.0,
                'gq': 99.0,
                'numAlt': 0,
                'dp': '45',
                'ad': '45,0'
            }
        }
    },
    {
        'alt': 'A',
        'ref': 'AAAG',
        'chrom': '3',
        'pos': 835,
        'xpos': 3000000835,
        'genomeVersion': '37',
        'liftedOverGenomeVersion': '',
        'variantId': '3-835-AAAG-A',
        'transcripts': {},
        'familyGuids': ['F000001_1'],
        'genotypes': {
            'NA19679': {
                'sampleId': 'NA19679',
                'ab': 0.0,
                'gq': 99.0,
                'numAlt': 0,
                'dp': '45',
                'ad': '45,0'
            }
        }
    },
    {
        'alt': 'T',
        'ref': 'TC',
        'chrom': '12',
        'pos': 48367227,
        'xpos': 1248367227,
        'genomeVersion': '37',
        'liftedOverGenomeVersion': '',
        'variantId': '12-48367227-TC-T',
        'transcripts': {'ENSG00000233653': {}},
        'familyGuids': ['F000002_2'],
        'genotypes': {}
    }
]

SINGLE_VARIANT = {
    'alt': 'A',
    'ref': 'G',
    'chrom': '1',
    'pos': 46394160,
    'xpos': 1046394160,
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'variantId': '1-46394160-G-A',
    'transcripts': {'ENSG00000233653': {}},
    'familyGuids': ['F000002_2'],
    'genotypes': {}
}

TRANSCRIPT_1 = {
  'aminoAcids': 'LL/L',
  'biotype': 'protein_coding',
  'lof': None,
  'lofFlags': None,
  'majorConsequenceRank': 10,
  'codons': 'ctTCTc/ctc',
  'geneSymbol': 'MFSD9',
  'domains': [
    'Transmembrane_helices:TMhelix',
    'PROSITE_profiles:PS50850',
  ],
  'canonical': 1,
  'transcriptRank': 0,
  'cdnaEnd': 421,
  'lofFilter': None,
  'hgvs': 'ENSP00000258436.5:p.Leu126del',
  'hgvsc': 'ENST00000258436.5:c.375_377delTCT',
  'cdnaStart': 419,
  'transcriptId': 'ENST00000258436',
  'proteinId': 'ENSP00000258436',
  'category': 'missense',
  'geneId': 'ENSG00000135953',
  'hgvsp': 'ENSP00000258436.5:p.Leu126del',
  'majorConsequence': 'inframe_deletion',
  'consequenceTerms': [
    'inframe_deletion'
  ]
}
TRANSCRIPT_2 = {
  'aminoAcids': 'P/X',
  'biotype': 'protein_coding',
  'lof': None,
  'lofFlags': None,
  'majorConsequenceRank': 4,
  'codons': 'Ccc/cc',
  'geneSymbol': 'OR2M3',
  'domains': [
    'Transmembrane_helices:TMhelix',
    'Prints_domain:PR00237',
  ],
  'canonical': 1,
  'transcriptRank': 0,
  'cdnaEnd': 897,
  'lofFilter': None,
  'hgvs': 'ENSP00000389625.1:p.Leu288SerfsTer10',
  'hgvsc': 'ENST00000456743.1:c.862delC',
  'cdnaStart': 897,
  'transcriptId': 'ENST00000456743',
  'proteinId': 'ENSP00000389625',
  'category': 'lof',
  'geneId': 'ENSG00000228198',
  'hgvsp': 'ENSP00000389625.1:p.Leu288SerfsTer10',
  'majorConsequence': 'frameshift_variant',
  'consequenceTerms': [
    'frameshift_variant'
  ]
}
TRANSCRIPT_3 = {
  'aminoAcids': 'LL/L',
  'biotype': 'nonsense_mediated_decay',
  'lof': None,
  'lofFlags': None,
  'majorConsequenceRank': 10,
  'codons': 'ctTCTc/ctc',
  'geneSymbol': 'MFSD9',
  'domains': [
    'Transmembrane_helices:TMhelix',
    'Gene3D:1',
  ],
  'canonical': None,
  'transcriptRank': 1,
  'cdnaEnd': 143,
  'lofFilter': None,
  'hgvs': 'ENSP00000413641.1:p.Leu48del',
  'hgvsc': 'ENST00000428085.1:c.141_143delTCT',
  'cdnaStart': 141,
  'transcriptId': 'ENST00000428085',
  'proteinId': 'ENSP00000413641',
  'category': 'missense',
  'geneId': 'ENSG00000135953',
  'hgvsp': 'ENSP00000413641.1:p.Leu48del',
  'majorConsequence': 'frameshift_variant',
  'consequenceTerms': [
    'frameshift_variant',
    'inframe_deletion',
    'NMD_transcript_variant'
  ]
}

PARSED_VARIANTS = [
    {
        'alt': 'T',
        'chrom': '1',
        'bothsidesSupport': None,
        'clinvar': {'clinicalSignificance': None, 'alleleId': None, 'variationId': None, 'goldStars': None},
        'familyGuids': ['F000003_3'],
        'cpxIntervals': None,
        'algorithms': None,
        'genotypes': {
            'I000007_na20870': {
                'ab': 1, 'ad': None, 'gq': 99, 'sampleId': 'NA20870', 'numAlt': 2, 'dp': 74, 'pl': None,
                'sampleType': 'WES',
            }
        },
        'genomeVersion': '37',
        'genotypeFilters': '',
        'hgmd': {'accession': None, 'class': None},
        'liftedOverChrom': None,
        'liftedOverGenomeVersion': None,
        'liftedOverPos': None,
        'mainTranscriptId': TRANSCRIPT_3['transcriptId'],
        'selectedMainTranscriptId': None,
        'originalAltAlleles': ['T'],
        'populations': {
            'callset': {'an': 32, 'ac': 2, 'hom': None, 'af': 0.063, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
            'g1k': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0, 'filter_af': None, 'het': 0, 'id': None},
            'gnomad_genomes': {'an': 30946, 'ac': 4, 'hom': 0, 'af': 0.00012925741614425127, 'hemi': 0, 'filter_af': 0.0004590314436538903, 'het': 0, 'id': None},
            'exac': {'an': 121308, 'ac': 8, 'hom': 0, 'af': 0.00006589, 'hemi': 0, 'filter_af': 0.0006726888333653661, 'het': 0, 'id': None},
            'gnomad_exomes': {'an': 245930, 'ac': 16, 'hom': 0, 'af': 0.00006505916317651364, 'hemi': 0, 'filter_af': 0.0009151523074911753, 'het': 0, 'id': None},
            'topmed': {'an': 125568, 'ac': 21, 'hom': 0, 'af': 0.00016724, 'hemi': 0, 'filter_af': None, 'het': None, 'id': None},
            'sv_callset': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
            'gnomad_svs': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None, 'hom': None, 'het': None, 'id': None},
        },
        'pos': 248367227,
        'predictions': {'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None,
                        'polyphen': None, 'dann': None, 'sift': None, 'cadd': '25.9', 'metasvm': None, 'primate_ai': None,
                        'gerp_rs': None, 'mpc': None, 'phastcons_100_vert': None, 'strvctvre': None,
                        'splice_ai_consequence': None},
        'ref': 'TC',
        'rsid': None,
        'transcripts': {
            'ENSG00000135953': [TRANSCRIPT_3],
            'ENSG00000228198': [TRANSCRIPT_2],
        },
        'variantId': '1-248367227-TC-T',
        'xpos': 1248367227,
        'end': None,
        'svType': None,
        'svTypeDetail': None,
        'numExon': None,
        'rg37LocusEnd': None,
        '_sort': [1248367227],
    },
    {
        'alt': 'G',
        'chrom': '2',
        'bothsidesSupport': None,
        'clinvar': {'clinicalSignificance': None, 'alleleId': None, 'variationId': None, 'goldStars': None},
        'familyGuids': ['F000002_2', 'F000003_3'],
        'cpxIntervals': None,
        'algorithms': None,
        'genotypes': {
            'I000004_hg00731': {
                'ab': 0, 'ad': None, 'gq': 99, 'sampleId': 'HG00731', 'numAlt': 2, 'dp': 67, 'pl': None,
                'sampleType': 'WES',
            },
            'I000005_hg00732': {
                'ab': 0, 'ad': None, 'gq': 96, 'sampleId': 'HG00732', 'numAlt': 1, 'dp': 42, 'pl': None,
                'sampleType': 'WES',
            },
            'I000006_hg00733': {
                'ab': 0, 'ad': None, 'gq': 96, 'sampleId': 'HG00733', 'numAlt': 0, 'dp': 42, 'pl': None,
                'sampleType': 'WES',
            },
            'I000007_na20870': {
                'ab': 0.70212764, 'ad': None, 'gq': 46, 'sampleId': 'NA20870', 'numAlt': 1, 'dp': 50, 'pl': None,
                'sampleType': 'WES',
            }
        },
        'genotypeFilters': '',
        'genomeVersion': '37',
        'hgmd': {'accession': None, 'class': None},
        'liftedOverGenomeVersion': None,
        'liftedOverChrom': None,
        'liftedOverPos': None,
        'mainTranscriptId': TRANSCRIPT_1['transcriptId'],
        'selectedMainTranscriptId': TRANSCRIPT_2['transcriptId'],
        'originalAltAlleles': ['G'],
        'populations': {
            'callset': {'an': 32, 'ac': 1, 'hom': None, 'af': 0.031, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
            'g1k': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0, 'filter_af': None, 'het': 0, 'id': None},
            'gnomad_genomes': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0, 'filter_af': None, 'het': 0, 'id': None},
            'exac': {'an': 121336, 'ac': 6, 'hom': 0, 'af': 0.00004942, 'hemi': 0, 'filter_af': 0.000242306760358614, 'het': 0, 'id': None},
            'gnomad_exomes': {'an': 245714, 'ac': 6, 'hom': 0, 'af': 0.000024418633044922146, 'hemi': 0, 'filter_af': 0.00016269686320447742, 'het': 0, 'id': None},
            'topmed': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0, 'filter_af': None, 'het': None, 'id': None},
            'sv_callset': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
            'gnomad_svs': {'ac': None, 'af': None, 'an': None, 'filter_af': None, 'hemi': None, 'hom': None, 'het': None, 'id': None},
        },
        'pos': 103343353,
        'predictions': {
            'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None, 'polyphen': None,
            'dann': None, 'sift': None, 'cadd': None, 'metasvm': None, 'primate_ai': 1, 'gerp_rs': None,
            'mpc': None, 'phastcons_100_vert': None, 'strvctvre': None, 'splice_ai_consequence': None,
        },
        'ref': 'GAGA',
        'rsid': None,
        'transcripts': {
            'ENSG00000135953': [TRANSCRIPT_1],
            'ENSG00000228198': [TRANSCRIPT_2],
        },
        'variantId': '2-103343353-GAGA-G',
        'xpos': 2103343353,
        'end': None,
        'svType': None,
        'svTypeDetail': None,
        'numExon': None,
        'rg37LocusEnd': None,
        '_sort': [2103343353],
    },
]

PARSED_SV_VARIANT = {
    'alt': None,
    'chrom': '1',
    'bothsidesSupport': True,
    'familyGuids': ['F000002_2'],
    'cpxIntervals': None,
    'algorithms': None,
    'genotypes': {
        'I000004_hg00731': {
            'sampleId': 'HG00731', 'sampleType': 'WES', 'numAlt': -1, 'geneIds': ['ENSG00000228198'],
            'cn': 1, 'end': None, 'start': None, 'numExon': None, 'defragged': False, 'qs': 33, 'gq': None,
            'prevCall': False, 'prevOverlap': False, 'newCall': True,
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'numAlt': -1, 'sampleType': None,  'geneIds': None, 'gq': None,
            'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None, 'isRef': True,
            'prevCall': None, 'prevOverlap': None, 'newCall': None,
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'numAlt': -1,  'geneIds': None, 'gq': None,
            'cn': 2, 'end': 49045890, 'start': 49045987, 'numExon': 1, 'defragged': False, 'qs': 80,
            'prevCall': False, 'prevOverlap': True, 'newCall': False,
        },
    },
    'clinvar': {'clinicalSignificance': None, 'alleleId': None, 'variationId': None, 'goldStars': None},
    'hgmd': {'accession': None, 'class': None},
    'genomeVersion': '37',
    'genotypeFilters': '',
    'liftedOverChrom': None,
    'liftedOverGenomeVersion': None,
    'liftedOverPos': None,
    'mainTranscriptId': None,
    'selectedMainTranscriptId': None,
    'originalAltAlleles': [],
    'populations': {
        'callset': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
        'g1k': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
        'gnomad_genomes': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
        'exac': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
        'gnomad_exomes': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
        'topmed': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
        'sv_callset': {'an': 10088, 'ac': 7, 'hom': None, 'af': 0.000693825, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
        'gnomad_svs': {'ac': 0, 'af': 0, 'an': 0, 'filter_af': None, 'hemi': 0, 'hom': 0, 'het': 0, 'id': None},
    },
    'pos': 49045487,
    'predictions': {'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None,
                    'polyphen': None, 'dann': None, 'sift': None, 'cadd': None, 'metasvm': None, 'primate_ai': None,
                    'gerp_rs': None, 'mpc': None, 'phastcons_100_vert': None, 'strvctvre': 0.374,
                    'splice_ai_consequence': None},
    'ref': None,
    'rsid': None,
    'transcripts': {
        'ENSG00000228198': [
            {
              'geneId': 'ENSG00000228198'
            },
        ],
        'ENSG00000135953': [
            {
              'geneId': 'ENSG00000135953'
            },
        ],
    },
    'variantId': 'prefix_19107_DEL',
    'xpos': 1049045487,
    'end': 49045899,
    'svType': 'INS',
    'svTypeDetail': None,
    'svSourceDetail': {'chrom': '9'},
    'numExon': 2,
    'rg37LocusEnd': None,
    '_sort': [1049045387],
}

PARSED_SV_WGS_VARIANT = {
    'alt': None,
    'chrom': '2',
    'bothsidesSupport': None,
    'familyGuids': ['F000014_14'],
    'cpxIntervals': [{'chrom': '2', 'end': 3000, 'start': 1000, 'type': 'DUP'},
                     {'chrom': '20', 'end': 13000, 'start': 11000, 'type': 'INV'}],
    'algorithms': 'wham, manta',
    'genotypes': {
        'I000018_na21234': {
            'gq': 33, 'sampleId': 'NA21234', 'numAlt': 1, 'geneIds': None,
            'cn': -1, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None, 'sampleType': 'WGS',
            'prevCall': None, 'prevOverlap': None, 'newCall': None,
        },
    },
    'clinvar': {'clinicalSignificance': None, 'alleleId': None, 'variationId': None, 'goldStars': None},
    'hgmd': {'accession': None, 'class': None},
    'genomeVersion': '37',
    'genotypeFilters': '',
    'liftedOverChrom': None,
    'liftedOverGenomeVersion': None,
    'liftedOverPos': None,
    'mainTranscriptId': None,
    'selectedMainTranscriptId': None,
    'originalAltAlleles': [],
    'populations': {
        'callset': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
        'g1k': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
        'gnomad_genomes': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
        'exac': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
        'gnomad_exomes': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
        'topmed': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
        'sv_callset': {'an': 10088, 'ac': 7, 'hom': None, 'af': 0.000693825, 'hemi': None, 'filter_af': None, 'het': None, 'id': None},
        'gnomad_svs': {'ac': 0, 'af': 0.00679, 'an': 0, 'filter_af': None, 'hemi': 0, 'hom': 0, 'het': 0, 'id': 'gnomAD-SV_v2.1_BND_1_1'},
    },
    'pos': 49045387,
    'predictions': {'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None,
                    'polyphen': None, 'dann': None, 'sift': None, 'cadd': None, 'metasvm': None, 'primate_ai': None,
                    'gerp_rs': None, 'mpc': None, 'phastcons_100_vert': None, 'strvctvre': None,
                    'splice_ai_consequence': None},
    'ref': None,
    'rsid': None,
    'transcripts': {
        'ENSG00000228198': [
            {
                'geneSymbol': 'OR4F5',
                'majorConsequence': 'DUP_PARTIAL',
                'geneId': 'ENSG00000228198'
            },
        ],
    },
    'variantId': 'prefix_19107_CPX',
    'xpos': 2049045387,
    'end': 12345678,
    'endChrom': '20',
    'svType': 'CPX',
    'svTypeDetail': 'dupINV',
    'numExon': None,
    'rg37LocusEnd': {'contig': '20', 'position': 12326326},
    '_sort': [2049045387],
}

GOOGLE_API_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_ACCESS_TOKEN_URL = 'https://accounts.google.com/o/oauth2/token'

GOOGLE_TOKEN_RESULT = '{"access_token":"ya29.c.EXAMPLE","expires_in":3599,"token_type":"Bearer"}'
