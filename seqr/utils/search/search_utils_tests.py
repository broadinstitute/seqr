from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
import json
import mock

from hail_search.test_utils import GENE_COUNTS, VARIANT_LOOKUP_VARIANT
from seqr.models import Family, Sample, VariantSearch, VariantSearchResults
from seqr.utils.search.utils import get_single_variant, get_variants_for_variant_ids, get_variant_query_gene_counts, \
    query_variants, variant_lookup, InvalidSearchException
from seqr.views.utils.test_utils import PARSED_VARIANTS, PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT, GENE_FIELDS

SV_SAMPLES = ['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733']
NON_SNP_INDEL_SAMPLES = SV_SAMPLES + ['S000149_hg00733']

class SearchTestHelper(object):

    def set_up(self):
        patcher = mock.patch('seqr.utils.redis_utils.redis.StrictRedis')
        self.mock_redis = patcher.start().return_value
        self.addCleanup(patcher.stop)

        self.families = Family.objects.filter(guid__in=['F000003_3', 'F000002_2', 'F000005_5'])
        self.user = User.objects.get(username='test_user')

        self.search_model = VariantSearch.objects.create(search={'inheritance': {'mode': 'de_novo'}})
        self.results_model = VariantSearchResults.objects.create(variant_search=self.search_model)
        self.results_model.families.set(self.families)

    def set_cache(self, cached):
        self.mock_redis.get.return_value = json.dumps(cached)

    def assert_cached_results(self, expected_results, sort='xpos', cache_key=None):
        cache_key = cache_key or f'search_results__{self.results_model.guid}__{sort}'
        self.mock_redis.set.assert_called_with(cache_key, mock.ANY)
        self.assertEqual(json.loads(self.mock_redis.set.call_args.args[1]), expected_results)
        self.mock_redis.expire.assert_called_with(cache_key, timedelta(weeks=2))


class SearchUtilsTests(SearchTestHelper):

    def set_up(self):
        super(SearchUtilsTests, self).set_up()

        self.non_affected_search_samples = Sample.objects.filter(guid__in=[
             'S000137_na20874',
        ])
        self.affected_search_samples = Sample.objects.filter(guid__in=[
            'S000132_hg00731', 'S000133_hg00732', 'S000134_hg00733', 'S000135_na20870',
            'S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733', 'S000149_hg00733',
        ])
        self.search_samples = list(self.affected_search_samples) + list(self.non_affected_search_samples)

    @mock.patch('seqr.utils.search.utils.hail_variant_lookup')
    def test_variant_lookup(self, mock_variant_lookup):
        mock_variant_lookup.return_value = VARIANT_LOOKUP_VARIANT
        variant = variant_lookup(self.user, '1-10439-AC-A', genome_version='38')
        self.assertDictEqual(variant, VARIANT_LOOKUP_VARIANT)
        mock_variant_lookup.assert_called_with(self.user, ('1', 10439, 'AC', 'A'), genome_version='GRCh38',
                                               dataset_type='SNV_INDEL_only')
        cache_key = 'variant_lookup_results__1-10439-AC-A__38__test_user'
        self.assert_cached_results(variant, cache_key=cache_key)

        variant = variant_lookup(self.user, '1-10439-AC-A', genome_version='37', families=self.families)
        self.assertDictEqual(variant, VARIANT_LOOKUP_VARIANT)
        mock_variant_lookup.assert_called_with(self.user, ('1', 10439, 'AC', 'A'), genome_version='GRCh37', samples=mock.ANY,
                                               dataset_type='SNV_INDEL_only')
        expected_samples = {s for s in self.search_samples if s.guid not in NON_SNP_INDEL_SAMPLES}
        self.assertSetEqual(set(mock_variant_lookup.call_args.kwargs['samples']), expected_samples)

        mock_variant_lookup.reset_mock()
        self.set_cache(variant)
        cached_variant = variant_lookup(self.user, '1-10439-AC-A', genome_version='38')
        self.assertDictEqual(variant, cached_variant)
        mock_variant_lookup.assert_not_called()
        self.mock_redis.get.assert_called_with(cache_key)

    def test_get_single_variant(self, mock_get_variants_for_ids):
        mock_get_variants_for_ids.return_value = [PARSED_VARIANTS[0]]
        variant = get_single_variant(self.families, '2-103343353-GAGA-G', user=self.user)
        self.assertDictEqual(variant, PARSED_VARIANTS[0])
        mock_get_variants_for_ids.assert_called_with(
            mock.ANY, '37', {'2-103343353-GAGA-G': ('2', 103343353, 'GAGA', 'G')}, self.user, return_all_queried_families=False,
            user_email=None,
        )
        expected_samples = {s for s in self.search_samples if s.guid not in NON_SNP_INDEL_SAMPLES}
        self.assertSetEqual(set(mock_get_variants_for_ids.call_args.args[0]), expected_samples)

        get_single_variant(self.families, '2-103343353-GAGA-G', user=self.user, return_all_queried_families=True)
        mock_get_variants_for_ids.assert_called_with(
            mock.ANY, '37', {'2-103343353-GAGA-G': ('2', 103343353, 'GAGA', 'G')}, self.user, return_all_queried_families=True,
            user_email=None,
        )
        self.assertSetEqual(set(mock_get_variants_for_ids.call_args.args[0]), expected_samples)

        get_single_variant(self.families, 'prefix_19107_DEL', user=self.user)
        mock_get_variants_for_ids.assert_called_with(
            mock.ANY, '37', {'prefix_19107_DEL': None}, self.user, return_all_queried_families=False, user_email=None,
        )
        expected_samples = {
            s for s in self.search_samples if s.guid in ['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733']
        }
        self.assertSetEqual(set(mock_get_variants_for_ids.call_args.args[0]), expected_samples)

        mock_get_variants_for_ids.return_value = []
        with self.assertRaises(InvalidSearchException) as cm:
            get_single_variant(self.families, '10-10334333-A-G')
        self.assertEqual(str(cm.exception), 'Variant 10-10334333-A-G not found')

    def test_get_variants_for_variant_ids(self, mock_get_variants_for_ids):
        variant_ids = ['2-103343353-GAGA-G', '1-248367227-TC-T', 'prefix-938_DEL', 'MT-10195-C-A']
        get_variants_for_variant_ids(self.families, variant_ids, user=self.user)
        mock_get_variants_for_ids.assert_called_with(mock.ANY, '37', {
            '2-103343353-GAGA-G': ('2', 103343353, 'GAGA', 'G'),
            '1-248367227-TC-T': ('1', 248367227, 'TC', 'T'),
            'MT-10195-C-A': ('M', 10195, 'C', 'A'),
            'prefix-938_DEL': None,
        }, self.user, user_email=None)
        self.assertSetEqual(set(mock_get_variants_for_ids.call_args.args[0]), set(self.search_samples))

        get_variants_for_variant_ids(
            self.families, variant_ids, user=self.user, dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS)
        mock_get_variants_for_ids.assert_called_with(mock.ANY, '37', {
            '2-103343353-GAGA-G': ('2', 103343353, 'GAGA', 'G'),
            '1-248367227-TC-T': ('1', 248367227, 'TC', 'T'),
            'MT-10195-C-A': ('M', 10195, 'C', 'A'),
        }, self.user, user_email=None)
        skipped_samples = ['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733']
        expected_samples = {s for s in self.search_samples if s.guid not in skipped_samples}
        self.assertSetEqual(set(mock_get_variants_for_ids.call_args.args[0]), expected_samples)

        get_variants_for_variant_ids(
            self.families, variant_ids[:3], user=self.user, dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS)
        mock_get_variants_for_ids.assert_called_with(mock.ANY, '37', {
            '2-103343353-GAGA-G': ('2', 103343353, 'GAGA', 'G'),
            '1-248367227-TC-T': ('1', 248367227, 'TC', 'T'),
        }, self.user, user_email=None)
        skipped_samples.append('S000149_hg00733')
        expected_samples = {s for s in self.search_samples if s.guid not in skipped_samples}
        self.assertSetEqual(set(mock_get_variants_for_ids.call_args.args[0]), expected_samples)

    @mock.patch('seqr.utils.search.utils.MAX_NO_LOCATION_COMP_HET_FAMILIES', 1)
    def _test_invalid_search_params(self, search_func):
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model, user=self.user, page=200)
        self.assertEqual(str(cm.exception), 'Unable to load more than 10000 variants (20000 requested)')

        self.search_model.search['inheritance'] = {'mode': 'recessive'}
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model)
        self.assertEqual(str(cm.exception), 'Annotations must be specified to search for compound heterozygous variants')

        self.search_model.search['annotations'] = {'frameshift': ['frameshift_variant']}
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model)
        self.assertEqual(
            str(cm.exception),
            'Location must be specified to search for compound heterozygous variants across many families')

        self.results_model.families.set([family for family in self.families if family.guid == 'F000005_5'])
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model)
        self.assertEqual(
            str(cm.exception),
            'Inheritance based search is disabled in families with no data loaded for affected individuals',
        )

        self.results_model.families.set([family for family in self.families if family.guid == 'F000003_3'])
        self.search_model.search['annotations'] = {'structural': ['DEL']}
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model)
        self.assertEqual(str(cm.exception), 'Unable to search against dataset type "SV"')

        self.search_model.search['annotations_secondary'] = {'frameshift': ['frameshift_variant']}
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model)
        self.assertEqual(
            str(cm.exception),
            'Unable to search for comp-het pairs with dataset type "SV". This may be because inheritance based search is disabled in families with no loaded affected individuals',
        )

        self.search_model.search['inheritance']['filter'] = {'affected': {'I000007_na20870': 'N'}}
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model)
        self.assertEqual(
            str(cm.exception),
            'Inheritance based search is disabled in families with no data loaded for affected individuals',
        )

        self.search_model.search['inheritance']['mode'] = None
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model, user=self.user)
        self.assertEqual(str(cm.exception), 'Inheritance must be specified if custom affected status is set')

        self.search_model.search['inheritance']['filter'] = {'genotype': {'I000004_hg00731': 'ref_ref'}}
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model)
        self.assertEqual(str(cm.exception), 'Invalid custom inheritance')

        self.results_model.families.set(Family.objects.filter(family_id='no_individuals'))
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model, user=self.user)
        self.assertEqual(str(cm.exception), 'No search data found for families no_individuals')

        self.results_model.families.set(Family.objects.all())
        self.search_model.search['annotations'] = None
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model, user=self.user)
        self.assertEqual(
            str(cm.exception),
            'Searching across multiple genome builds is not supported. Remove projects with differing genome builds from search: 37 - 1kg project nåme with uniçøde, Test Reprocessed Project; 38 - Non-Analyst Project',
        )

        self.search_model.search['locus'] = {'rawVariantItems': 'chr2-A-C'}
        with self.assertRaises(InvalidSearchException) as cm:
            search_func(self.results_model, user=self.user)
        self.assertEqual(str(cm.exception), 'Invalid variants: chr2-A-C')

        self.search_model.search['locus']['rawVariantItems'] = 'rs9876,chr2-1234-A-C'
        with self.assertRaises(InvalidSearchException) as cm:
            search_func(self.results_model, user=self.user)
        self.assertEqual(str(cm.exception), 'Invalid variant notation: found both variant IDs and rsIDs')

        self.search_model.search['locus']['rawItems'] = 'chr27:1234-5678,2:40-400000000, ENSG00012345'
        with self.assertRaises(InvalidSearchException) as cm:
            search_func(self.results_model, user=self.user)
        self.assertEqual(str(cm.exception), 'Invalid genes/intervals: chr27:1234-5678, chr2:40-400000000, ENSG00012345')

    def test_invalid_search_query_variants(self):
        with self.assertRaises(InvalidSearchException) as se:
            query_variants(self.results_model, sort='prioritized_gene', num_results=2)
        self.assertEqual(str(se.exception), 'Phenotype sort is only supported for single-family search.')

        self.set_cache({'total_results': 20000})
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model, page=1, num_results=2, load_all=True)
        self.assertEqual(str(cm.exception), 'Unable to export more than 1000 variants (20000 requested)')

        self._test_invalid_search_params(query_variants)

    def _test_expected_search_call(self, mock_get_variants, results_cache, search_fields=None, genes=None, intervals=None,
                                   rs_ids=None, variant_ids=None, parsed_variant_ids=None, inheritance_mode='de_novo',
                                   dataset_type=None, secondary_dataset_type=None, omitted_sample_guids=None,  **kwargs):
        expected_search = {
            'inheritance_mode': inheritance_mode,
            'inheritance_filter': {},
            'parsedLocus': {
                'genes': genes, 'intervals': intervals, 'rs_ids': rs_ids, 'variant_ids': variant_ids,
                'parsed_variant_ids': parsed_variant_ids,
            },
            'skipped_samples': mock.ANY,
            'dataset_type': dataset_type,
            'secondary_dataset_type': secondary_dataset_type,
        }
        expected_search.update({field: self.search_model.search[field] for field in search_fields or []})

        mock_get_variants.assert_called_with(mock.ANY, expected_search, self.user, results_cache, '37', **kwargs)
        searched_samples = self.affected_search_samples
        non_affected_search_samples = self.non_affected_search_samples
        if omitted_sample_guids:
            searched_samples = searched_samples.exclude(guid__in=omitted_sample_guids)
            non_affected_search_samples = non_affected_search_samples.exclude(guid__in=omitted_sample_guids)
        self.assertSetEqual(set(mock_get_variants.call_args.args[0]), set(searched_samples))
        self.assertSetEqual(set(mock_get_variants.call_args.args[1]['skipped_samples']), set(non_affected_search_samples))

    def test_query_variants(self, mock_get_variants):
        def _mock_get_variants(families, search, user, previous_search_results, genome_version, **kwargs):
            previous_search_results['all_results'] = PARSED_VARIANTS
            previous_search_results['total_results'] = 5
            return PARSED_VARIANTS
        mock_get_variants.side_effect = _mock_get_variants

        variants, total = query_variants(self.results_model, user=self.user)
        self.assertListEqual(variants, PARSED_VARIANTS)
        self.assertEqual(total, 5)
        results_cache = {'all_results': PARSED_VARIANTS, 'total_results': 5}
        self.assert_cached_results(results_cache)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
        )

        query_variants(
            self.results_model, user=self.user, sort='cadd', skip_genotype_filter=True, page=3, num_results=10,
        )
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='cadd', page=3, num_results=10, skip_genotype_filter=True,
        )

        query_variants(self.results_model, user=self.user, load_all=True)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=1000, skip_genotype_filter=False,
        )

        with mock.patch('seqr.utils.search.utils.MAX_EXPORT_VARIANTS', 4):
            with self.assertRaises(InvalidSearchException) as cm:
                query_variants(self.results_model, user=self.user, load_all=True)
        self.assertEqual(str(cm.exception), 'Unable to export more than 4 variants (5 requested)')
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=4, skip_genotype_filter=False,
        )

        self.set_cache({'total_results': 22})
        query_variants(self.results_model, user=self.user, load_all=True)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=22, skip_genotype_filter=False,
        )

        self.search_model.search['locus'] = {'rawVariantItems': '1-248367227-TC-T,2-103343353-GAGA-G'}
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=2, skip_genotype_filter=False,
            search_fields=['locus'], rs_ids=[],  variant_ids=['1-248367227-TC-T', '2-103343353-GAGA-G'],
            parsed_variant_ids=[('1', 248367227, 'TC', 'T'), ('2', 103343353, 'GAGA', 'G')], dataset_type='SNV_INDEL',
            omitted_sample_guids=['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733', 'S000149_hg00733'],
        )

        self.search_model.search['locus']['rawVariantItems'] = 'rs9876'
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            search_fields=['locus'], rs_ids=['rs9876'], variant_ids=[], parsed_variant_ids=[],
        )

        self.search_model.search['locus']['rawItems'] = 'DDX11L1, chr2:1234-5678, chr7:100-10100%10, ENSG00000186092'
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            search_fields=['locus'], genes={
                'ENSG00000223972': mock.ANY, 'ENSG00000186092': mock.ANY,
            }, intervals=[
                {'chrom': '2', 'start': 1234, 'end': 5678, 'offset': None},
                {'chrom': '7', 'start': 100, 'end': 10100, 'offset': 0.1},
            ],
        )
        parsed_genes = mock_get_variants.call_args.args[1]['parsedLocus']['genes']
        for gene in parsed_genes.values():
            self.assertSetEqual(set(gene.keys()), GENE_FIELDS)
        self.assertEqual(parsed_genes['ENSG00000223972']['geneSymbol'], 'DDX11L1')
        self.assertEqual(parsed_genes['ENSG00000186092']['geneSymbol'], 'OR4F5')

        self.search_model.search.update({'pathogenicity': {'clinvar': ['pathogenic', 'likely_pathogenic']}, 'locus': {}})
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            search_fields=['pathogenicity', 'locus'], dataset_type='SNV_INDEL', omitted_sample_guids=SV_SAMPLES,
        )

        self.search_model.search = {
            'inheritance': {'mode': 'recessive'}, 'annotations': {'frameshift': ['frameshift_variant']},
        }
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            inheritance_mode='recessive', dataset_type='SNV_INDEL', secondary_dataset_type=None,
            search_fields=['annotations'], omitted_sample_guids=['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733'],
        )

        self.search_model.search['annotations_secondary'] = {'structural_consequence': ['LOF']}
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            inheritance_mode='recessive', dataset_type='SNV_INDEL', secondary_dataset_type='SV',
            search_fields=['annotations', 'annotations_secondary']
        )

        self.search_model.search['annotations_secondary'].update({'SCREEN': ['dELS', 'DNase-only']})
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            inheritance_mode='recessive', dataset_type='SNV_INDEL', secondary_dataset_type='ALL',
            search_fields=['annotations', 'annotations_secondary']
        )

        self.search_model.search['annotations_secondary']['structural_consequence'] = []
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            inheritance_mode='recessive', dataset_type='SNV_INDEL', secondary_dataset_type='SNV_INDEL',
            search_fields=['annotations', 'annotations_secondary'],
            omitted_sample_guids=['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733'],
        )

    def test_cached_query_variants(self):
        self.set_cache({'total_results': 4, 'all_results': PARSED_VARIANTS + PARSED_VARIANTS})
        variants, total = query_variants(self.results_model, user=self.user)
        self.assertListEqual(variants, PARSED_VARIANTS + PARSED_VARIANTS)
        self.assertEqual(total, 4)

        variants, total = query_variants(self.results_model, user=self.user, num_results=2)
        self.assertListEqual(variants, PARSED_VARIANTS)
        self.assertEqual(total, 4)

    def test_invalid_search_get_variant_query_gene_counts(self):
        self._test_invalid_search_params(get_variant_query_gene_counts)

    def test_get_variant_query_gene_counts(self, mock_get_variants):
        def _mock_get_variants(families, search, user, previous_search_results, genome_version, **kwargs):
            previous_search_results['gene_aggs'] = GENE_COUNTS
            return GENE_COUNTS
        mock_get_variants.side_effect = _mock_get_variants

        gene_counts = get_variant_query_gene_counts(self.results_model, self.user)
        self.assertDictEqual(gene_counts, GENE_COUNTS)
        results_cache = {'gene_aggs': gene_counts}
        self.assert_cached_results(results_cache)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort=None, num_results=100, gene_agg=True,
        )

    def test_cached_get_variant_query_gene_counts(self):
        cached_gene_counts = {
            'ENSG00000135953': {'total': 5, 'families': {'F000003_3': 2, 'F000002_2': 1, 'F000011_11': 4}},
            'ENSG00000228198': {'total': 5, 'families': {'F000003_3': 4, 'F000002_2': 1, 'F000011_11': 4}}
        }
        self.set_cache({'total_results': 5, 'gene_aggs': cached_gene_counts})
        gene_counts = get_variant_query_gene_counts(self.results_model, self.user)
        self.assertDictEqual(gene_counts, cached_gene_counts)

        self.set_cache({'all_results': PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT, 'total_results': 2})
        gene_counts = get_variant_query_gene_counts(self.results_model, self.user)
        self.assertDictEqual(gene_counts, {
            'ENSG00000135953': {'total': 1, 'families': {'F000003_3': 1, 'F000011_11': 1}},
            'ENSG00000228198': {'total': 1, 'families': {'F000003_3': 1, 'F000011_11': 1}}
        })


@mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', 'testhost')
class ElasticsearchSearchUtilsTests(TestCase, SearchUtilsTests):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data']

    def setUp(self):
        self.set_up()

    def test_variant_lookup(self, *args, **kwargs):
        with self.assertRaises(InvalidSearchException) as cm:
            super().test_variant_lookup(*args, **kwargs)
        self.assertEqual(str(cm.exception), 'Hail backend is disabled')

    @mock.patch('seqr.utils.search.utils.get_es_variants_for_variant_ids')
    def test_get_single_variant(self, mock_get_variants_for_ids):
        super(ElasticsearchSearchUtilsTests, self).test_get_single_variant(mock_get_variants_for_ids)

    @mock.patch('seqr.utils.search.utils.get_es_variants_for_variant_ids')
    def test_get_variants_for_variant_ids(self, mock_get_variants_for_ids):
        super(ElasticsearchSearchUtilsTests, self).test_get_variants_for_variant_ids(mock_get_variants_for_ids)

    @mock.patch('seqr.utils.search.utils.get_es_variants')
    def test_query_variants(self, mock_get_variants):
        super(ElasticsearchSearchUtilsTests, self).test_query_variants(mock_get_variants)

    def test_cached_query_variants(self):
        super(ElasticsearchSearchUtilsTests, self).test_cached_query_variants()

        self.set_cache({
            'grouped_results': [
                {'null': [PARSED_VARIANTS[0]]}, {'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT},
                {'null': [PARSED_VARIANTS[1]]}
            ],
            'total_results': 3,
        })

        variants, total = query_variants(self.results_model, user=self.user)
        self.assertListEqual(variants, [PARSED_VARIANTS[0]] + [PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT] + [PARSED_VARIANTS[1]])
        self.assertEqual(total, 3)

        variants, total = query_variants(self.results_model, user=self.user, num_results=2)
        self.assertListEqual(variants, [PARSED_VARIANTS[0]] + [PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT])
        self.assertEqual(total, 3)

    @mock.patch('seqr.utils.search.utils.get_es_variants')
    def test_get_variant_query_gene_counts(self, mock_get_variants):
        super(ElasticsearchSearchUtilsTests, self).test_get_variant_query_gene_counts(mock_get_variants)

    def test_cached_get_variant_query_gene_counts(self):
        super(ElasticsearchSearchUtilsTests, self).test_cached_get_variant_query_gene_counts()

        self.set_cache({
            'grouped_results': [
                {'null': [PARSED_VARIANTS[0]]}, {'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT},
                {'null': [PARSED_VARIANTS[1]]}
            ],
            'loaded_variant_counts': {
                'test_index_second': {'loaded': 1, 'total': 1},
                'test_index_second_compound_het': {'total': 0, 'loaded': 0},
                'test_index': {'loaded': 1, 'total': 1},
                'test_index_compound_het': {'total': 2, 'loaded': 2},
            },
            'total_results': 4,
        })
        gene_counts = get_variant_query_gene_counts(self.results_model, self.user)
        self.assertDictEqual(gene_counts, {
            'ENSG00000135953': {'total': 2, 'families': {'F000003_3': 2, 'F000002_2': 1}},
            'ENSG00000228198': {'total': 2, 'families': {'F000003_3': 2, 'F000011_11': 2}}
        })


class HailSearchUtilsTests(TestCase, SearchUtilsTests):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data']

    def setUp(self):
        self.set_up()

    @mock.patch('seqr.utils.search.utils.get_hail_variants_for_variant_ids')
    def test_get_single_variant(self, mock_call):
        super(HailSearchUtilsTests, self).test_get_single_variant(mock_call)

    @mock.patch('seqr.utils.search.utils.get_hail_variants_for_variant_ids')
    def test_get_variants_for_variant_ids(self, mock_call):
        super(HailSearchUtilsTests, self).test_get_variants_for_variant_ids(mock_call)

    @mock.patch('seqr.utils.search.utils.get_hail_variants')
    def test_query_variants(self, mock_call):
        super(HailSearchUtilsTests, self).test_query_variants(mock_call)

    @mock.patch('seqr.utils.search.utils.get_hail_variants')
    def test_get_variant_query_gene_counts(self, mock_call):
        super(HailSearchUtilsTests, self).test_get_variant_query_gene_counts(mock_call)
