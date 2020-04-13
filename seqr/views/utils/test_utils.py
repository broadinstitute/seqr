# Utilities used for unit and integration tests.
from django.contrib.auth.models import User
from django.http.response import HttpResponse


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


def create_proxy_request_stub(response_status=200, reason="OK"):

    """Factory for creating a PhenoTips mock function to replace _send_request_to_phenotips.
    This allows unit tests to be decoupled from communicating with PhenoTips.

    The python mock module allows this to be done using this decorator:

    @mock.patch('seqr.views.apis.phenotips_api._send_request_to_phenotips', create_send_requests_to_phenotips_stub())
    """

    def _proxy_request_stub(*args, **kwargs):
        """Function that stubs out sending a request to PhenoTips."""

        http_response = HttpResponse(
            content='text content',
            status=response_status,
            reason=reason,
            charset='UTF-8'
        )

        return http_response

    return _proxy_request_stub


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

INDIVIDUAL_FIELDS = {
    'projectGuid', 'familyGuid', 'individualGuid', 'caseReviewStatusLastModifiedBy', 'phenotipsData', 'individualId',
    'paternalId', 'maternalId', 'sex', 'affected', 'displayName', 'notes', 'phenotipsData', 'createdDate',
    'lastModifiedDate', 'paternalGuid', 'maternalGuid', 'popPlatformFilters', 'filterFlags', 'population',
}

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
