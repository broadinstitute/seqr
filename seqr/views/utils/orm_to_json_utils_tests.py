from django.contrib.auth.models import User
import mock
from copy import deepcopy
from seqr.models import Project, Family, Individual, Sample, IgvSample, SavedVariant, VariantTag, VariantFunctionalData, \
    VariantNote, LocusList, VariantSearch
from seqr.views.utils.orm_to_json_utils import get_json_for_user, _get_json_for_project, _get_json_for_family, \
    _get_json_for_individual, get_json_for_sample, get_json_for_saved_variant, get_json_for_variant_tags, \
    get_json_for_variant_functional_data_tags, get_json_for_variant_note, get_json_for_locus_list, \
    get_json_for_saved_search, get_json_for_saved_variants_with_tags, get_json_for_current_user
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, \
    PROJECT_FIELDS, FAMILY_FIELDS, INTERNAL_FAMILY_FIELDS, \
    INDIVIDUAL_FIELDS, INTERNAL_INDIVIDUAL_FIELDS, INDIVIDUAL_FIELDS_NO_FEATURES, SAMPLE_FIELDS, SAVED_VARIANT_FIELDS,  \
    FUNCTIONAL_FIELDS, SAVED_SEARCH_FIELDS, LOCUS_LIST_DETAIL_FIELDS, PA_LOCUS_LIST_FIELDS, IGV_SAMPLE_FIELDS, \
    CASE_REVIEW_FAMILY_FIELDS, TAG_FIELDS, VARIANT_NOTE_FIELDS, NO_INTERNAL_CASE_REVIEW_INDIVIDUAL_FIELDS

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

    def test_json_for_family(self):
        family = Family.objects.filter(project__has_case_review=False).first()
        json = _get_json_for_family(family)
        self.assertSetEqual(set(json.keys()), FAMILY_FIELDS)

        user = User.objects.get(username='test_user')
        json = _get_json_for_family(family, user, add_individual_guids_field=True)
        self.assertSetEqual(set(json.keys()), INTERNAL_FAMILY_FIELDS)

        case_review_family = Family.objects.filter(project__has_case_review=True).first()
        json = _get_json_for_family(case_review_family)
        self.assertSetEqual(set(json.keys()), FAMILY_FIELDS)

        fields = set()
        fields.update(INTERNAL_FAMILY_FIELDS)
        fields.update(CASE_REVIEW_FAMILY_FIELDS)
        json = _get_json_for_family(case_review_family, user, add_individual_guids_field=True)
        self.assertSetEqual(set(json.keys()), fields)

        self.mock_analyst_group.__str__.return_value = ''
        json = _get_json_for_family(family, user)
        self.assertSetEqual(set(json.keys()), FAMILY_FIELDS)

    def test_json_for_individual(self):
        individual = Individual.objects.first()
        json = _get_json_for_individual(individual)
        self.assertSetEqual(set(json.keys()), INDIVIDUAL_FIELDS_NO_FEATURES)

        json = _get_json_for_individual(individual, add_hpo_details=True)
        self.assertSetEqual(set(json.keys()), INDIVIDUAL_FIELDS)

        json = _get_json_for_individual(individual, self.manager_user, add_hpo_details=True)
        self.assertSetEqual(set(json.keys()), NO_INTERNAL_CASE_REVIEW_INDIVIDUAL_FIELDS)

        json = _get_json_for_individual(individual, self.analyst_user, add_hpo_details=True)
        self.assertSetEqual(set(json.keys()), INTERNAL_INDIVIDUAL_FIELDS)

    def test_json_for_sample(self):
        sample = Sample.objects.first()
        json = get_json_for_sample(sample)

        self.assertSetEqual(set(json.keys()), SAMPLE_FIELDS)

    def test_json_for_igv_sample(self):
        sample = IgvSample.objects.first()
        json = get_json_for_sample(sample)

        self.assertSetEqual(set(json.keys()), IGV_SAMPLE_FIELDS)

    def test_json_for_saved_variant(self):
        variant = SavedVariant.objects.get(guid='SV0000001_2103343353_r0390_100')
        json = get_json_for_saved_variant(variant)

        self.assertSetEqual(set(json.keys()), SAVED_VARIANT_FIELDS)
        self.assertListEqual(json['familyGuids'], ["F000001_1"])
        self.assertEqual(json['variantId'], '21-3343353-GAGA-G')

        fields = set()
        fields.update(SAVED_VARIANT_FIELDS)
        fields.update(list(variant.saved_variant_json.keys()))
        json = get_json_for_saved_variant(variant, add_details=True)
        self.assertSetEqual(set(json.keys()), fields)
        self.assertListEqual(json['familyGuids'], ["F000001_1"])
        self.assertEqual(json['variantId'], '21-3343353-GAGA-G')
        self.assertEqual(json['mainTranscriptId'], 'ENST00000258436')

    def test_json_for_saved_variants_with_tags(self):
        variant_guid_1 = 'SV0000001_2103343353_r0390_100'
        variant_guid_2 = 'SV0000002_1248367227_r0390_100'
        v1_tag_guids = {'VT1708633_2103343353_r0390_100', 'VT1726961_2103343353_r0390_100'}
        v2_tag_guids = {'VT1726945_2103343353_r0390_100', 'VT1726970_2103343353_r0004_tes'}
        v2_note_guids = ['VN0714935_2103343353_r0390_100']
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
        self.assertEqual(var_2['variantId'], '12-48367227-TC-T')
        self.assertSetEqual(set(var_2['tagGuids']), v2_tag_guids)
        self.assertListEqual(var_2['noteGuids'], v2_note_guids)

        self.assertSetEqual(set(json['variantTagsByGuid'].keys()), v1_tag_guids | v2_tag_guids)
        self.assertSetEqual(set(next(iter(json['variantTagsByGuid'].values())).keys()), TAG_FIELDS)
        for tag_guid in v1_tag_guids:
            self.assertListEqual(json['variantTagsByGuid'][tag_guid]['variantGuids'], [variant_guid_1])
        for tag_guid in v2_tag_guids:
            self.assertListEqual(json['variantTagsByGuid'][tag_guid]['variantGuids'], [variant_guid_2])

        self.assertListEqual(list(json['variantNotesByGuid'].keys()), v2_note_guids)
        self.assertSetEqual(set(json['variantNotesByGuid'][v2_note_guids[0]].keys()), VARIANT_NOTE_FIELDS)
        self.assertListEqual(json['variantNotesByGuid'][v2_note_guids[0]]['variantGuids'], [variant_guid_2])

        self.assertSetEqual(set(json['variantFunctionalDataByGuid'].keys()), v1_functional_guids)
        self.assertSetEqual(set(next(iter(json['variantFunctionalDataByGuid'].values())).keys()), FUNCTIONAL_FIELDS)
        for tag_guid in v1_functional_guids:
            self.assertListEqual(json['variantFunctionalDataByGuid'][tag_guid]['variantGuids'], [variant_guid_1])

    def test_json_for_variant_tags(self):
        tags = VariantTag.objects.all()[:1]
        json = get_json_for_variant_tags(tags)[0]
        self.assertSetEqual(set(json.keys()), TAG_FIELDS)

    def test_json_for_variant_functional_data(self):
        tags = VariantFunctionalData.objects.all()[:1]
        json = get_json_for_variant_functional_data_tags(tags)[0]
        self.assertSetEqual(set(json.keys()), FUNCTIONAL_FIELDS)

    def test_json_for_variant_note(self):
        tag = VariantNote.objects.first()
        json = get_json_for_variant_note(tag)
        self.assertSetEqual(set(json.keys()), VARIANT_NOTE_FIELDS)

    def test_json_for_saved_search(self):
        search = VariantSearch.objects.first()
        user = User.objects.get(username='test_user')
        json = get_json_for_saved_search(search, user)

        self.assertSetEqual(set(json.keys()), SAVED_SEARCH_FIELDS)
        self.assertTrue('hgmd' in json['search']['pathogenicity'])

        user = User.objects.get(username='test_user_collaborator')
        json = get_json_for_saved_search(search, user)
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

