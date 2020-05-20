# Utilities used for unit and integration tests.
from django.contrib.auth.models import User

def _check_login(test_case, url):
    """For integration tests of django views that can only be accessed by a logged-in user,
    the 1st step is to authenticate. This function checks that the given url redirects requests
    if the user isn't logged-in, and then authenticates a test user.

    Args:
        test_case (object): the django.TestCase or unittest.TestCase object
        url (string): The url of the django view being tested.
     """
    response = test_case.client.get(url)
    test_case.assertEqual(response.status_code, 302)  # check that it redirects if you don't login

    test_user = User.objects.get(username='test_user')
    test_case.client.force_login(test_user)


def login_non_staff_user(test_case):
    test_user = User.objects.get(username='test_user_non_staff')
    test_case.client.force_login(test_user)


USER_FIELDS = {'dateJoined', 'email', 'firstName', 'isStaff', 'lastLogin', 'lastName', 'username', 'displayName', 'id'}

PROJECT_FIELDS = {
    'projectGuid', 'projectCategoryGuids', 'canEdit', 'name', 'description', 'createdDate', 'lastModifiedDate',
    'lastAccessedDate',  'mmeContactUrl', 'genomeVersion', 'mmePrimaryDataOwner', 'mmeContactInstitution',
    'isMmeEnabled',
}

FAMILY_FIELDS = {
    'projectGuid', 'familyGuid', 'analysedBy', 'pedigreeImage', 'familyId', 'displayName', 'description',
    'analysisNotes', 'analysisSummary', 'analysisStatus', 'pedigreeImage', 'createdDate', 'assignedAnalyst',
    'codedPhenotype', 'postDiscoveryOmimNumber', 'pubmedIds', 'mmeNotes',
}

INTERNAL_FAMILY_FIELDS = {
    'internalAnalysisStatus', 'internalCaseReviewNotes', 'internalCaseReviewSummary', 'individualGuids', 'successStory',
    'successStoryTypes',
}
INTERNAL_FAMILY_FIELDS.update(FAMILY_FIELDS)

INDIVIDUAL_FIELDS_NO_FEATURES = {
    'projectGuid', 'familyGuid', 'individualGuid', 'caseReviewStatusLastModifiedBy', 'individualId',
    'paternalId', 'maternalId', 'sex', 'affected', 'displayName', 'notes', 'createdDate', 'lastModifiedDate',
    'paternalGuid', 'maternalGuid', 'popPlatformFilters', 'filterFlags', 'population', 'birthYear', 'deathYear',
    'onsetAge', 'maternalEthnicity', 'paternalEthnicity', 'consanguinity', 'affectedRelatives', 'expectedInheritance',
    'disorders', 'candidateGenes', 'rejectedGenes', 'arFertilityMeds', 'arIui', 'arIvf', 'arIcsi', 'arSurrogacy',
    'arDonoregg', 'arDonorsperm',
}

INDIVIDUAL_FIELDS = {'features', 'absentFeatures', 'nonstandardFeatures', 'absentNonstandardFeatures'}
INDIVIDUAL_FIELDS.update(INDIVIDUAL_FIELDS_NO_FEATURES)

INTERNAL_INDIVIDUAL_FIELDS = {
    'caseReviewStatus', 'caseReviewDiscussion', 'caseReviewStatusLastModifiedDate', 'caseReviewStatusLastModifiedBy',
}
INTERNAL_INDIVIDUAL_FIELDS.update(INDIVIDUAL_FIELDS)

SAMPLE_FIELDS = {
    'projectGuid', 'individualGuid', 'sampleGuid', 'createdDate', 'sampleType', 'sampleId', 'isActive',
    'loadedDate', 'datasetType',
}

IGV_SAMPLE_FIELDS = {
    'projectGuid', 'individualGuid', 'sampleGuid', 'filePath',
}

SAVED_VARIANT_FIELDS = {'variantGuid', 'variantId', 'familyGuids', 'xpos', 'ref', 'alt', 'selectedMainTranscriptId'}

TAG_FIELDS = {'tagGuid', 'name', 'category', 'color', 'searchHash', 'lastModifiedDate', 'createdBy', 'variantGuids'}

VARIANT_NOTE_FIELDS = {'noteGuid', 'note', 'submitToClinvar', 'lastModifiedDate', 'createdBy', 'variantGuids'}

FUNCTIONAL_FIELDS = {
    'tagGuid', 'name', 'color', 'metadata', 'metadataTitle', 'lastModifiedDate', 'createdBy', 'variantGuids',
}

SAVED_SEARCH_FIELDS = {'savedSearchGuid', 'name', 'search', 'createdById'}

LOCUS_LIST_FIELDS = {
    'locusListGuid', 'description', 'lastModifiedDate', 'numEntries', 'isPublic', 'createdBy', 'createdDate', 'canEdit',
    'name',
}
LOCUS_LIST_DETAIL_FIELDS = {'items', 'intervalGenomeVersion'}
LOCUS_LIST_DETAIL_FIELDS.update(LOCUS_LIST_FIELDS)

GENE_FIELDS = {
    'chromGrch37', 'chromGrch38', 'codingRegionSizeGrch37', 'codingRegionSizeGrch38',  'endGrch37', 'endGrch38',
    'gencodeGeneType', 'geneId', 'geneSymbol', 'startGrch37', 'startGrch38',
}

GENE_DETAIL_FIELDS = {
    'constraints', 'diseaseDesc', 'functionDesc', 'notes', 'omimPhenotypes', 'mimNumber', 'mgiMarkerId', 'geneNames',
}
GENE_DETAIL_FIELDS.update(GENE_FIELDS)

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
                'ab': 0.7021276595744681,
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
