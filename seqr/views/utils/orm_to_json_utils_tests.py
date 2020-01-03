from django.contrib.auth.models import User
from django.test import TestCase
from reference_data.models import GeneInfo
from seqr.models import Project, Family, Individual, Sample, SavedVariant, VariantTag, VariantFunctionalData, \
    VariantNote, LocusList, VariantSearch
from seqr.views.utils.orm_to_json_utils import _get_json_for_user, _get_json_for_project, _get_json_for_family, \
    _get_json_for_individual, get_json_for_sample, get_json_for_saved_variant, get_json_for_variant_tags, \
    get_json_for_variant_functional_data_tags, get_json_for_variant_note, get_json_for_locus_list, get_json_for_gene, \
    get_json_for_saved_search, get_json_for_saved_variants_with_tags


class JSONUtilsTest(TestCase):
    fixtures = ['users.json', '1kg_project', 'reference_data', 'variant_searches']
    multi_db = True

    def test_json_for_user(self):
        for user in User.objects.all():
            user_json = _get_json_for_user(user)
            user_json_keys = set(user_json.keys())

            self.assertSetEqual(
                user_json_keys,
                set(('dateJoined', 'email', 'firstName', 'isStaff', 'lastLogin', 'lastName', 'username', 'displayName', 'id'))
            )

    def test_json_for_project(self):
        project = Project.objects.first()
        user = User.objects.first()
        json = _get_json_for_project(project, user)

        self.assertSetEqual(
            set(json.keys()),
            {'projectGuid', 'projectCategoryGuids', 'canEdit', 'name', 'description', 'createdDate', 'lastModifiedDate',
             'isPhenotipsEnabled', 'phenotipsUserId', 'lastAccessedDate',  'mmeContactUrl', 'genomeVersion',
             'isMmeEnabled', 'mmePrimaryDataOwner', 'mmeContactInstitution', }
        )

    def test_json_for_family(self):
        family = Family.objects.first()
        json = _get_json_for_family(family)

        family_fields = {
            'projectGuid', 'familyGuid', 'analysedBy', 'pedigreeImage', 'familyId', 'displayName', 'description',
            'analysisNotes', 'analysisSummary', 'causalInheritanceMode', 'analysisStatus', 'pedigreeImage', 'createdDate',
            'codedPhenotype', 'postDiscoveryOmimNumber', 'pubmedIds', 'assignedAnalyst'
        }
        self.assertSetEqual(set(json.keys()), family_fields)

        family_fields.update({
            'internalAnalysisStatus', 'internalCaseReviewNotes', 'internalCaseReviewSummary', 'individualGuids',
            'successStory', 'successStoryTypes'
        })
        user = User.objects.filter(is_staff=True).first()
        json = _get_json_for_family(family, user, add_individual_guids_field=True)
        self.assertSetEqual(set(json.keys()), family_fields)

    def test_json_for_individual(self):
        individual = Individual.objects.first()
        json = _get_json_for_individual(individual)

        individual_fields = {
            'projectGuid', 'familyGuid', 'individualGuid', 'caseReviewStatusLastModifiedBy', 'phenotipsData',
            'individualId', 'paternalId', 'maternalId', 'sex', 'affected', 'displayName', 'notes',
            'phenotipsPatientId', 'phenotipsData', 'createdDate', 'lastModifiedDate', 'paternalGuid', 'maternalGuid',
            'mmeSubmittedDate', 'mmeDeletedDate', 'popPlatformFilters', 'filterFlags', 'population',
        }
        self.assertSetEqual(set(json.keys()), individual_fields)

        individual_fields.update({
            'caseReviewStatus', 'caseReviewDiscussion',
            'caseReviewStatusLastModifiedDate', 'caseReviewStatusLastModifiedBy',
        })
        user = User.objects.filter(is_staff=True).first()
        json = _get_json_for_individual(individual, user)
        self.assertSetEqual(set(json.keys()), individual_fields)

    def test_json_for_sample(self):
        sample = Sample.objects.first()
        json = get_json_for_sample(sample)

        self.assertSetEqual(
            set(json.keys()),
            {'projectGuid', 'individualGuid', 'sampleGuid', 'createdDate', 'sampleType', 'sampleId', 'isActive',
             'datasetFilePath', 'loadedDate', 'datasetType', 'elasticsearchIndex'}
        )

    def test_json_for_saved_variant(self):
        variant = SavedVariant.objects.get(guid='SV0000001_2103343353_r0390_100')
        json = get_json_for_saved_variant(variant)

        fields = {'variantGuid', 'variantId', 'familyGuids', 'xpos', 'ref', 'alt', 'selectedMainTranscriptId'}
        self.assertSetEqual(set(json.keys()), fields)
        self.assertListEqual(json['familyGuids'], ["F000001_1"])
        self.assertEqual(json['variantId'], '21-3343353-GAGA-G')

        fields.update(variant.saved_variant_json.keys())
        json = get_json_for_saved_variant(variant, add_details=True)
        self.assertSetEqual(set(json.keys()), fields)
        self.assertListEqual(json['familyGuids'], ["F000001_1"])
        self.assertEqual(json['variantId'], 'abc123')

    def test_json_for_saved_variants_with_tags(self):
        variant_guid_1 = 'SV0000001_2103343353_r0390_100'
        variant_guid_2 = 'SV0000002_1248367227_r0390_100'
        v1_tag_guids = {'VT1708633_2103343353_r0390_100', 'VT1726961_2103343353_r0390_100'}
        v2_tag_guids = {'VT1726945_2103343353_r0390_100'}
        v2_note_guids = ['VN0714935_2103343353_r0390_100']
        v1_functional_guids = {'VFD0000023_1248367227_r0390_10', 'VFD0000024_1248367227_r0390_10'}

        variants = SavedVariant.objects.filter(guid__in=[variant_guid_1, variant_guid_2])
        json = get_json_for_saved_variants_with_tags(variants)

        keys = {'variantTagsByGuid', 'variantNotesByGuid', 'variantFunctionalDataByGuid', 'savedVariantsByGuid'}
        self.assertSetEqual(set(json.keys()), keys)

        self.assertSetEqual(set(json['savedVariantsByGuid'].keys()), {variant_guid_1, variant_guid_2})
        var_fields = {
            'variantGuid', 'variantId', 'familyGuids', 'xpos', 'ref', 'alt', 'selectedMainTranscriptId',
            'tagGuids', 'noteGuids', 'functionalDataGuids',
        }
        self.assertSetEqual(set(json['savedVariantsByGuid'][variant_guid_1].keys()), var_fields)
        var_1 = json['savedVariantsByGuid'][variant_guid_1]
        self.assertEqual(var_1['variantId'], '21-3343353-GAGA-G')
        self.assertSetEqual(set(var_1['tagGuids']), v1_tag_guids)
        self.assertSetEqual(set(var_1['functionalDataGuids']), v1_functional_guids)
        var_2 = json['savedVariantsByGuid'][variant_guid_2]
        self.assertEqual(var_2['variantId'], '1-248367227-TC-T')
        self.assertSetEqual(set(var_2['tagGuids']), v2_tag_guids)
        self.assertListEqual(var_2['noteGuids'], v2_note_guids)

        self.assertSetEqual(set(json['variantTagsByGuid'].keys()), v1_tag_guids | v2_tag_guids)
        tag_fields = {
            'tagGuid', 'name', 'category', 'color', 'searchParameters', 'searchHash', 'lastModifiedDate', 'createdBy',
            'variantGuids'
        }
        self.assertSetEqual(set(json['variantTagsByGuid'].values()[0].keys()), tag_fields)
        for tag_guid in v1_tag_guids:
            self.assertListEqual(json['variantTagsByGuid'][tag_guid]['variantGuids'], [variant_guid_1])
        for tag_guid in v2_tag_guids:
            self.assertListEqual(json['variantTagsByGuid'][tag_guid]['variantGuids'], [variant_guid_2])

        self.assertListEqual(json['variantNotesByGuid'].keys(), v2_note_guids)
        note_fields = {
            'noteGuid', 'note', 'submitToClinvar', 'lastModifiedDate', 'createdBy', 'variantGuids'
        }
        self.assertSetEqual(set(json['variantNotesByGuid'][v2_note_guids[0]].keys()), note_fields)
        self.assertListEqual(json['variantNotesByGuid'][v2_note_guids[0]]['variantGuids'], [variant_guid_2])

        self.assertSetEqual(set(json['variantFunctionalDataByGuid'].keys()), v1_functional_guids)
        functional_fields = {
            'tagGuid', 'name', 'color', 'metadata', 'metadataTitle', 'lastModifiedDate', 'createdBy', 'variantGuids'
        }
        self.assertSetEqual(set(json['variantFunctionalDataByGuid'].values()[0].keys()), functional_fields)
        for tag_guid in v1_functional_guids:
            self.assertListEqual(json['variantFunctionalDataByGuid'][tag_guid]['variantGuids'], [variant_guid_1])

    def test_json_for_variant_tags(self):
        tags = VariantTag.objects.all()[:1]
        json = get_json_for_variant_tags(tags)[0]

        fields = {
            'tagGuid', 'name', 'category', 'color', 'searchParameters', 'searchHash', 'lastModifiedDate', 'createdBy',
            'variantGuids'
        }
        self.assertSetEqual(set(json.keys()), fields)

    def test_json_for_variant_functional_data(self):
        tags = VariantFunctionalData.objects.all()[:1]
        json = get_json_for_variant_functional_data_tags(tags)[0]

        fields = {
             'tagGuid', 'name', 'color', 'metadata', 'metadataTitle', 'lastModifiedDate', 'createdBy', 'variantGuids'
        }
        self.assertSetEqual(set(json.keys()), fields)

    def test_json_for_variant_note(self):
        tag = VariantNote.objects.first()
        json = get_json_for_variant_note(tag)

        fields = {
             'noteGuid', 'note', 'submitToClinvar', 'lastModifiedDate', 'createdBy', 'variantGuids'
        }
        self.assertSetEqual(set(json.keys()), fields)

    def test_json_for_saved_search(self):
        search = VariantSearch.objects.first()
        user = User.objects.filter(is_staff=True).first()
        json = get_json_for_saved_search(search, user)

        fields = {'savedSearchGuid', 'name', 'search', 'createdById'}
        self.assertSetEqual(set(json.keys()), fields)
        self.assertTrue('hgmd' in json['search']['pathogenicity'])

        user = User.objects.filter(is_staff=False).first()
        json = get_json_for_saved_search(search, user)
        self.assertSetEqual(set(json.keys()), fields)
        self.assertFalse('hgmd' in json['search']['pathogenicity'])

    def test_json_for_locus_list(self):
        locus_list = LocusList.objects.first()
        user = User.objects.filter().first()
        json = get_json_for_locus_list(locus_list, user)

        fields = {
            'locusListGuid', 'description', 'lastModifiedDate', 'numEntries', 'isPublic', 'createdBy', 'createdDate',
             'canEdit', 'name', 'items', 'intervalGenomeVersion'
        }
        self.assertSetEqual(set(json.keys()), fields)

    def test_json_for_gene(self):
        gene = GeneInfo.objects.get(id=1)
        json = get_json_for_gene(gene)

        fields = {
            'chromGrch37', 'chromGrch38', 'codingRegionSizeGrch37', 'codingRegionSizeGrch38',  'endGrch37', 'endGrch38',
            'gencodeGeneType', 'geneId', 'geneSymbol', 'startGrch37', 'startGrch38',
        }
        self.assertSetEqual(set(json.keys()), fields)

        user = User.objects.filter().first()
        json = get_json_for_gene(
            gene, user=user, add_dbnsfp=True, add_omim=True, add_constraints=True, add_notes=True, add_primate_ai=True)
        fields.update({
            'constraints', 'diseaseDesc', 'functionDesc', 'notes', 'omimPhenotypes', 'mimNumber',
            'primateAi', 'geneNames',
        })
        self.assertSetEqual(set(json.keys()), fields)
