import json
import mock
from copy import deepcopy

from django.db import transaction
from django.urls.base import reverse
from elasticsearch.exceptions import ConnectionTimeout, TransportError

from seqr.models import VariantSearchResults, LocusList, Project, VariantSearch
from seqr.utils.elasticsearch.utils import InvalidIndexException, InvalidSearchException
from seqr.views.apis.variant_search_api import query_variants_handler, query_single_variant_handler, \
    export_variants_handler, search_context_handler, get_saved_search_handler, create_saved_search_handler, \
    update_saved_search_handler, delete_saved_search_handler, get_variant_gene_breakdown
from seqr.views.utils.test_utils import AuthenticationTestCase, VARIANTS, AnvilAuthenticationTestCase,\
    MixAuthenticationTestCase, GENE_VARIANT_FIELDS, GENE_VARIANT_DISPLAY_FIELDS, PROJECT_FIELDS, LOCUS_LIST_FIELDS, FAMILY_FIELDS, \
    PA_LOCUS_LIST_FIELDS, INDIVIDUAL_FIELDS, FUNCTIONAL_FIELDS, IGV_SAMPLE_FIELDS, FAMILY_NOTE_FIELDS, ANALYSIS_GROUP_FIELDS, \
    VARIANT_NOTE_FIELDS, TAG_FIELDS

LOCUS_LIST_GUID = 'LL00049_pid_genes_autosomal_do'
PROJECT_GUID = 'R0001_1kg'
SEARCH_HASH = 'd380ed0fd28c3127d07a64ea2ba907d7'
SEARCH = {'filters': {}, 'inheritance': None}
PROJECT_FAMILIES = [{'projectGuid': PROJECT_GUID, 'familyGuids': ['F000001_1', 'F000002_2']}]

VARIANTS_WITH_DISCOVERY_TAGS = deepcopy(VARIANTS)
VARIANTS_WITH_DISCOVERY_TAGS[2]['discoveryTags'] = [{
    'savedVariant': {
        'variantGuid': 'SV0000006_1248367227_r0003_tes',
        'familyGuid': 'F000011_11',
        'projectGuid': 'R0003_test',
    },
    'tagGuid': 'VT1726961_2103343353_r0003_tes',
    'name': 'Tier 1 - Novel gene and phenotype',
    'category': 'CMG Discovery Tags',
    'color': '#03441E',
    'searchHash': None,
    'metadata': None,
    'lastModifiedDate': '2018-05-29T16:32:51.449Z',
    'createdBy': None,
}]

PROJECT_CONTEXT_FIELDS = {'locusListGuids', 'datasetTypes', 'analysisGroupsLoaded'}
PROJECT_CONTEXT_FIELDS.update(PROJECT_FIELDS)

PROJECT_TAG_TYPE_FIELDS = {'projectGuid', 'variantTagTypes', 'variantFunctionalTagTypes'}

EXPECTED_SEARCH_RESPONSE = {
    'searchedVariants': VARIANTS,
    'savedVariantsByGuid': {'SV0000001_2103343353_r0390_100': mock.ANY, 'SV0000002_1248367227_r0390_100': mock.ANY},
    'genesById': {'ENSG00000227232': mock.ANY, 'ENSG00000268903': mock.ANY, 'ENSG00000233653': mock.ANY},
    'search': {
        'search': SEARCH,
        'projectFamilies': [{'projectGuid': PROJECT_GUID, 'familyGuids': mock.ANY}],
        'totalResults': 3,
    },
    'variantTagsByGuid': {
        'VT1708633_2103343353_r0390_100': mock.ANY, 'VT1726945_2103343353_r0390_100': mock.ANY,
        'VT1726970_2103343353_r0004_tes': mock.ANY, 'VT1726961_2103343353_r0390_100': mock.ANY,
    },
    'variantNotesByGuid': {'VN0714935_2103343353_r0390_100': mock.ANY},
    'variantFunctionalDataByGuid': {
        'VFD0000023_1248367227_r0390_10': mock.ANY, 'VFD0000024_1248367227_r0390_10': mock.ANY,
        'VFD0000025_1248367227_r0390_10': mock.ANY, 'VFD0000026_1248367227_r0390_10': mock.ANY,
    },
    'locusListsByGuid': {LOCUS_LIST_GUID: mock.ANY},
    'rnaSeqData': {'I000001_na19675': {'outliers': {'ENSG00000268903': mock.ANY}}},
}

EXPECTED_SEARCH_CONTEXT_RESPONSE = {
    'savedSearchesByGuid': {
        'VS0000001_de_novo_dominant_res': mock.ANY, 'VS0000002_recessive_restrictiv': mock.ANY, 'VS0000003_de_novo_dominant_per': mock.ANY,
    },
    'projectsByGuid': {PROJECT_GUID: mock.ANY},
    'familiesByGuid': mock.ANY,
    'analysisGroupsByGuid': {'AG0000183_test_group': mock.ANY, 'AG0000185_accepted': mock.ANY},
    'locusListsByGuid': {LOCUS_LIST_GUID: mock.ANY, 'LL00005_retina_proteome': mock.ANY},
}

EXPECTED_SEARCH_FAMILY_CONTEXT_RESPONSE = {
    'familiesByGuid': {'F000001_1': mock.ANY, 'F000002_2': mock.ANY},
    'individualsByGuid': mock.ANY,
    'igvSamplesByGuid': mock.ANY,
    'locusListsByGuid': {LOCUS_LIST_GUID: mock.ANY},
    'familyNotesByGuid': mock.ANY,
}
EXPECTED_SEARCH_FAMILY_CONTEXT_RESPONSE.update(deepcopy(EXPECTED_SEARCH_RESPONSE))

def _get_es_variants(results_model, **kwargs):
    results_model.save()
    return deepcopy(VARIANTS), len(VARIANTS)


def _get_empty_es_variants(results_model, **kwargs):
    results_model.save()
    return [], 0


COMP_HET_VARAINTS = [[VARIANTS[2], VARIANTS[1]]]
def _get_compound_het_es_variants(results_model, **kwargs):
    results_model.save()
    return deepcopy(COMP_HET_VARAINTS), 1


@mock.patch('seqr.views.utils.permissions_utils.safe_redis_get_json', lambda *args: None)
class VariantSearchAPITest(object):

    def _assert_expected_search_context(self, response_json):
        self.assertSetEqual(set(response_json), set(EXPECTED_SEARCH_CONTEXT_RESPONSE))
        self.assertDictEqual(response_json, EXPECTED_SEARCH_CONTEXT_RESPONSE)

        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID].keys()), PROJECT_CONTEXT_FIELDS)
        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID]['datasetTypes']), {'VARIANTS', 'SV'})

        locus_list_fields = deepcopy(LOCUS_LIST_FIELDS)
        locus_list_fields.update(PA_LOCUS_LIST_FIELDS)
        locus_list_fields.remove('numEntries')
        locus_list_fields.remove('canEdit')
        self.assertSetEqual(set(response_json['locusListsByGuid'][LOCUS_LIST_GUID].keys()), locus_list_fields)
        self.assertSetEqual(set(response_json['analysisGroupsByGuid']['AG0000183_test_group'].keys()), ANALYSIS_GROUP_FIELDS)

        self.assertEqual(len(response_json['familiesByGuid']), 11)
        self.assertSetEqual(set(response_json['familiesByGuid']['F000001_1'].keys()), {'projectGuid', 'familyGuid', 'displayName'})
        self.assertEqual(response_json['familiesByGuid']['F000001_1']['displayName'], '1')


    def _assert_expected_results_family_context(self, response_json, locus_list_detail=False):
        self._assert_expected_results_context(response_json, locus_list_detail=locus_list_detail)

        family_fields = {'individualGuids'}
        family_fields.update(FAMILY_FIELDS)
        if len(response_json['familiesByGuid']) > 1:
            self.assertSetEqual(set(response_json['familiesByGuid']['F000002_2'].keys()), family_fields)

        family_fields.add('hasRnaTpmData')
        self.assertSetEqual(set(response_json['familiesByGuid']['F000001_1'].keys()), family_fields)

        self.assertEqual(len(response_json['individualsByGuid']), len(response_json['familiesByGuid'])*3)
        individual_fields = {'igvSampleGuids'}
        individual_fields.update(INDIVIDUAL_FIELDS)
        self.assertSetEqual(set(response_json['individualsByGuid']['I000001_na19675'].keys()), individual_fields)

        self.assertEqual(len(response_json['igvSamplesByGuid']), 1)
        self.assertSetEqual(set(response_json['igvSamplesByGuid']['S000145_na19675'].keys()), IGV_SAMPLE_FIELDS)

        self.assertEqual(len(response_json['familyNotesByGuid']), 3)
        self.assertSetEqual(set(response_json['familyNotesByGuid']['FAN000001_1'].keys()), FAMILY_NOTE_FIELDS)

    def _assert_expected_results_context(self, response_json, has_pa_detail=True, locus_list_detail=False):
        gene_fields = {'locusListGuids'}
        gene_fields.update(GENE_VARIANT_FIELDS)
        basic_gene_id = next(gene_id for gene_id in ['ENSG00000268903', 'ENSG00000233653'] if gene_id in response_json['genesById'])
        self.assertSetEqual(set(response_json['genesById'][basic_gene_id].keys()), gene_fields)
        if has_pa_detail:
            gene_fields.add('panelAppDetail')
            self.assertSetEqual(set(response_json['genesById']['ENSG00000227232'].keys()), gene_fields)
            self.assertListEqual(
                response_json['genesById']['ENSG00000227232']['locusListGuids'], [LOCUS_LIST_GUID]
            )
            self.assertDictEqual(
                response_json['genesById']['ENSG00000227232']['panelAppDetail'], {LOCUS_LIST_GUID: {'confidence': '3', 'moi': 'BIALLELIC, autosomal or pseudoautosomal'}}
            )

        locus_list_fields = {'intervals'}
        if locus_list_detail:
            locus_list_fields.update(LOCUS_LIST_FIELDS)
            if has_pa_detail:
                locus_list_fields.update({'paLocusList'})
        self.assertSetEqual(set(response_json['locusListsByGuid'][LOCUS_LIST_GUID].keys()), locus_list_fields)
        intervals = response_json['locusListsByGuid'][LOCUS_LIST_GUID]['intervals']
        self.assertEqual(len(intervals), 2)
        self.assertSetEqual(
            set(intervals[0].keys()),
            {'locusListGuid', 'locusListIntervalGuid', 'genomeVersion', 'chrom', 'start', 'end'}
        )

        self.assertSetEqual(set(next(iter(response_json['variantTagsByGuid'].values())).keys()), TAG_FIELDS)
        if response_json['variantNotesByGuid']:
            self.assertSetEqual(set(next(iter(response_json['variantNotesByGuid'].values())).keys()), VARIANT_NOTE_FIELDS)
        if response_json['variantFunctionalDataByGuid']:
            self.assertSetEqual(set(next(iter(response_json['variantFunctionalDataByGuid'].values())).keys()), FUNCTIONAL_FIELDS)


    @mock.patch('seqr.views.utils.orm_to_json_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP')
    @mock.patch('seqr.utils.middleware.logger.error')
    @mock.patch('seqr.views.apis.variant_search_api.get_es_variant_gene_counts')
    @mock.patch('seqr.views.apis.variant_search_api.get_es_variants')
    def test_query_variants(self, mock_get_variants, mock_get_gene_counts, mock_error_logger, mock_analyst_group):
        url = reverse(query_variants_handler, args=['abc'])
        self.check_collaborator_login(url, request_data={'projectFamilies': PROJECT_FAMILIES})
        url = reverse(query_variants_handler, args=[SEARCH_HASH])

        # Test invalid inputs
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search hash: {}'.format(SEARCH_HASH))
        mock_error_logger.assert_not_called()

        response = self.client.post(url, content_type='application/json', data=json.dumps({'search': SEARCH}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search: no projects/ families specified')
        mock_error_logger.assert_not_called()

        mock_get_variants.side_effect = InvalidIndexException('Invalid index')
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Invalid index')
        mock_error_logger.assert_called_with(
            'Invalid index', self.collaborator_user, http_request_json=mock.ANY, traceback=mock.ANY, request_body=mock.ANY, detail=None)

        mock_get_variants.side_effect = InvalidSearchException('Invalid search')
        mock_error_logger.reset_mock()
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Invalid search')
        mock_error_logger.assert_not_called()

        mock_get_variants.side_effect = ConnectionTimeout('', '', ValueError('Timeout'))
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json()['error'], 'ConnectionTimeout caused by - ValueError(Timeout)')
        mock_error_logger.assert_not_called()

        mock_get_variants.side_effect = TransportError('N/A', 'search_phase_execution_exception', {'error': 'Invalid'})
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], "TransportError: N/A - 'search_phase_execution_exception' - 'Invalid'")
        self.assertEqual(response.json()['detail'], {'error': 'Invalid'})
        mock_error_logger.assert_not_called()

        error_info_json = {'error': {'root_cause': [{'type': 'response_handler_failure_transport_exception'}]}}
        mock_get_variants.side_effect = TransportError('401', 'search_phase_execution_exception', error_info_json)
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()['error'],
            "TransportError: 401 - 'search_phase_execution_exception' - response_handler_failure_transport_exception")
        self.assertEqual(response.json()['detail'], error_info_json)
        mock_error_logger.assert_not_called()

        mock_get_variants.side_effect = _get_es_variants

        # Test new search
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), set(EXPECTED_SEARCH_RESPONSE.keys()))
        self.assertDictEqual(response_json, EXPECTED_SEARCH_RESPONSE)
        self.assertSetEqual(
            set(response_json['search']['projectFamilies'][0]['familyGuids']), {'F000001_1', 'F000002_2'})
        self._assert_expected_results_context(response_json)

        results_model = VariantSearchResults.objects.get(search_hash=SEARCH_HASH)
        mock_get_variants.assert_called_with(results_model, sort='xpos', page=1, num_results=100, skip_genotype_filter=False, user=self.collaborator_user)
        mock_error_logger.assert_not_called()

        # include project context info
        response = self.client.get('{}?loadProjectTagTypes=true'.format(url))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        expected_search_response = {'projectsByGuid': EXPECTED_SEARCH_CONTEXT_RESPONSE['projectsByGuid']}
        expected_search_response.update(EXPECTED_SEARCH_RESPONSE)
        self.assertSetEqual(set(response_json.keys()), set(expected_search_response.keys()))
        self.assertDictEqual(response_json, expected_search_response)
        self._assert_expected_results_context(response_json)
        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID].keys()), PROJECT_TAG_TYPE_FIELDS)

        # include family context info
        response = self.client.get('{}?loadFamilyContext=true'.format(url))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), set(EXPECTED_SEARCH_FAMILY_CONTEXT_RESPONSE.keys()))
        self.assertDictEqual(response_json, EXPECTED_SEARCH_FAMILY_CONTEXT_RESPONSE)
        self._assert_expected_results_family_context(response_json)

        # Test pagination
        response = self.client.get('{}?page=3'.format(url))
        self.assertEqual(response.status_code, 200)
        mock_get_variants.assert_called_with(results_model, sort='xpos', page=3, num_results=100, skip_genotype_filter=False, user=self.collaborator_user)
        mock_error_logger.assert_not_called()

        # Test sort
        response = self.client.get('{}?sort=pathogenicity'.format(url))
        self.assertEqual(response.status_code, 200)
        mock_get_variants.assert_called_with(results_model, sort='pathogenicity', page=1, num_results=100, skip_genotype_filter=False, user=self.collaborator_user)
        mock_error_logger.assert_not_called()

        # Test export
        export_url = reverse(export_variants_handler, args=[SEARCH_HASH])
        response = self.client.get(export_url)
        self.assertEqual(response.status_code, 200)
        expected_content = [
            ['chrom', 'pos', 'ref', 'alt', 'gene', 'worst_consequence', '1kg_freq', 'exac_freq', 'gnomad_genomes_freq',
             'gnomad_exomes_freq', 'topmed_freq', 'cadd', 'revel', 'eigen', 'splice_ai', 'polyphen', 'sift', 'muttaster', 'fathmm',
             'rsid', 'hgvsc', 'hgvsp', 'clinvar_clinical_significance', 'clinvar_gold_stars', 'filter', 'family_id_1',
             'tags_1', 'notes_1', 'family_id_2', 'tags_2', 'notes_2', 'sample_1', 'num_alt_alleles_1', 'gq_1', 'ab_1',
             'sample_2', 'num_alt_alleles_2', 'gq_2', 'ab_2'],
            ['21', '3343400', 'GAGA', 'G', 'WASH7P', 'missense_variant', '', '', '', '', '', '', '', '', '', '', '', '',
             '', '', 'ENST00000623083.3:c.1075G>A', 'ENSP00000485442.1:p.Gly359Ser', '', '', '', '1',
             'Tier 1 - Novel gene and phenotype (None)|Review (None)', '', '2', '', '', 'NA19675', '1', '46.0',
             '0.702127659574', 'NA19679', '0', '99.0', '0.0'],
            ['3', '835', 'AAAG', 'A', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
             '1', '', '', '', '', '', 'NA19679', '0', '99.0', '0.0', '', '', '', ''],
            ['12', '48367227', 'TC', 'T', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
             '', '2', 'Known gene for phenotype (None)|Excluded (None)', 'test n\xf8te (None)', '', '', '', '', '', '',
             '', '', '', '', '']]
        self.assertEqual(response.content, ('\n'.join(['\t'.join(line) for line in expected_content])+'\n').encode('utf-8'))

        # test export with max families
        with mock.patch('seqr.views.apis.variant_search_api.MAX_FAMILIES_PER_ROW', 1):
            response = self.client.get(export_url)
            self.assertEqual(response.status_code, 200)
            expected_content = [
                ['chrom', 'pos', 'ref', 'alt', 'gene', 'worst_consequence', '1kg_freq', 'exac_freq', 'gnomad_genomes_freq',
                 'gnomad_exomes_freq', 'topmed_freq', 'cadd', 'revel', 'eigen', 'splice_ai', 'polyphen', 'sift', 'muttaster', 'fathmm',
                 'rsid', 'hgvsc', 'hgvsp', 'clinvar_clinical_significance', 'clinvar_gold_stars', 'filter', 'family_id_1',
                 'tags_1', 'notes_1', 'sample_1', 'num_alt_alleles_1', 'gq_1', 'ab_1',],
                ['21', '3343400', 'GAGA', 'G', 'WASH7P', 'missense_variant', '', '', '', '', '', '', '', '', '', '', '', '', '',
                 '', 'ENST00000623083.3:c.1075G>A', 'ENSP00000485442.1:p.Gly359Ser', '', '', '', '1',
                 'Tier 1 - Novel gene and phenotype (None)|Review (None)', '', 'NA19675', '1', '46.0', '0.702127659574',],
                ['21', '3343400', 'GAGA', 'G', 'WASH7P', 'missense_variant', '', '', '', '', '', '', '', '', '', '', '', '', '',
                 '', 'ENST00000623083.3:c.1075G>A', 'ENSP00000485442.1:p.Gly359Ser', '', '', '', '2', '', '',
                 'NA19679', '0', '99.0', '0.0'],
                ['3', '835', 'AAAG', 'A', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
                 '1', '', '', 'NA19679', '0', '99.0', '0.0',],
                ['12', '48367227', 'TC', 'T', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
                 '', '2', 'Known gene for phenotype (None)|Excluded (None)', 'test n\xf8te (None)', '', '', '', '',]]
            self.assertEqual(response.content,
                             ('\n'.join(['\t'.join(line) for line in expected_content]) + '\n').encode('utf-8'))

        mock_get_variants.assert_called_with(results_model, page=1, load_all=True, user=self.collaborator_user)
        mock_error_logger.assert_not_called()

        # Test gene breakdown
        gene_counts = {
            'ENSG00000227232': {'total': 2, 'families': {'F000001_1': 2, 'F000002_2': 1}},
            'ENSG00000268903': {'total': 1, 'families': {'F000002_2': 1}}
        }
        mock_get_gene_counts.return_value = gene_counts

        gene_breakdown_url = reverse(get_variant_gene_breakdown, args=[SEARCH_HASH])
        response = self.client.get(gene_breakdown_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'searchGeneBreakdown', 'genesById'})
        self.assertDictEqual(response_json['searchGeneBreakdown'], {SEARCH_HASH: gene_counts})
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000227232', 'ENSG00000268903'})
        self.assertSetEqual(set(response_json['genesById']['ENSG00000227232'].keys()), GENE_VARIANT_DISPLAY_FIELDS)

        # Test compound hets
        mock_get_variants.side_effect = _get_compound_het_es_variants
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), set(EXPECTED_SEARCH_RESPONSE.keys()))
        expected_search_response = deepcopy(EXPECTED_SEARCH_RESPONSE)
        expected_search_response.update({
            'searchedVariants': COMP_HET_VARAINTS,
            'savedVariantsByGuid': {'SV0000002_1248367227_r0390_100': mock.ANY},
            'genesById': {'ENSG00000233653': mock.ANY},
            'variantTagsByGuid': {
                'VT1726970_2103343353_r0004_tes': mock.ANY, 'VT1726945_2103343353_r0390_100': mock.ANY,
            },
            'variantFunctionalDataByGuid': {},
            'rnaSeqData': {},
        })
        expected_search_response['search']['totalResults'] = 1
        self.assertDictEqual(response_json, expected_search_response)
        self._assert_expected_results_context(response_json, has_pa_detail=False)
        mock_error_logger.assert_not_called()

        # Test cross-project discovery for analyst users
        self.login_analyst_user()
        mock_get_variants.side_effect = _get_es_variants
        response = self.client.get('{}?sort=pathogenicity'.format(url))
        self.assertEqual(response.status_code, 403)

        mock_analyst_group.__bool__.return_value = True
        mock_analyst_group.resolve_expression.return_value = 'analysts'
        response = self.client.get('{}?sort=pathogenicity'.format(url))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        expected_search_results = deepcopy(EXPECTED_SEARCH_RESPONSE)
        expected_search_results['searchedVariants'] = VARIANTS_WITH_DISCOVERY_TAGS
        expected_search_results['familiesByGuid'] = {'F000011_11': mock.ANY}
        self.assertSetEqual(set(response_json.keys()), set(expected_search_results.keys()))
        self.assertDictEqual(response_json, expected_search_results)
        self._assert_expected_results_context(response_json)

        mock_get_variants.assert_called_with(results_model, sort='pathogenicity_hgmd', page=1, num_results=100, skip_genotype_filter=False, user=self.analyst_user)
        mock_error_logger.assert_not_called()

        # Test no results
        mock_get_variants.side_effect = _get_empty_es_variants
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json, {
            'searchedVariants': [],
            'search': {
                'search': SEARCH,
                'projectFamilies': PROJECT_FAMILIES,
                'totalResults': 0,
            }
        })
        mock_error_logger.assert_not_called()

    @mock.patch('seqr.views.apis.variant_search_api.get_es_variants')
    def test_query_all_projects_variants(self, mock_get_variants):
        url = reverse(query_variants_handler, args=[SEARCH_HASH])
        self.check_require_login(url)

        expected_searched_families = set()
        def _get_variants(results_model, **kwargs):
            results_model.save()
            self.assertSetEqual(expected_searched_families, {f.guid for f in results_model.families.all()})
            matched_variants = [
                deepcopy(variant) for variant in VARIANTS
                if any(family_guid in expected_searched_families for family_guid in variant['familyGuids'])
            ]
            return matched_variants, len(matched_variants)

        mock_get_variants.side_effect = _get_variants

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'allProjectFamilies': True, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        empty_search_response = {
            'searchedVariants': [], 'search': {
                'search': SEARCH,
                'projectFamilies': [],
                'totalResults': 0,
        }}
        self.assertDictEqual(response_json, empty_search_response)
        results_model = VariantSearchResults.objects.get(search_hash=SEARCH_HASH)
        mock_get_variants.assert_called_with(results_model, sort='xpos', page=1, num_results=100, skip_genotype_filter=True, user=self.no_access_user)

        VariantSearchResults.objects.filter(search_hash=SEARCH_HASH).delete()
        self.login_data_manager_user()
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'allProjectFamilies': True, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), empty_search_response)

        VariantSearchResults.objects.filter(search_hash=SEARCH_HASH).delete()
        self.login_collaborator()
        expected_searched_families = {
            'F000001_1', 'F000002_2', 'F000003_3', 'F000004_4', 'F000005_5', 'F000006_6', 'F000007_7', 'F000008_8',
            'F000009_9', 'F000010_10', 'F000013_13'}
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'allProjectFamilies': True, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), set(EXPECTED_SEARCH_RESPONSE.keys()))
        self.assertDictEqual(response_json, EXPECTED_SEARCH_RESPONSE)
        self._assert_expected_results_context(response_json)
        self.assertSetEqual(
            set(response_json['search']['projectFamilies'][0]['familyGuids']), expected_searched_families)

        result_model = VariantSearchResults.objects.get(search_hash=SEARCH_HASH)
        self.assertSetEqual(expected_searched_families, {f.guid for f in result_model.families.all()})
        mock_get_variants.assert_called_with(result_model, sort='xpos', page=1, num_results=100,
                                             skip_genotype_filter=True, user=self.collaborator_user)

    @mock.patch('seqr.views.apis.variant_search_api.get_es_variants')
    def test_query_all_project_families_variants(self, mock_get_variants):
        url = reverse(query_variants_handler, args=['abc'])
        self.check_collaborator_login(url, request_data={'projectGuids': ['R0003_test']})
        url = reverse(query_variants_handler, args=[SEARCH_HASH])

        mock_get_variants.side_effect = _get_es_variants

        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectGuids': ['R0003_test'], 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json['search'], {
            'search': SEARCH,
            'projectFamilies': [{'projectGuid': 'R0003_test', 'familyGuids': mock.ANY}],
            'totalResults': 3,
        })
        self.assertSetEqual(
            {'F000011_11', 'F000012_12'}, set(response_json['search']['projectFamilies'][0]['familyGuids']))

        mock_get_variants.assert_called_with(
            VariantSearchResults.objects.get(search_hash=SEARCH_HASH), sort='xpos', page=1, num_results=100,
            skip_genotype_filter=False, user=self.collaborator_user)

        # Test export disabled in demo projects
        export_url = reverse(export_variants_handler, args=[SEARCH_HASH])
        response = self.client.get(export_url)
        self.assertEqual(response.status_code, 403)

    def test_search_context(self):
        search_context_url = reverse(search_context_handler)
        self.check_collaborator_login(search_context_url, request_data={'familyGuid': 'F000001_1'})

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'foo': 'bar'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid context params: {"foo": "bar"}')

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'familyGuid': 'bar'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid context params: {"familyGuid": "bar"}')

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'projectGuid': PROJECT_GUID}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'familyGuid': 'F000001_1'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'analysisGroupGuid': 'AG0000183_test_group'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

        # Test fetching multiple projects where a locus list is contained in a non-included project
        LocusList.objects.get(guid=LOCUS_LIST_GUID).projects.add(Project.objects.get(id=2))

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'projectCategoryGuid': 'PC000003_test_category_name'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        expected_response = {
            'savedSearchesByGuid': mock.ANY,
            'projectCategoriesByGuid': {'PC000003_test_category_name': mock.ANY},
        }
        expected_response.update(deepcopy(EXPECTED_SEARCH_CONTEXT_RESPONSE))
        expected_response['projectsByGuid']['R0003_test'] = mock.ANY
        self.assertSetEqual(set(response_json), set(expected_response))
        self.assertDictEqual(response_json, expected_response)
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID].keys()), PROJECT_CONTEXT_FIELDS)
        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID]['datasetTypes']), {'VARIANTS', 'SV'})
        self.assertSetEqual(set(response_json['projectsByGuid']['R0003_test']['datasetTypes']), {'VARIANTS'})
        self.assertEqual(len(response_json['familiesByGuid']), 13)

        # Test search hash context
        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': SEARCH_HASH}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search hash: {}'.format(SEARCH_HASH))

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': SEARCH_HASH, 'searchParams': {'search': SEARCH}}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search: no projects/ families specified')

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': SEARCH_HASH, 'searchParams': {'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH}}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': SEARCH_HASH}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)

        # Test all project search context
        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': 'djd29394hfw2njr2hod2', 'searchParams': {'allProjectFamilies': True, 'search': SEARCH}}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self._assert_expected_search_context(response_json)


    @mock.patch('seqr.views.apis.variant_search_api.get_single_es_variant')
    def test_query_single_variant(self, mock_get_variant):
        single_family_variant = deepcopy(VARIANTS[0])
        single_family_variant['familyGuids'] = ['F000001_1']
        mock_get_variant.return_value = single_family_variant

        url = '{}?familyGuid=F000001_1'.format(reverse(query_single_variant_handler, args=['21-3343353-GAGA-G']))
        self.check_collaborator_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        response_keys = {'projectsByGuid'}
        response_keys.update(EXPECTED_SEARCH_FAMILY_CONTEXT_RESPONSE)
        response_keys.remove('search')
        self.assertSetEqual(set(response_json.keys()), response_keys)

        expected_search_response = deepcopy(EXPECTED_SEARCH_FAMILY_CONTEXT_RESPONSE)
        expected_search_response.update({
            k: EXPECTED_SEARCH_CONTEXT_RESPONSE[k] for k in ['projectsByGuid', 'familiesByGuid', 'locusListsByGuid']
        })
        expected_search_response.pop('search')
        expected_search_response['savedVariantsByGuid'].pop('SV0000002_1248367227_r0390_100')
        expected_search_response['variantTagsByGuid'].pop('VT1726945_2103343353_r0390_100')
        expected_search_response['variantTagsByGuid'].pop('VT1726970_2103343353_r0004_tes')
        expected_search_response['variantNotesByGuid'].pop('VN0714935_2103343353_r0390_100')
        expected_search_response['genesById'].pop('ENSG00000233653')
        expected_search_response['searchedVariants'] = [single_family_variant]
        self.assertDictEqual(response_json, expected_search_response)
        self._assert_expected_results_family_context(response_json, locus_list_detail=True)
        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID].keys()), PROJECT_TAG_TYPE_FIELDS)
        self.assertSetEqual(set(response_json['familiesByGuid'].keys()), {'F000001_1'})

        mock_get_variant.assert_called_with(mock.ANY, '21-3343353-GAGA-G', user=self.collaborator_user)
        searched_families = mock_get_variant.call_args.args[0]
        self.assertEqual(searched_families.count(), 1)
        self.assertEqual(searched_families.first().guid, 'F000001_1')

        mock_get_variant.side_effect = InvalidSearchException('Variant not found')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Variant not found')

    def test_saved_search(self):
        get_saved_search_url = reverse(get_saved_search_handler)
        self.check_require_login(get_saved_search_url)

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 3)

        create_saved_search_url = reverse(create_saved_search_handler)

        response = self.client.post(create_saved_search_url, content_type='application/json', data='{}')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, '"Name" is required')

        body = {'name': 'Test Search'}

        invalid_body = {'inheritance': {'filter': {'genotype': {'indiv_1': 'ref_alt'}}}}
        invalid_body.update(body)
        response = self.client.post(create_saved_search_url, content_type='application/json', data=json.dumps(invalid_body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Saved searches cannot include custom genotype filters')

        body.update(SEARCH)
        response = self.client.post(create_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        saved_searches = response.json()['savedSearchesByGuid']
        self.assertEqual(len(saved_searches), 1)
        search_guid = next(iter(saved_searches))
        self.assertDictEqual(saved_searches[search_guid], {
            'savedSearchGuid': search_guid, 'name': 'Test Search', 'search': SEARCH, 'createdById': 13, 'order': None,
        })

        # Test no errors if duplicate searches get created
        dup_search_guid = VariantSearch.objects.create(search=SEARCH, created_by=self.no_access_user).guid
        response = self.client.post(create_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(list(response.json()['savedSearchesByGuid'].keys()), [search_guid])
        self.assertIsNone(VariantSearch.objects.filter(guid=dup_search_guid).first())

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 4)

        # Test cannot save different searches with the same name
        body['filters'] = {'test': 'filter'}
        with transaction.atomic():
            response = self.client.post(create_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Saved search with name "Test Search" already exists')

        # Test update endpoint
        update_saved_search_url = reverse(update_saved_search_handler, args=[search_guid])
        body['name'] = None
        response = self.client.post(update_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, '"Name" is required')

        body['name'] = 'Updated Test Search'
        response = self.client.post(update_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json()['savedSearchesByGuid'][search_guid], {
            'savedSearchGuid': search_guid, 'name': 'Updated Test Search', 'search': SEARCH, 'createdById': 13, 'order': None,
        })

        delete_saved_search_url = reverse(delete_saved_search_handler, args=[search_guid])
        response = self.client.get(delete_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'savedSearchesByGuid': {search_guid: None}})

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 3)

        global_saved_search_guid = next(iter(response.json()['savedSearchesByGuid']))

        update_saved_search_url = reverse(update_saved_search_handler, args=[global_saved_search_guid])
        response = self.client.post(update_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 403)

        delete_saved_search_url = reverse(delete_saved_search_handler, args=[global_saved_search_guid])
        response = self.client.get(delete_saved_search_url)
        self.assertEqual(response.status_code, 403)


# Tests for AnVIL access disabled
class LocalVariantSearchAPITest(AuthenticationTestCase, VariantSearchAPITest):
    fixtures = ['users', '1kg_project', 'reference_data', 'variant_searches']


def assert_no_list_ws_has_al(self, acl_call_count, workspace_name=None):
    self.mock_list_workspaces.assert_not_called()
    assert_ws_has_al(self, acl_call_count, workspace_name)

def assert_ws_has_al(self, acl_call_count, workspace_name=None):
    if not workspace_name:
        workspace_name = 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de'
    self.mock_get_ws_access_level.assert_called_with(mock.ANY, 'my-seqr-billing', workspace_name)
    self.assertEqual(self.mock_get_ws_access_level.call_count, acl_call_count)
    self.mock_get_ws_acl.assert_not_called()


# Test for permissions from AnVIL only
class AnvilVariantSearchAPITest(AnvilAuthenticationTestCase, VariantSearchAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data', 'variant_searches']

    def test_query_variants(self, *args):
        super(AnvilVariantSearchAPITest, self).test_query_variants(*args)
        assert_no_list_ws_has_al(self, 17)

    def test_query_all_projects_variants(self, *args):
        super(AnvilVariantSearchAPITest, self).test_query_all_projects_variants(*args)
        calls = [
            mock.call(self.no_access_user),
            mock.call(self.collaborator_user),
        ]
        self.mock_list_workspaces.assert_has_calls(calls)
        self.mock_get_ws_access_level.assert_has_calls([
            mock.call(self.collaborator_user, 'my-seqr-billing', 'anvil-1kg project n\u00e5me with uni\u00e7\u00f8de'),
        ])
        self.assertEqual(self.mock_get_ws_access_level.call_count, 1)
        self.mock_get_ws_acl.assert_not_called()

    def test_query_all_project_families_variants(self, *args):
        super(AnvilVariantSearchAPITest, self).test_query_all_project_families_variants(*args)
        assert_no_list_ws_has_al(self, 3, workspace_name='anvil-project 1000 Genomes Demo')

    def test_search_context(self):
        super(AnvilVariantSearchAPITest, self).test_search_context()
        self.mock_list_workspaces.assert_called_with(self.collaborator_user)
        assert_ws_has_al(self, 17)

    def test_query_single_variant(self, *args):
        super(AnvilVariantSearchAPITest, self).test_query_single_variant(*args)
        assert_no_list_ws_has_al(self, 4)

    def test_saved_search(self):
        super(AnvilVariantSearchAPITest, self).test_saved_search()
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()


# Test for permissions from AnVIL and local
class MixSavedVariantSearchAPITest(MixAuthenticationTestCase, VariantSearchAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data', 'variant_searches']

    def test_query_variants(self, *args):
        super(MixSavedVariantSearchAPITest, self).test_query_variants(*args)
        assert_no_list_ws_has_al(self, 3)

    def test_query_all_projects_variants(self, *args):
        super(MixSavedVariantSearchAPITest, self).test_query_all_projects_variants(*args)
        calls = [
            mock.call(self.no_access_user),
            mock.call(self.collaborator_user),
        ]
        self.mock_list_workspaces.assert_has_calls(calls)
        self.mock_get_ws_acl.assert_not_called()

    def test_query_all_project_families_variants(self, *args):
        super(MixSavedVariantSearchAPITest, self).test_query_all_project_families_variants(*args)
        assert_no_list_ws_has_al(self, 1, workspace_name='anvil-project 1000 Genomes Demo')

    def test_search_context(self):
        super(MixSavedVariantSearchAPITest, self).test_search_context()
        self.mock_list_workspaces.assert_called_with(self.collaborator_user)
        assert_ws_has_al(self, 9)

    def test_query_single_variant(self, *args):
        super(MixSavedVariantSearchAPITest, self).test_query_single_variant(*args)
        assert_no_list_ws_has_al(self, 2)

    def test_saved_search(self):
        super(MixSavedVariantSearchAPITest, self).test_saved_search()
        self.mock_list_workspaces.assert_not_called()
        self.mock_get_ws_acl.assert_not_called()
