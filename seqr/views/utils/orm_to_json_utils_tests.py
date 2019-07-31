from django.contrib.auth.models import User
from django.test import TestCase
from reference_data.models import GeneInfo
from seqr.models import Project, Family, Individual, Sample, SavedVariant, VariantTag, VariantFunctionalData, \
    VariantNote, LocusList, VariantSearch
from seqr.views.utils.orm_to_json_utils import _get_json_for_user, _get_json_for_project, _get_json_for_family, \
    _get_json_for_individual, _get_json_for_sample, get_json_for_saved_variant, get_json_for_variant_tag, \
    get_json_for_variant_functional_data, get_json_for_variant_note, get_json_for_locus_list, get_json_for_gene, \
    get_json_for_saved_search


class JSONUtilsTest(TestCase):
    fixtures = ['users.json', '1kg_project', 'reference_data', 'variant_searches']

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
             'isPhenotipsEnabled', 'phenotipsUserId', 'deprecatedProjectId', 'lastAccessedDate', 'hasNewSearch',
             'isMmeEnabled', 'mmePrimaryDataOwner', 'mmeContactInstitution', 'mmeContactUrl', 'genomeVersion'}
        )

    def test_json_for_family(self):
        family = Family.objects.first()
        json = _get_json_for_family(family)

        family_fields = {
            'projectGuid', 'familyGuid', 'analysedBy', 'pedigreeImage', 'familyId', 'displayName', 'description',
            'analysisNotes', 'analysisSummary', 'causalInheritanceMode', 'analysisStatus', 'pedigreeImage', 'createdDate',
            'codedPhenotype', 'postDiscoveryOmimNumber', 'pubmedIds', 'assignedAnalyst',
        }
        self.assertSetEqual(set(json.keys()), family_fields)

        family_fields.update({
            'internalAnalysisStatus', 'internalCaseReviewNotes', 'internalCaseReviewSummary', 'individualGuids',
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
        json = _get_json_for_sample(sample)

        self.assertSetEqual(
            set(json.keys()),
            {'projectGuid', 'individualGuid', 'sampleGuid', 'createdDate', 'sampleType', 'sampleId', 'sampleStatus',
             'datasetFilePath', 'loadedDate', 'datasetType', 'elasticsearchIndex'}
        )

    def test_json_for_saved_variant(self):
        variant = SavedVariant.objects.first()
        json = get_json_for_saved_variant(variant)

        fields = {'variantGuid', 'variantId', 'familyGuids', 'xpos', 'ref', 'alt'}
        self.assertSetEqual(set(json.keys()), fields)

        fields.update({'tags', 'functionalData', 'notes', 'liftedOverGenomeVersion', 'clinvar', 'originalAltAlleles',
                       'liftedOverPos', 'genomeVersion', 'mainTranscript', 'hgmd', 'liftedOverChrom', 'genotypeFilters',
                       'genotypes', 'transcripts', 'populations', 'predictions', 'chrom', 'pos', 'rsid'})
        json = get_json_for_saved_variant(variant, add_tags=True, add_details=True)
        self.assertSetEqual(set(json.keys()), fields)

    def test_json_for_variant_tag(self):
        tag = VariantTag.objects.first()
        json = get_json_for_variant_tag(tag)

        fields = {
             'tagGuid', 'name', 'category', 'color', 'searchParameters', 'searchHash', 'lastModifiedDate', 'createdBy'
        }
        self.assertSetEqual(set(json.keys()), fields)

    def test_json_for_variant_functional_data(self):
        tag = VariantFunctionalData.objects.first()
        json = get_json_for_variant_functional_data(tag)

        fields = {
             'tagGuid', 'name', 'color', 'metadata', 'metadataTitle', 'lastModifiedDate', 'createdBy'
        }
        self.assertSetEqual(set(json.keys()), fields)

    def test_json_for_variant_note(self):
        tag = VariantNote.objects.first()
        json = get_json_for_variant_note(tag)

        fields = {
             'noteGuid', 'note', 'submitToClinvar', 'lastModifiedDate', 'createdBy'
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
            gene, user=user, add_dbnsfp=True, add_omim=True, add_constraints=True, add_notes=True, add_expression=True,
            add_primate_ai=True)
        fields.update({
            'constraints', 'diseaseDesc', 'expression', 'functionDesc', 'notes', 'omimPhenotypes', 'mimNumber', 'primateAi'
        })
        self.assertSetEqual(set(json.keys()), fields)
