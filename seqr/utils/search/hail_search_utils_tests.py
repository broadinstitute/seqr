from copy import deepcopy
from django.test import TestCase
import json
import mock
from requests import HTTPError
import responses

from seqr.models import Family, Project
from seqr.utils.search.utils import get_variant_query_gene_counts, query_variants, get_single_variant, \
    get_variants_for_variant_ids, variant_lookup, sv_variant_lookup, InvalidSearchException
from seqr.utils.search.search_utils_tests import SearchTestHelper
from hail_search.test_utils import get_hail_search_body, EXPECTED_SAMPLE_DATA, FAMILY_1_SAMPLE_DATA, \
    ALL_AFFECTED_SAMPLE_DATA, CUSTOM_AFFECTED_SAMPLE_DATA, HAIL_BACKEND_VARIANTS, \
    LOCATION_SEARCH, EXCLUDE_LOCATION_SEARCH, VARIANT_ID_SEARCH, RSID_SEARCH, GENE_COUNTS, FAMILY_2_VARIANT_SAMPLE_DATA, \
    FAMILY_2_MITO_SAMPLE_DATA, EXPECTED_SAMPLE_DATA_WITH_SEX, VARIANT_LOOKUP_VARIANT, MULTI_PROJECT_SAMPLE_DATA, \
    GCNV_VARIANT4, SV_VARIANT2
MOCK_HOST = 'test-hail-host'
MOCK_ORIGIN = f'http://{MOCK_HOST}'

SV_WGS_SAMPLE_DATA = [{
    'individual_guid': 'I000018_na21234', 'family_guid': 'F000014_14', 'project_guid': 'R0004_non_analyst_project',
    'affected': 'A', 'sample_id': 'NA21234', 'sample_type': 'WGS',
}]

EXPECTED_MITO_SAMPLE_DATA = deepcopy(FAMILY_2_MITO_SAMPLE_DATA)
EXPECTED_MITO_SAMPLE_DATA['MITO'][0].update({'individual_guid': 'I000004_hg00731', 'sample_id': 'HG00731', 'affected': 'A'})

ALL_EXPECTED_SAMPLE_DATA = {**EXPECTED_SAMPLE_DATA, **EXPECTED_MITO_SAMPLE_DATA}


@mock.patch('seqr.utils.search.hail_search_utils.HAIL_BACKEND_SERVICE_HOSTNAME', MOCK_HOST)
class HailSearchUtilsTests(SearchTestHelper, TestCase):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data']

    def setUp(self):
        Project.objects.update(genome_version='37')
        super(HailSearchUtilsTests, self).set_up()
        responses.add(responses.POST, f'{MOCK_ORIGIN}:5000/search', status=200, json={
            'results': HAIL_BACKEND_VARIANTS, 'total': 5,
        })

    def _test_minimal_search_call(self, expected_search_body=None, call_offset=-1, url_path='search', sample_data=ALL_EXPECTED_SAMPLE_DATA, **kwargs):
        expected_search = expected_search_body or get_hail_search_body(genome_version='GRCh37', sample_data=sample_data, **kwargs)

        executed_request = responses.calls[call_offset].request
        self.assertEqual(executed_request.headers.get('From'), 'test_user@broadinstitute.org')
        self.assertEqual(executed_request.url.split('/')[-1], url_path)
        self.assertDictEqual(json.loads(executed_request.body), expected_search)

    def _test_expected_search_call(self, search_fields=None, gene_ids=None, intervals=None, exclude_intervals= None,
                                   rs_ids=None, variant_ids=None, dataset_type=None, secondary_dataset_type=None,
                                   frequencies=None, custom_query=None, inheritance_mode='de_novo', inheritance_filter=None,
                                   quality_filter=None, sort='xpos', sort_metadata=None, **kwargs):

        expected_search = {
            'sort': sort,
            'sort_metadata': sort_metadata,
            'inheritance_mode': inheritance_mode,
            'inheritance_filter': inheritance_filter or {},
            'dataset_type': dataset_type,
            'secondary_dataset_type': secondary_dataset_type,
            'frequencies': frequencies,
            'quality_filter': quality_filter,
            'custom_query': custom_query,
            'intervals': intervals,
            'exclude_intervals': exclude_intervals,
            'gene_ids': gene_ids,
            'variant_ids': variant_ids,
            'rs_ids': rs_ids,
        }
        expected_search.update({field: self.search_model.search[field] for field in search_fields or []})

        self._test_minimal_search_call(**expected_search, **kwargs)

    @mock.patch('seqr.utils.search.hail_search_utils.MAX_FAMILY_COUNTS', {'WES': 2, 'WGS': 1})
    @responses.activate
    def test_query_variants(self):
        variants, total = query_variants(self.results_model, user=self.user)
        self.assertListEqual(variants, HAIL_BACKEND_VARIANTS)
        self.assertEqual(total, 5)
        self.assert_cached_results({'all_results': HAIL_BACKEND_VARIANTS, 'total_results': 5})
        self._test_expected_search_call()

        variants, _ = query_variants(
            self.results_model, user=self.user, sort='cadd', skip_genotype_filter=True, page=2, num_results=1,
        )
        self.assertListEqual(variants, HAIL_BACKEND_VARIANTS[1:])
        self._test_expected_search_call(sort='cadd', num_results=2)

        raw_variant_locus = '1-10439-AC-A,1-91511686-TCA-G'
        self.search_model.search['locus'] = {'rawVariantItems': raw_variant_locus}
        query_variants(self.results_model, user=self.user, sort='in_omim')
        self._test_expected_search_call(
            num_results=2,  dataset_type='SNV_INDEL', sample_data={'SNV_INDEL': EXPECTED_SAMPLE_DATA['SNV_INDEL']},
            sort='in_omim', sort_metadata=['ENSG00000240361', 'ENSG00000135953'],
            **VARIANT_ID_SEARCH,
        )

        self.search_model.search['locus']['rawVariantItems'] = 'rs1801131'
        query_variants(self.results_model, user=self.user, sort='constraint')
        self._test_expected_search_call(
            sort='constraint', sort_metadata={'ENSG00000223972': 2}, **RSID_SEARCH,
        )

        raw_locus = 'CDC7, chr2:1234-5678, chr7:100-10100%10, ENSG00000177000'
        self.search_model.search['locus']['rawItems'] = raw_locus
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(**LOCATION_SEARCH, sample_data=EXPECTED_SAMPLE_DATA)

        self.search_model.search['locus']['excludeLocations'] = True
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(**EXCLUDE_LOCATION_SEARCH)

        self.search_model.search = {
            'inheritance': {'mode': 'recessive', 'filter': {'affected': {
                'I000004_hg00731': 'N', 'I000005_hg00732': 'A', 'I000006_hg00733': 'U',
            }}}, 'annotations': {'frameshift': ['frameshift_variant']},
        }
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            inheritance_mode='recessive', dataset_type='SNV_INDEL', secondary_dataset_type=None,
            search_fields=['annotations'], sample_data=CUSTOM_AFFECTED_SAMPLE_DATA,
        )

        self.search_model.search['inheritance']['filter'] = {}
        self.search_model.search['annotations_secondary'] = self.search_model.search['annotations']
        sv_annotations = {'structural_consequence': ['LOF']}
        self.search_model.search['annotations'] = sv_annotations
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            inheritance_mode='recessive', dataset_type='SV', secondary_dataset_type='SNV_INDEL',
            search_fields=['annotations', 'annotations_secondary'], sample_data=EXPECTED_SAMPLE_DATA,
        )

        self.search_model.search['annotations'] = self.search_model.search['annotations_secondary']
        self.search_model.search['annotations_secondary'] = sv_annotations
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            inheritance_mode='recessive', dataset_type='SNV_INDEL', secondary_dataset_type='SV',
            search_fields=['annotations', 'annotations_secondary']
        )

        self.search_model.search['annotations_secondary'].update({'SCREEN': ['dELS', 'DNase-only']})
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            inheritance_mode='recessive', dataset_type='SNV_INDEL', secondary_dataset_type='ALL',
            search_fields=['annotations', 'annotations_secondary']
        )

        self.search_model.search['annotations_secondary']['structural_consequence'] = []
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            inheritance_mode='recessive', dataset_type='SNV_INDEL', secondary_dataset_type='SNV_INDEL',
            search_fields=['annotations', 'annotations_secondary'], omit_data_type='SV_WES',
        )

        self.search_model.search['inheritance']['mode'] = 'x_linked_recessive'
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            inheritance_mode='x_linked_recessive', dataset_type='SNV_INDEL', secondary_dataset_type='SNV_INDEL',
            search_fields=['annotations', 'annotations_secondary'], sample_data=EXPECTED_SAMPLE_DATA_WITH_SEX,
            omit_data_type='SV_WES',
        )

        self.results_model.families.set(Family.objects.filter(id__in=[2, 11, 14]))
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model, user=self.user)
        self.assertEqual(str(cm.exception), 'Location must be specified to search across multiple projects')

        self.search_model.search = {'inheritance': {'mode': 'de_novo'}, 'annotations': {'structural_consequence': ['LOF']}}
        query_variants(self.results_model, user=self.user)
        sv_sample_data = {
            'SV_WES': FAMILY_2_VARIANT_SAMPLE_DATA['SNV_INDEL'],
            'SV_WGS': SV_WGS_SAMPLE_DATA,
        }
        self._test_expected_search_call(search_fields=['annotations'], dataset_type='SV', sample_data=sv_sample_data)

        del self.search_model.search['annotations']
        self.search_model.search['locus'] = {'rawVariantItems': raw_variant_locus}
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(**VARIANT_ID_SEARCH, num_results=2,  dataset_type='SNV_INDEL', sample_data=MULTI_PROJECT_SAMPLE_DATA)

        self.search_model.search['locus'] = {'rawItems': 'M:10-100 '}
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(intervals=[['M', 10, 100]], sample_data=EXPECTED_MITO_SAMPLE_DATA)

        self.search_model.search['locus']['rawItems'] += raw_locus
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            gene_ids=LOCATION_SEARCH['gene_ids'],
            intervals=[['M', 10, 100]] + LOCATION_SEARCH['intervals'],
            sample_data={**MULTI_PROJECT_SAMPLE_DATA, **sv_sample_data, **EXPECTED_MITO_SAMPLE_DATA},
        )

        self.search_model.search['locus']['rawItems'] = raw_locus
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(**LOCATION_SEARCH, sample_data={**MULTI_PROJECT_SAMPLE_DATA, **sv_sample_data})

        self.results_model.families.set(Family.objects.filter(project_id=1))
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(**LOCATION_SEARCH, sample_data={
            'SNV_INDEL': FAMILY_1_SAMPLE_DATA['SNV_INDEL'] + EXPECTED_SAMPLE_DATA['SNV_INDEL'],
            'SV_WES': sv_sample_data['SV_WES'],
        })

        del self.search_model.search['locus']
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model, user=self.user)
        self.assertEqual(str(cm.exception), 'Location must be specified to search across multiple families in large projects')

        quality_filter = {'min_ab': 10, 'min_gq': 15, 'vcf_filter': 'pass'}
        freq_filter = {'callset': {'af': 0.1}, 'gnomad_genomes': {'af': 0.01, 'ac': 3, 'hh': 3}}
        custom_query = {'term': {'customFlag': 'flagVal'}}
        genotype_filter = {'genotype': {'I000001_na19675': 'ref_alt'}}
        self.search_model.search = deepcopy({
            'inheritance': {'mode': 'any_affected', 'filter': genotype_filter},
            'freqs': freq_filter,
            'qualityFilter': quality_filter,
            'in_silico': {'cadd': '11.5', 'sift': 'D'},
            'customQuery': custom_query,
        })
        self.results_model.families.set(Family.objects.filter(guid='F000001_1'))
        query_variants(self.results_model, user=self.user, sort='prioritized_gene')
        expected_freq_filter = {'seqr': freq_filter['callset'], 'gnomad_genomes': freq_filter['gnomad_genomes']}
        self._test_expected_search_call(
            inheritance_mode=None, inheritance_filter=genotype_filter, sample_data=FAMILY_1_SAMPLE_DATA,
            search_fields=['in_silico'], frequencies=expected_freq_filter, quality_filter=quality_filter, custom_query=custom_query,
            sort='prioritized_gene', sort_metadata={'ENSG00000268903': 1, 'ENSG00000268904': 11},
        )

        responses.add(responses.POST, f'{MOCK_ORIGIN}:5000/search', status=400, body='Bad Search Error')
        with self.assertRaises(HTTPError) as cm:
            query_variants(self.results_model, user=self.user)
        self.assertEqual(cm.exception.response.status_code, 400)
        self.assertEqual(str(cm.exception), 'Bad Search Error')

    @responses.activate
    def test_get_variant_query_gene_counts(self):
        responses.add(responses.POST, f'{MOCK_ORIGIN}:5000/gene_counts', json=GENE_COUNTS, status=200)

        gene_counts = get_variant_query_gene_counts(self.results_model, self.user)
        self.assertDictEqual(gene_counts, GENE_COUNTS)
        self.assert_cached_results({'gene_aggs': gene_counts})
        self._test_expected_search_call(url_path='gene_counts', sort=None)

    @responses.activate
    def test_variant_lookup(self):
        responses.add(responses.POST, f'{MOCK_ORIGIN}:5000/lookup', status=200, json=VARIANT_LOOKUP_VARIANT)
        variant = variant_lookup(self.user, ('1', 10439, 'AC', 'A'), genome_version='37', foo='bar')
        self.assertDictEqual(variant, VARIANT_LOOKUP_VARIANT)
        self._test_minimal_search_call(url_path='lookup', expected_search_body={
            'variant_id': ['1', 10439, 'AC', 'A'], 'genome_version': 'GRCh37', 'foo': 'bar', 'data_type': 'SNV_INDEL',
        })

        responses.add(responses.POST, f'{MOCK_ORIGIN}:5000/lookup', status=404)
        with self.assertRaises(HTTPError) as cm:
            variant_lookup(self.user, ('1', 10439, 'AC', 'A'))
        self.assertEqual(cm.exception.response.status_code, 404)
        self.assertEqual(str(cm.exception), 'Variant not present in seqr')
        self._test_minimal_search_call(url_path='lookup', expected_search_body={
            'variant_id': ['1', 10439, 'AC', 'A'], 'genome_version': 'GRCh38', 'data_type': 'SNV_INDEL',
        })

        # Test mitochondrial variant lookup
        responses.add(responses.POST, f'{MOCK_ORIGIN}:5000/lookup', status=400)
        with self.assertRaises(InvalidSearchException) as cm:
            variant_lookup(self.user, ('M', 11018, 'G', 'T'), genome_version='37')
        self.assertEqual(str(cm.exception), 'MITO variants are not available for GRCh37')

    @responses.activate
    def test_sv_variant_lookup(self):
        sv_families = Family.objects.filter(id__in=[2, 14])
        with self.assertRaises(InvalidSearchException) as cm:
            sv_variant_lookup(self.user, 'suffix_140608_DUP', sv_families)
        self.assertEqual(str(cm.exception), 'Sample type must be specified to look up a structural variant')

        responses.add(responses.POST, f'{MOCK_ORIGIN}:5000/lookup', status=200, json=GCNV_VARIANT4)
        variants = sv_variant_lookup(self.user, 'suffix_140608_DUP', sv_families, sample_type='WES')
        self.assertListEqual(variants, [GCNV_VARIANT4] + HAIL_BACKEND_VARIANTS)
        self._test_minimal_search_call(url_path='lookup', call_offset=-2, expected_search_body={
            'variant_id': 'suffix_140608_DUP', 'genome_version': 'GRCh38', 'data_type': 'SV_WES',
            'sample_data': ALL_AFFECTED_SAMPLE_DATA['SV_WES']
        })
        self._test_minimal_search_call(expected_search_body={
            'genome_version': 'GRCh38', 'data_type': 'SV_WES', 'annotations': {'structural': ['DEL', 'gCNV_DEL']},
            'padded_interval': {'chrom': '17', 'start': 38721781, 'end': 38735703, 'padding': 0.2},
            'sample_data': {'SV_WGS': SV_WGS_SAMPLE_DATA},
        })

        # No second lookup call is made for non DELs/DUPs
        responses.add(responses.POST, f'{MOCK_ORIGIN}:5000/lookup', status=200, json=SV_VARIANT2)
        variants = sv_variant_lookup(self.user, 'cohort_2911.chr1.final_cleanup_INS_chr1_160', sv_families, sample_type='WGS')
        self._test_minimal_search_call(url_path='lookup', expected_search_body={
            'variant_id': 'cohort_2911.chr1.final_cleanup_INS_chr1_160', 'genome_version': 'GRCh38', 'data_type': 'SV_WGS',
            'sample_data': SV_WGS_SAMPLE_DATA
        })
        self.assertListEqual(variants, [SV_VARIANT2])

        responses.add(responses.POST, f'{MOCK_ORIGIN}:5000/lookup', status=404)
        with self.assertRaises(HTTPError) as cm:
            sv_variant_lookup(self.user, 'suffix_140608_DUP', sv_families, sample_type='WES')
        self.assertEqual(cm.exception.response.status_code, 404)
        self.assertEqual(str(cm.exception), 'Variant not present in seqr')

    @responses.activate
    def test_get_single_variant(self):
        variant = get_single_variant(self.families, '2-103343353-GAGA-G', user=self.user)
        self.assertDictEqual(variant, HAIL_BACKEND_VARIANTS[0])
        self._test_minimal_search_call(
            variant_ids=[['2', 103343353, 'GAGA', 'G']], variant_keys=[],
            num_results=1, sample_data={'SNV_INDEL': ALL_AFFECTED_SAMPLE_DATA['SNV_INDEL']})

        get_single_variant(self.families, 'prefix_19107_DEL', user=self.user)
        self._test_minimal_search_call(
            variant_ids=[], variant_keys=['prefix_19107_DEL'],
            num_results=1, sample_data=EXPECTED_SAMPLE_DATA, omit_data_type='SNV_INDEL')

        get_single_variant(self.families, 'M-10195-C-A', user=self.user)
        self._test_minimal_search_call(
            variant_ids=[['M', 10195, 'C', 'A']], variant_keys=[],
            num_results=1, sample_data=EXPECTED_MITO_SAMPLE_DATA)

        with self.assertRaises(InvalidSearchException) as cm:
            get_single_variant(self.families, '1-91502721-G-A', user=self.user, return_all_queried_families=True)
        self.assertEqual(
            str(cm.exception),
            'Unable to return all families for the following variants: 1-38724419-T-G (F000003_3; F000005_5), 1-91502721-G-A (F000005_5)',
        )

        get_single_variant(self.families.filter(guid='F000002_2'), '2-103343353-GAGA-G', user=self.user, return_all_queried_families=True)
        self._test_minimal_search_call(
            variant_ids=[['2', 103343353, 'GAGA', 'G']], variant_keys=[],
            num_results=1, sample_data=FAMILY_2_VARIANT_SAMPLE_DATA)

        responses.add(responses.POST, f'{MOCK_ORIGIN}:5000/search', status=200, json={'results': [], 'total': 0})
        with self.assertRaises(InvalidSearchException) as cm:
            get_single_variant(self.families, '10-10334333-A-G', user=self.user)
        self.assertEqual(str(cm.exception), 'Variant 10-10334333-A-G not found')

    @responses.activate
    def test_get_variants_for_variant_ids(self):
        variant_ids = ['2-103343353-GAGA-G', '1-248367227-TC-T', 'prefix-938_DEL']
        get_variants_for_variant_ids(self.families, variant_ids, user=self.user)
        expected_sample_data = {k: ALL_AFFECTED_SAMPLE_DATA[k] for k in ['SNV_INDEL', 'SV_WES']}
        self._test_minimal_search_call(
            variant_ids=[['2', 103343353, 'GAGA', 'G'], ['1', 248367227, 'TC', 'T']],
            variant_keys=['prefix-938_DEL'],
            num_results=3, sample_data=expected_sample_data)

        del expected_sample_data['SV_WES']
        get_variants_for_variant_ids(self.families, variant_ids, user=self.user, dataset_type='SNV_INDEL')
        self._test_minimal_search_call(
            variant_ids=[['2', 103343353, 'GAGA', 'G'], ['1', 248367227, 'TC', 'T']],
            variant_keys=[],
            num_results=2, sample_data=expected_sample_data)
