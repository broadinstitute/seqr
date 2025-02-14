from django.contrib.auth.models import User
import mock
from copy import deepcopy
from seqr.models import Project, Sample, IgvSample, SavedVariant, VariantNote, LocusList, VariantSearch
from seqr.views.utils.orm_to_json_utils import get_json_for_user, _get_json_for_project, \
    get_json_for_sample, get_json_for_saved_variants, get_json_for_variant_note, get_json_for_locus_list, \
    get_json_for_saved_searches, get_json_for_saved_variants_with_tags, get_json_for_current_user
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, \
    PROJECT_FIELDS, SAMPLE_FIELDS, SAVED_VARIANT_FIELDS,  \
    FUNCTIONAL_FIELDS, SAVED_SEARCH_FIELDS, LOCUS_LIST_DETAIL_FIELDS, PA_LOCUS_LIST_FIELDS, IGV_SAMPLE_FIELDS, \
    TAG_FIELDS, VARIANT_NOTE_FIELDS

class JSONUtilsTest(object):
    databases = '__all__'

    def test_json_for_user(self):
        users = User.objects.all()

        with self.assertRaises(ValueError) as ec:
            get_json_for_user(users.first(), ['foobar', 'first_name', 'lastName', 'is_analyst'])
        self.assertEqual(str(ec.exception), 'Invalid user fields: foobar, lastName, is_analyst')

        for user in users:
            user_json = get_json_for_user(user, ['first_name', 'email', 'display_name', 'is_active', 'is_data_manager'])
            self.assertSetEqual(
                set(user_json.keys()),
                {'firstName', 'email', 'displayName', 'isActive', 'isDataManager'},
            )

    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP')
    def test_json_for_current_user(self, mock_pm_group):
        pm_user = User.objects.get(username='test_pm_user')
        superuser = User.objects.get(username='test_superuser')

        mock_pm_group.__eq__.side_effect = lambda s: str(mock_pm_group) == s
        mock_pm_group.__bool__.return_value = True
        mock_pm_group.resolve_expression.return_value = 'project-managers'
        mock_pm_group.__str__.return_value = 'project-managers'

        pm_json = {
            'id': 17,
            'username': 'test_pm_user',
            'firstName': 'Test PM User',
            'lastName': '',
            'displayName': 'Test PM User',
            'email': 'test_pm_user@test.com',
            'dateJoined': mock.ANY,
            'lastLogin': None,
            'isActive': True,
            'isAnalyst': True,
            'isAnvil': self.IS_ANVIL,
            'isDataManager': False,
            'isPm': True,
            'isSuperuser': False,
        }
        self.assertDictEqual(get_json_for_current_user(pm_user), pm_json)

        superuser_json = {
            'id': 15,
            'username': 'test_superuser',
            'firstName': 'Test Superuser',
            'lastName': '',
            'displayName': 'Test Superuser',
            'email': 'test_superuser@test.com',
            'dateJoined': mock.ANY,
            'lastLogin': mock.ANY,
            'isActive': True,
            'isAnalyst': False,
            'isAnvil': self.IS_ANVIL,
            'isDataManager': True,
            'isPm': False,
            'isSuperuser': True,
        }
        self.assertDictEqual(get_json_for_current_user(superuser), superuser_json)

        self.mock_analyst_group.__str__.return_value = ''
        mock_pm_group.__str__.return_value = ''
        mock_pm_group.__bool__.return_value = False

        pm_json.update({
            'isAnalyst': False,
            'isPm': False,
        })
        self.assertDictEqual(get_json_for_current_user(pm_user), pm_json)

        superuser_json.update({
            'isPm': False if self.IS_ANVIL else True,
        })
        self.assertDictEqual(get_json_for_current_user(superuser), superuser_json)

    def test_json_for_project(self):
        project = Project.objects.first()
        user = User.objects.first()
        json = _get_json_for_project(project, user)

        self.assertSetEqual(set(json.keys()), PROJECT_FIELDS)

    def test_json_for_sample(self):
        sample = Sample.objects.first()
        json = get_json_for_sample(sample)

        self.assertSetEqual(set(json.keys()), SAMPLE_FIELDS)

    def test_json_for_igv_sample(self):
        sample = IgvSample.objects.first()
        json = get_json_for_sample(sample)

        self.assertSetEqual(set(json.keys()), IGV_SAMPLE_FIELDS)

    def test_json_for_saved_variant(self):
        variants = SavedVariant.objects.filter(guid='SV0000001_2103343353_r0390_100')
        json = get_json_for_saved_variants(variants)[0]

        self.assertSetEqual(set(json.keys()), SAVED_VARIANT_FIELDS)
        self.assertListEqual(json['familyGuids'], ["F000001_1"])
        self.assertEqual(json['variantId'], '21-3343353-GAGA-G')

        fields = set()
        fields.update(SAVED_VARIANT_FIELDS)
        fields.update(list(variants.first().saved_variant_json.keys()))
        json = get_json_for_saved_variants(variants, add_details=True)[0]
        self.assertSetEqual(set(json.keys()), fields)
        self.assertListEqual(json['familyGuids'], ["F000001_1"])
        self.assertEqual(json['variantId'], '21-3343353-GAGA-G')
        self.assertEqual(json['mainTranscriptId'], 'ENST00000258436')

    def test_json_for_saved_variants_with_tags(self):
        variant_guid_1 = 'SV0000001_2103343353_r0390_100'
        variant_guid_2 = 'SV0000002_1248367227_r0390_100'
        v1_tag_guids = {'VT1708633_2103343353_r0390_100', 'VT1726961_2103343353_r0390_100'}
        v2_tag_guids = {'VT1726945_2103343353_r0390_100', 'VT1726970_2103343353_r0004_tes', 'VT1726985_2103343353_r0390_100'}
        v2_note_guids = ['VN0714935_2103343353_r0390_100', 'VN0714937_2103343353_r0390_100']
        v1_functional_guids = {
            'VFD0000023_1248367227_r0390_10', 'VFD0000024_1248367227_r0390_10', 'VFD0000025_1248367227_r0390_10',
            'VFD0000026_1248367227_r0390_10'}

        variants = SavedVariant.objects.filter(guid__in=[variant_guid_1, variant_guid_2])
        json = get_json_for_saved_variants_with_tags(variants)

        keys = {'variantTagsByGuid', 'variantNotesByGuid', 'variantFunctionalDataByGuid', 'savedVariantsByGuid'}
        self.assertSetEqual(set(json.keys()), keys)

        self.assertSetEqual(set(json['savedVariantsByGuid'].keys()), {variant_guid_1, variant_guid_2})
        var_fields = {'tagGuids', 'noteGuids', 'functionalDataGuids'}
        var_fields.update(SAVED_VARIANT_FIELDS)
        self.assertSetEqual(set(json['savedVariantsByGuid'][variant_guid_1].keys()), var_fields)
        var_1 = json['savedVariantsByGuid'][variant_guid_1]
        self.assertEqual(var_1['variantId'], '21-3343353-GAGA-G')
        self.assertSetEqual(set(var_1['tagGuids']), v1_tag_guids)
        self.assertSetEqual(set(var_1['functionalDataGuids']), v1_functional_guids)
        var_2 = json['savedVariantsByGuid'][variant_guid_2]
        self.assertEqual(var_2['variantId'], '1-248367227-TC-T')
        self.assertSetEqual(set(var_2['tagGuids']), v2_tag_guids)
        self.assertSetEqual(set(var_2['noteGuids']), set(v2_note_guids))

        self.assertSetEqual(set(json['variantTagsByGuid'].keys()), v1_tag_guids | v2_tag_guids)
        self.assertSetEqual(set(json['variantTagsByGuid']['VT1726961_2103343353_r0390_100'].keys()), TAG_FIELDS)
        for tag_guid in v1_tag_guids:
            self.assertListEqual(json['variantTagsByGuid'][tag_guid]['variantGuids'], [variant_guid_1])
        for tag_guid in v2_tag_guids:
            self.assertListEqual(json['variantTagsByGuid'][tag_guid]['variantGuids'], [variant_guid_2])

        self.assertSetEqual(set(json['variantNotesByGuid'].keys()), set(v2_note_guids))
        self.assertSetEqual(set(json['variantNotesByGuid'][v2_note_guids[0]].keys()), VARIANT_NOTE_FIELDS)
        self.assertListEqual(json['variantNotesByGuid'][v2_note_guids[0]]['variantGuids'], [variant_guid_2])

        self.assertSetEqual(set(json['variantFunctionalDataByGuid'].keys()), v1_functional_guids)
        self.assertSetEqual(set(next(iter(json['variantFunctionalDataByGuid'].values())).keys()), FUNCTIONAL_FIELDS)
        for tag_guid in v1_functional_guids:
            self.assertListEqual(json['variantFunctionalDataByGuid'][tag_guid]['variantGuids'], [variant_guid_1])

    def test_json_for_variant_note(self):
        tag = VariantNote.objects.first()
        json = get_json_for_variant_note(tag)
        fields = deepcopy(VARIANT_NOTE_FIELDS)
        fields.remove('variantGuids')
        self.assertSetEqual(set(json.keys()), fields)

    def test_json_for_saved_search(self):
        searches = VariantSearch.objects.filter(name='De Novo/Dominant Restrictive')
        user = User.objects.get(username='test_user')
        json = get_json_for_saved_searches(searches, user)[0]

        self.assertSetEqual(set(json.keys()), SAVED_SEARCH_FIELDS)
        self.assertTrue('hgmd' in json['search']['pathogenicity'])

        user = User.objects.get(username='test_user_collaborator')
        json = get_json_for_saved_searches(searches, user)[0]
        self.assertSetEqual(set(json.keys()), SAVED_SEARCH_FIELDS)
        self.assertFalse('hgmd' in json['search']['pathogenicity'])

    def test_json_for_locus_list(self):
        locus_list = LocusList.objects.first()
        user = User.objects.filter().first()
        json = get_json_for_locus_list(locus_list, user)
        exp_detail_fields = deepcopy(LOCUS_LIST_DETAIL_FIELDS)
        exp_detail_fields.update(PA_LOCUS_LIST_FIELDS)
        self.assertSetEqual(set(json.keys()), exp_detail_fields)


class LocalJSONUtilsTest(AuthenticationTestCase, JSONUtilsTest):
    fixtures = ['users', '1kg_project', 'variant_searches']
    IS_ANVIL = False


class AnvilJSONUtilsTest(AnvilAuthenticationTestCase, JSONUtilsTest):
    fixtures = ['users', 'social_auth', '1kg_project', 'variant_searches']
    IS_ANVIL = True

