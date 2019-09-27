import json
import mock
from copy import deepcopy

from django.test import TestCase
from django.urls.base import reverse

from seqr.models import VariantSearchResults
from seqr.utils.es_utils import InvalidIndexException
from seqr.views.apis.locus_list_api import add_project_locus_lists
from seqr.views.apis.variant_search_api import query_variants_handler, query_single_variant_handler, \
    export_variants_handler, search_context_handler, get_saved_search_handler, create_saved_search_handler, \
    update_saved_search_handler, delete_saved_search_handler, get_variant_gene_breakdown
from seqr.views.utils.test_utils import _check_login


LOCUS_LIST_GUID = 'LL00049_pid_genes_autosomal_do'
PROJECT_GUID = 'R0001_1kg'
SEARCH_HASH = 'd380ed0fd28c3127d07a64ea2ba907d7'
SEARCH = {'filters': {}, 'inheritance': None}
PROJECT_FAMILIES = [{'projectGuid': PROJECT_GUID, 'familyGuids': ['F000001_1', 'F000002_2']}]
VARIANTS = [
    {'alt': 'G', 'ref': 'GAGA', 'chrom': '21', 'pos': 3343400, 'xpos': 2103343400, 'genomeVersion': '38',
     'liftedOverChrom': '21', 'liftedOverPos': 3343353, 'liftedOverGenomeVersion': '37', 'variantId': '21-3343400-GAGA-G',
     'mainTranscriptId': 'ENST00000623083', 'transcripts': {'ENSG00000227232': [{'aminoAcids': 'G/S', 'geneSymbol': 'WASH7P',
     'biotype': 'protein_coding', 'category': 'missense', 'cdnaEnd': 1075, 'cdnaStart': 1075, 'codons': 'Ggt/Agt',
     'consequenceTerms': ['missense_variant'], 'hgvs': 'ENSP00000485442.1:p.Gly359Ser', 'hgvsc': 'ENST00000623083.3:c.1075G>A',
     'hgvsp': 'ENSP00000485442.1:p.Gly359Ser', 'majorConsequence': 'missense_variant', 'majorConsequenceRank': 11,
     'proteinId': 'ENSP00000485442', 'transcriptId': 'ENST00000623083', 'transcriptRank': 0}], 'ENSG00000268903': [{
     'aminoAcids': 'G/S', 'biotype': 'protein_coding', 'category': 'missense', 'cdnaEnd': 1338, 'cdnaStart': 1338,
     'codons': 'Ggt/Agt', 'consequenceTerms': ['missense_variant'], 'geneId': 'ENSG00000268903', 'hgvs': 'ENSP00000485351.1:p.Gly368Ser',
     'hgvsc': 'ENST00000624735.1:c.1102G>A', 'hgvsp': 'ENSP00000485351.1:p.Gly368Ser', 'majorConsequence': 'missense_variant',
     'majorConsequenceRank': 11, 'proteinId': 'ENSP00000485351', 'transcriptId': 'ENST00000624735', 'transcriptRank': 1}]
     }, 'familyGuids': ['F000001_1', 'F000002_2'],
     'genotypes': {'NA19675': {'sampleId': 'NA19675', 'ab': 0.7021276595744681, 'gq': 46.0, 'numAlt': 1, 'dp': '50', 'ad': '14,33'},
                   'NA19679': {'sampleId': 'NA19679', 'ab': 0.0, 'gq': 99.0, 'numAlt': 0, 'dp': '45', 'ad': '45,0'}}},
    {'alt': 'A', 'ref': 'AAAG', 'chrom': '3', 'pos': 835, 'xpos': 3000000835, 'genomeVersion': '37', 'liftedOverGenomeVersion': '', 'variantId': '3-835-AAAG-A', 'transcripts': {}, 'familyGuids': ['F000001_1'], 'genotypes': {'NA19679': {'sampleId': 'NA19679', 'ab': 0.0, 'gq': 99.0, 'numAlt': 0, 'dp': '45', 'ad': '45,0'}}},
    {'alt': 'T', 'ref': 'TC', 'chrom': '12', 'pos': 48367227, 'xpos': 1248367227, 'genomeVersion': '37', 'liftedOverGenomeVersion': '', 'variantId': '12-48367227-TC-T', 'transcripts': {'ENSG00000233653': {}}, 'familyGuids': ['F000002_2'], 'genotypes': {}},
]
EXPECTED_VARIANTS = deepcopy(VARIANTS)
EXPECTED_VARIANTS[0]['locusListGuids'] = []
EXPECTED_VARIANTS[1]['locusListGuids'] = [LOCUS_LIST_GUID]
EXPECTED_VARIANTS[2]['locusListGuids'] = []


def _get_es_variants(results_model, **kwargs):
    results_model.save()
    return deepcopy(VARIANTS), len(VARIANTS)

def _get_empty_es_variants(results_model, **kwargs):
    results_model.save()
    return [], 0


class VariantSearchAPITest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data', 'variant_searches']

    @mock.patch('seqr.views.apis.variant_search_api.get_es_variant_gene_counts')
    @mock.patch('seqr.views.apis.variant_search_api.get_es_variants')
    def test_query_variants(self, mock_get_variants, mock_get_gene_counts):
        url = reverse(query_variants_handler, args=[SEARCH_HASH])
        _check_login(self, url)

        # add a locus list
        response = self.client.post(
            reverse(add_project_locus_lists, args=[PROJECT_GUID]), content_type='application/json',
            data=json.dumps({'locusListGuids': [LOCUS_LIST_GUID]}))
        self.assertEqual(response.status_code, 200)

        # Test invalid inputs
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search hash: {}'.format(SEARCH_HASH))

        response = self.client.post(url, content_type='application/json', data=json.dumps({'search': SEARCH}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid search: no projects/ families specified')

        mock_get_variants.side_effect = InvalidIndexException('Invalid index')
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid index')

        mock_get_variants.side_effect = _get_es_variants

        # Test new search
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'searchedVariants', 'savedVariantsByGuid', 'genesById', 'search'})

        self.assertListEqual(response_json['searchedVariants'], EXPECTED_VARIANTS)
        self.assertDictEqual(response_json['search'], {
            'search': SEARCH,
            'projectFamilies': PROJECT_FAMILIES,
            'totalResults': 3,
        })
        self.assertSetEqual(
            set(response_json['savedVariantsByGuid'].keys()),
            {'SV0000001_2103343353_r0390_100', 'SV0000002_1248367227_r0390_100'}
        )
        self.assertSetEqual(
            set(response_json['genesById'].keys()),
            {'ENSG00000227232', 'ENSG00000268903', 'ENSG00000233653'}
        )
        self.assertListEqual(
            response_json['genesById']['ENSG00000227232']['locusListGuids'], [LOCUS_LIST_GUID]
        )

        results_model = VariantSearchResults.objects.get(search_hash=SEARCH_HASH)
        mock_get_variants.assert_called_with(results_model, sort='xpos', page=1, num_results=100)

        # Test pagination
        response = self.client.get('{}?page=3'.format(url))
        self.assertEqual(response.status_code, 200)
        mock_get_variants.assert_called_with(results_model, sort='xpos', page=3, num_results=100)

        # Test sort
        response = self.client.get('{}?sort=consequence'.format(url))
        self.assertEqual(response.status_code, 200)
        mock_get_variants.assert_called_with(results_model, sort='consequence', page=1, num_results=100)

        # Test export
        export_url = reverse(export_variants_handler, args=[SEARCH_HASH])
        response = self.client.get(export_url)
        self.assertEqual(response.status_code, 200)
        export_content = [row.split('\t') for row in response.content.rstrip('\n').split('\n')]
        self.assertEqual(len(export_content), 4)
        self.assertListEqual(
            export_content[0],
            ['chrom', 'pos', 'ref', 'alt', 'gene', 'worst_consequence', '1kg_freq', 'exac_freq', 'gnomad_genomes_freq',
            'gnomad_exomes_freq', 'topmed_freq', 'cadd', 'revel', 'eigen', 'polyphen', 'sift', 'muttaster', 'fathmm',
             'rsid', 'hgvsc', 'hgvsp', 'clinvar_clinical_significance', 'clinvar_gold_stars', 'filter', 'family_id_1',
             'tags_1', 'notes_1', 'family_id_2', 'tags_2', 'notes_2', 'sample_1:num_alt_alleles:gq:ab', 'sample_2:num_alt_alleles:gq:ab'])
        self.assertListEqual(
            export_content[1],
            ['21', '3343400', 'GAGA', 'G', 'WASH7P', 'missense_variant', '', '', '', '', '', '', '', '', '', '', '', '',
             '', 'ENST00000623083.3:c.1075G>A', 'ENSP00000485442.1:p.Gly359Ser', '', '', '', '1',
             'Tier 1 - Novel gene and phenotype (None)|Review (None)', '', '2', '', '', 'NA19675:1:46.0:0.702127659574', 'NA19679:0:99.0:0.0'])

        mock_get_variants.assert_called_with(results_model, page=1, load_all=True)

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

        # Test no results
        mock_get_variants.side_effect = _get_empty_es_variants
        response = self.client.post(url, content_type='application/json', data=json.dumps({
            'projectFamilies': PROJECT_FAMILIES, 'search': SEARCH
        }))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertDictEqual(response_json, {
            'searchedVariants': [],
            'savedVariantsByGuid': {},
            'genesById': {},
            'search': {
                'search': SEARCH,
                'projectFamilies': PROJECT_FAMILIES,
                'totalResults': 0,
            }
        })

    def test_search_context(self):
        search_context_url = reverse(search_context_handler)
        _check_login(self, search_context_url)

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'foo': 'bar'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid context params: {"foo": "bar"}')

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'projectGuid': PROJECT_GUID}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'locusListsByGuid', 'analysisGroupsByGuid', }
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])
        self.assertTrue('AG0000183_test_group' in response_json['analysisGroupsByGuid'])

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'familyGuid': 'F000001_1'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'locusListsByGuid', 'analysisGroupsByGuid', }
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])
        self.assertTrue('AG0000183_test_group' in response_json['analysisGroupsByGuid'])

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'analysisGroupGuid': 'AG0000183_test_group'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'locusListsByGuid', 'analysisGroupsByGuid', }
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])
        self.assertTrue('AG0000183_test_group' in response_json['analysisGroupsByGuid'])

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps({'projectCategoryGuid': 'PC000003_test_category_name'}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'locusListsByGuid', 'analysisGroupsByGuid', 'projectCategoriesByGuid'}
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])
        self.assertTrue('AG0000183_test_group' in response_json['analysisGroupsByGuid'])
        self.assertListEqual(response_json['projectCategoriesByGuid'].keys(), ['PC000003_test_category_name'])

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
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'locusListsByGuid', 'analysisGroupsByGuid', }
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])

        response = self.client.post(search_context_url, content_type='application/json', data=json.dumps(
            {'searchHash': SEARCH_HASH}))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json),
            {'savedSearchesByGuid', 'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid',
             'locusListsByGuid', 'analysisGroupsByGuid', }
        )
        self.assertEqual(len(response_json['savedSearchesByGuid']), 3)
        self.assertTrue(PROJECT_GUID in response_json['projectsByGuid'])
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])

    @mock.patch('seqr.views.apis.variant_search_api.get_single_es_variant')
    def test_query_single_variant(self, mock_get_variant):
        mock_get_variant.return_value = VARIANTS[0]

        url = reverse(query_single_variant_handler, args=['21-3343353-GAGA-G'])
        _check_login(self, url)

        response = self.client.get('{}?familyGuid=F000001_1'.format(url))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(
            set(response_json.keys()),
            {'searchedVariants', 'savedVariantsByGuid', 'genesById', 'projectsByGuid', 'familiesByGuid',
             'individualsByGuid', 'samplesByGuid', 'locusListsByGuid', 'analysisGroupsByGuid',}
        )

        self.assertListEqual(response_json['searchedVariants'], EXPECTED_VARIANTS[:1])
        self.assertSetEqual(set(response_json['savedVariantsByGuid'].keys()), {'SV0000001_2103343353_r0390_100'})
        self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000227232', 'ENSG00000268903'})
        self.assertTrue('F000001_1' in response_json['familiesByGuid'])

    def test_saved_search(self):
        get_saved_search_url = reverse(get_saved_search_handler)
        _check_login(self, get_saved_search_url)

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
        search_guid = saved_searches.keys()[0]
        self.assertDictEqual(saved_searches[search_guid], {
            'savedSearchGuid': search_guid, 'name': 'Test Search', 'search': SEARCH, 'createdById': 10,
        })

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 4)

        update_saved_search_url = reverse(update_saved_search_handler, args=[search_guid])
        body['name'] = 'Updated Test Search'
        response = self.client.post(update_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json()['savedSearchesByGuid'][search_guid], {
            'savedSearchGuid': search_guid, 'name': 'Updated Test Search', 'search': SEARCH, 'createdById': 10,
        })

        delete_saved_search_url = reverse(delete_saved_search_handler, args=[search_guid])
        response = self.client.get(delete_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'savedSearchesByGuid': {search_guid: None}})

        response = self.client.get(get_saved_search_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['savedSearchesByGuid']), 3)

        global_saved_search_guid = response.json()['savedSearchesByGuid'].keys()[0]

        update_saved_search_url = reverse(update_saved_search_handler, args=[global_saved_search_guid])
        response = self.client.post(update_saved_search_url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 403)

        delete_saved_search_url = reverse(delete_saved_search_handler, args=[global_saved_search_guid])
        response = self.client.get(delete_saved_search_url)
        self.assertEqual(response.status_code, 403)
