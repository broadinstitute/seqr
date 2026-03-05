from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
import json
import mock

from clickhouse_search.test_utils import VARIANT1, VARIANT2, VARIANT3, VARIANT4, PROJECT_2_VARIANT2, format_cached_variant, \
    GENE_COUNTS, VARIANT_LOOKUP_VARIANT, SV_LOOKUP_VARIANT, GCNV_LOOKUP_VARIANT, SV_VARIANT1
from seqr.models import Project, Family, Sample, VariantSearch, VariantSearchResults
from seqr.views.utils.json_utils import DjangoJSONEncoderWithSets
from seqr.utils.search.utils import get_single_variant, get_variant_query_gene_counts, \
    query_variants, variant_lookup, InvalidSearchException
from seqr.views.utils.test_utils import DifferentDbTransactionSupportMixin, \
    PARSED_VARIANTS, PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT, GENE_FIELDS


SV_SAMPLES = ['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733']
MITO_SAMPLES = ['S000149_hg00733']
NON_SNP_INDEL_SAMPLES = SV_SAMPLES + MITO_SAMPLES
FAMILY_3_SAMPLE = 'S000135_na20870'

GENE_COUNTS = {
    **GENE_COUNTS,
    'ENSG00000177000': {**GENE_COUNTS['ENSG00000177000'], 'total': 3},
    'ENSG00000277258': {**GENE_COUNTS['ENSG00000277258'], 'total': 2},
}

class SearchTestHelper(object):

    def set_up(self):
        patcher = mock.patch('seqr.utils.redis_utils.redis.StrictRedis')
        self.mock_redis = patcher.start().return_value
        self.addCleanup(patcher.stop)

        self.families = Family.objects.filter(guid__in=['F000003_3', 'F000002_2', 'F000005_5'])
        self.user = User.objects.get(username='test_user')

        self.search_model = VariantSearch.objects.create(search={'inheritance': {'mode': 'de_novo'}, 'freqs': {'callset': {'ac': 1000}}})
        self.results_model = VariantSearchResults.objects.create(variant_search=self.search_model)
        self.results_model.families.set(self.families)

    def set_cache(self, cached):
        self.mock_redis.get.return_value = json.dumps(cached)

    def assert_cached_results(self, expected_results, sort='xpos', cache_key=None):
        cache_key = cache_key or f'search_results__{self.results_model.guid}__{sort}'
        self.mock_redis.set.assert_called_with(cache_key, mock.ANY)
        self.assertEqual(json.loads(self.mock_redis.set.call_args.args[1]), expected_results)
        self.mock_redis.expire.assert_called_with(cache_key, timedelta(weeks=2))


class SearchUtilsTests(DifferentDbTransactionSupportMixin, TestCase, SearchTestHelper):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data', 'clickhouse_transcripts']

    PARSED_CACHED_VARIANTS = [VARIANT1, VARIANT2, VARIANT3, VARIANT4]
    CACHED_VARIANTS = [format_cached_variant(v) for v in PARSED_CACHED_VARIANTS]

    def setUp(self):
        self.set_up()

        self.non_affected_search_samples = Sample.objects.filter(guid__in=[
             'S000137_na20874',
        ])
        self.affected_search_samples = Sample.objects.filter(guid__in=[
            'S000132_hg00731', 'S000133_hg00732', 'S000134_hg00733', FAMILY_3_SAMPLE,
            'S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733', 'S000149_hg00733',
        ])
        self.search_samples = list(self.affected_search_samples) + list(self.non_affected_search_samples)


    def _get_expected_search_call(self, results_cache, search_fields=None, has_gene_search=False,
                                   variant_ids=None, parsed_variant_ids=None, inheritance_mode='de_novo',
                                   dataset_type=None, secondary_dataset_type=None, exclude_keys=None, exclude_key_pairs=None,
                                   exclude_locations=False, exclude=None, annotations=None, annotations_secondary=None, single_gene_search=False, **kwargs):
        genes = intervals = None
        if has_gene_search:
            genes = {'ENSG00000186092': mock.ANY, 'ENSG00000227232': mock.ANY}
            intervals = [{'chrom': '2', 'start': 1234, 'end': 5678, 'offset': None}, {'chrom': '7', 'start': 100, 'end': 10100, 'offset': 0.1}]
        if single_gene_search:
            genes = {'ENSG00000227232': mock.ANY}
            intervals = intervals[2:3]

        expected_search = {
            'inheritance_mode': inheritance_mode,
            'inheritance_filter': {},
            'skipped_samples': mock.ANY,
            'dataset_type': dataset_type,
            'secondary_dataset_type': secondary_dataset_type,
            'exclude_locations': exclude_locations,
            'genes': genes,
            'intervals': intervals,
            'freqs': {'callset': {'ac': 1000}},
        }
        if not genes:
            expected_search.update({
                'parsed_variant_ids': parsed_variant_ids,
                'variant_ids': variant_ids,
            })
        expected_search.update({field: self.search_model.search[field] for field in search_fields or []})
        if exclude:
            expected_search['exclude'] = exclude
        if annotations is not None:
            expected_search['annotations'] = annotations
        if annotations_secondary is not None:
            expected_search['annotations_secondary'] = annotations_secondary
        if exclude_keys is not None:
            expected_search['exclude_keys'] = exclude_keys
        if exclude_key_pairs is not None:
            expected_search['exclude_key_pairs'] = exclude_key_pairs

        return (mock.ANY, expected_search, self.user, results_cache, '37'), kwargs, genes

    def _test_expected_search_call(self, mock_get_variants, *args, has_gene_search=False, exclude_locations=False, omitted_sample_guids=None, **kwargs):
        call_args, call_kwargs, genes = self._get_expected_search_call(*args, has_gene_search=has_gene_search, exclude_locations=exclude_locations, **kwargs)
        mock_get_variants.assert_called_with(*call_args, **call_kwargs)
        self._assert_expected_search_samples(mock_get_variants, omitted_sample_guids, has_gene_search and not exclude_locations)

        if genes:
            parsed_genes = mock_get_variants.call_args.args[1]['genes']
            for gene in parsed_genes.values():
                self.assertSetEqual(set(gene.keys()), {'id', *GENE_FIELDS})
            self.assertEqual(parsed_genes['ENSG00000227232']['geneSymbol'], 'WASH7P')
            if len(genes) > 1:
                self.assertEqual(parsed_genes['ENSG00000186092']['geneSymbol'], 'OR4F5')


    def _assert_expected_search_samples(self, mock_get_variants, omitted_sample_guids, has_gene_search):
        searched_samples = self.affected_search_samples
        non_affected_search_samples = self.non_affected_search_samples
        if omitted_sample_guids:
            searched_samples = searched_samples.exclude(guid__in=omitted_sample_guids)
            non_affected_search_samples = non_affected_search_samples.exclude(guid__in=omitted_sample_guids)
        if has_gene_search:
            searched_samples = searched_samples.exclude(guid__in=MITO_SAMPLES)
        self.assertSetEqual(set(mock_get_variants.call_args.args[0]), set(searched_samples))
        self.assertSetEqual(set(mock_get_variants.call_args.args[1]['skipped_samples']), set(non_affected_search_samples))

    @mock.patch('seqr.utils.search.utils.get_clickhouse_variants')
    def test_query_variants(self, mock_get_variants):
        parsed_variants = [{**v, 'key': (i+1) * 1000 } for i, v in enumerate(PARSED_VARIANTS)]
        def _mock_get_variants(families, search, user, previous_search_results, genome_version, **kwargs):
            previous_search_results['all_results'] =parsed_variants
            previous_search_results['total_results'] = 5
            return parsed_variants
        mock_get_variants.side_effect = _mock_get_variants

        results_cache = {'all_results': parsed_variants, 'total_results': 5}

        query_variants(
            self.results_model, user=self.user,  page=3, num_results=10,
        )
        self._test_expected_search_call(
            mock_get_variants, results_cache, page=3, num_results=10,
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

        self._test_locus_query_variants(mock_get_variants, results_cache)

        locus_items = self.search_model.search['locus']['rawItems']
        del self.search_model.search['locus']
        self.search_model.search['exclude'] = {'clinvar': ['benign'], 'rawItems': locus_items}
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            has_gene_search=True, exclude_locations=True, exclude={'clinvar': ['benign']},
        )

        del self.search_model.search['exclude']['rawItems']
        self.search_model.search.update({'pathogenicity': {'clinvar': ['pathogenic', 'likely_pathogenic']},
                                         'annotations': {'frameshift': [], 'structural': []}})
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            search_fields=['exclude', 'pathogenicity'], annotations={}, dataset_type='SNV_INDEL', omitted_sample_guids=SV_SAMPLES,
        )

        self.search_model.search = {
            'inheritance': {'mode': 'recessive'}, 'annotations': {'frameshift': ['frameshift_variant']},
            'freqs': self.search_model.search['freqs'],
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

        screen_annotations = {'SCREEN': ['dELS', 'DNase-only']}
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
            search_fields=['annotations'], annotations_secondary=screen_annotations,
            omitted_sample_guids=['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733'],
        )

        self.set_cache(None)
        mock_get_variants.reset_mock()
        self.search_model.search = {
            'inheritance': {'mode': 'any_affected'},
            'exclude': {'previousSearch': True, 'previousSearchHash': 'abc1234', 'clinvar': ['benign']},
            'freqs': self.search_model.search['freqs'],
        }
        previous_search_model = VariantSearch.objects.create(search={'inheritance': {'mode': 'de_novo'}, 'freqs': self.search_model.search['freqs']})
        previous_results_model = VariantSearchResults.objects.create(variant_search=previous_search_model, search_hash='abc1234')
        previous_results_model.families.set(self.families)
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            inheritance_mode='any_affected', exclude={'clinvar': ['benign']}, search_fields=['exclude'],
            exclude_key_pairs={}, exclude_keys={'MITO': [1000, 2000]},
        )
        self.assertEqual(mock_get_variants.call_count, 2)
        call_args, call_kwargs, _ = self._get_expected_search_call(results_cache, inheritance_mode='de_novo', sort=None, num_results=100)
        mock_get_variants.assert_has_calls([mock.call(*call_args, **call_kwargs)])

        # Test when previous results are cached
        mock_get_variants.reset_mock()
        self.mock_redis.get.side_effect = [
            None,
            json.dumps({'all_results': [VARIANT1, [VARIANT1, VARIANT2], [VARIANT1, SV_VARIANT1], VARIANT2, [VARIANT4, VARIANT3], SV_VARIANT1]}),
        ]
        self.mock_redis.keys.side_effect = [[], ['search_results__abc1234__gnomad']]
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            inheritance_mode='any_affected', exclude={'clinvar': ['benign']}, search_fields=['exclude'],
            exclude_key_pairs={'SNV_INDEL': [[1, 2], [3, 4]], 'SNV_INDEL,SV_WGS': [[1, 12]]},
            exclude_keys={'SNV_INDEL': [1, 2], 'SV_WGS': [12]},
        )
        self.assertEqual(mock_get_variants.call_count, 1)

        del self.search_model.search['exclude']
        self.search_model.search['exclude_svs'] = True
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            inheritance_mode='any_affected', omitted_sample_guids=SV_SAMPLES, dataset_type='SNV_INDEL',
        )

        self.search_model.search['locus'] = {'rawItems': 'WASH7P'}
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            inheritance_mode='any_affected', has_gene_search=True, single_gene_search=True,
            omitted_sample_guids=NON_SNP_INDEL_SAMPLES, dataset_type='SNV_INDEL_only',
        )

    def _test_locus_query_variants(self, mock_get_variants, results_cache):
        self.search_model.search['locus'] = {'rawVariantItems': '1-248367227-TC-T,2-103343353-GAGA-G'}
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=2, skip_genotype_filter=False,
            variant_ids=['1-248367227-TC-T', '2-103343353-GAGA-G'],
            parsed_variant_ids=[('1', 248367227, 'TC', 'T'), ('2', 103343353, 'GAGA', 'G')], dataset_type='SNV_INDEL',
            omitted_sample_guids=['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733', 'S000149_hg00733'],
        )

        self.search_model.search['locus']['rawItems'] = 'WASH7P'
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            has_gene_search=True, single_gene_search=True, omitted_sample_guids=MITO_SAMPLES,
        )

        self.search_model.search['locus']['rawItems'] = 'WASH7P, chr2:1234-5678, chr7:100-10100%10, ENSG00000186092'
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            has_gene_search=True, omitted_sample_guids=MITO_SAMPLES,
        )

    def test_cached_query_variants(self):
        Project.objects.filter(id=1).update(genome_version='38')

        self.set_cache({'total_results': 4, 'all_results': self.CACHED_VARIANTS})
        variants, total = query_variants(self.results_model, user=self.user)
        self._assert_expected_cached_variants(variants, 4)
        self.assertEqual(total, 4)

        variants, total = query_variants(self.results_model, user=self.user, num_results=2)
        self._assert_expected_cached_variants(variants, 2)
        self.assertEqual(total, 4)

        cache_key_prefix = f'search_results__{self.results_model.guid}'
        self.mock_redis.get.side_effect = [None, json.dumps({'total_results': 4, 'all_results': self.CACHED_VARIANTS})]
        self.mock_redis.keys.return_value = [f'{cache_key_prefix}__xpos', f'{cache_key_prefix}__gnomad']

        variants, total = query_variants(self.results_model, user=self.user, sort='cadd')
        self.assertEqual(total, 4)
        self.assertListEqual(
            json.loads(json.dumps(variants, cls=DjangoJSONEncoderWithSets)),
            [VARIANT4, VARIANT3, VARIANT2, VARIANT1]
        )
        self.mock_redis.get.assert_has_calls([
            mock.call(f'{cache_key_prefix}__cadd'),
            mock.call(f'{cache_key_prefix}__xpos'),
        ])
        self.mock_redis.keys.assert_called_with(pattern=f'{cache_key_prefix}__*')
        self.assert_cached_results(
            {'all_results': [format_cached_variant(v) for v in [VARIANT4, VARIANT3, VARIANT2, VARIANT1]],
             'total_results': 4},
            sort='cadd',
        )

    def _assert_expected_cached_variants(self, variants, num_results):
        self.assertListEqual(
            json.loads(json.dumps(variants, cls=DjangoJSONEncoderWithSets)),
            self.PARSED_CACHED_VARIANTS[:num_results],
        )

    @mock.patch('seqr.utils.search.utils.get_clickhouse_variants')
    def test_get_variant_query_gene_counts(self, mock_get_variants):
        gene_agg_all_results = self.CACHED_VARIANTS + [format_cached_variant(PROJECT_2_VARIANT2)]
        def _mock_get_variants(families, search, user, previous_search_results, genome_version, **kwargs):
            previous_search_results['all_results'] = gene_agg_all_results
            return None

        mock_get_variants.side_effect = _mock_get_variants

        gene_counts = get_variant_query_gene_counts(self.results_model, self.user)
        self.assertDictEqual(gene_counts, GENE_COUNTS)
        results_cache = {'all_results': gene_agg_all_results}
        self.assert_cached_results(results_cache)
        kwargs = dict(sort=None, num_results=100)
        self._test_expected_search_call(
            mock_get_variants, results_cache, **kwargs,
        )

    def test_cached_get_variant_query_gene_counts(self):
        self.set_cache({'all_results': self.CACHED_VARIANTS + [SV_VARIANT1], 'total_results': 5})
        gene_counts = get_variant_query_gene_counts(self.results_model, self.user)
        self.assertDictEqual(gene_counts, {
            'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
            'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2}},
            'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
            'ENSG00000171621': {'total': 1, 'families': {'F000014_14': 1}},
        })
