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
from seqr.views.utils.test_utils import DifferentDbTransactionSupportMixin, PARSED_VARIANTS, PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT, GENE_FIELDS


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

    CACHED_VARIANTS = PARSED_VARIANTS + PARSED_VARIANTS
    HAS_GENE_AGG = False

    def set_up(self):
        super(SearchUtilsTests, self).set_up()

        self.non_affected_search_samples = Sample.objects.filter(guid__in=[
             'S000137_na20874',
        ])
        self.affected_search_samples = Sample.objects.filter(guid__in=[
            'S000132_hg00731', 'S000133_hg00732', 'S000134_hg00733', FAMILY_3_SAMPLE,
            'S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733', 'S000149_hg00733',
        ])
        self.search_samples = list(self.affected_search_samples) + list(self.non_affected_search_samples)

    def test_variant_lookup(self, mock_variant_lookup):
        mock_variant_lookup.return_value = [VARIANT_LOOKUP_VARIANT]
        variants = variant_lookup(self.user, '1-10439-AC-A', '38', affected_only=True)
        self.assertListEqual(variants, [VARIANT_LOOKUP_VARIANT])
        mock_variant_lookup.assert_called_with(self.user, ('1', 10439, 'AC', 'A'), 'SNV_INDEL', None, '38', True, False)
        cache_key = "variant_lookup_results__1-10439-AC-A__38"
        self.assert_cached_results(variants, cache_key=cache_key)

        mock_variant_lookup.reset_mock()
        self.set_cache(variants)
        cached_variant = variant_lookup(self.user, '1-10439-AC-A', '38')
        self.assertListEqual(variants, cached_variant)
        mock_variant_lookup.assert_not_called()
        self.mock_redis.get.assert_called_with(cache_key)

        self.set_cache(None)
        mock_variant_lookup.reset_mock()
        with self.assertRaises(InvalidSearchException) as cm:
            variant_lookup(self.user, 'phase2_DEL_chr14_4640', '37')
        self.assertEqual(str(cm.exception), 'SV variants are not available for GRCh37')

        with self.assertRaises(InvalidSearchException) as cm:
            variant_lookup(self.user, 'phase2_DEL_chr14_4640', '38')
        self.assertEqual(str(cm.exception), 'Sample type must be specified to look up a structural variant')

        mock_variant_lookup.return_value = [SV_LOOKUP_VARIANT, GCNV_LOOKUP_VARIANT]
        variants = variant_lookup(self.user, 'phase2_DEL_chr14_4640', '38', sample_type='WGS', hom_only=True)
        self.assertListEqual(variants, [SV_LOOKUP_VARIANT, GCNV_LOOKUP_VARIANT])
        mock_variant_lookup.assert_called_with(
            self.user, 'phase2_DEL_chr14_4640', 'SV', 'WGS', '38', False, True)
        cache_key = 'variant_lookup_results__phase2_DEL_chr14_4640__38'
        self.assert_cached_results(variants, cache_key=cache_key)

        mock_variant_lookup.reset_mock()
        self.set_cache(variants)
        cached_variant = variant_lookup(self.user, 'phase2_DEL_chr14_4640', '38', sample_type='WGS')
        self.assertListEqual(variants, cached_variant)
        mock_variant_lookup.assert_not_called()
        self.mock_redis.get.assert_called_with(cache_key)

    def test_get_single_variant(self, mock_get_variants_for_ids):
        family = self.families.filter(guid='F000002_2').first()
        variant = get_single_variant(family, '2-103343353-GAGA-G', user=self.user)
        self.assertDictEqual(variant, PARSED_VARIANTS[0])
        expected_samples = {s for s in self.affected_search_samples if s.guid not in NON_SNP_INDEL_SAMPLES and s.guid != FAMILY_3_SAMPLE}
        self._assert_expected_get_single_variant_call(
            mock_get_variants_for_ids, ('2', 103343353, 'GAGA', 'G'), expected_samples,
        )

        get_single_variant(family, 'prefix_19107_DEL', user=self.user)
        expected_samples = {
            s for s in self.search_samples if s.guid in ['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733']
        }
        self._assert_expected_get_single_variant_call(
            mock_get_variants_for_ids, 'prefix_19107_DEL', expected_samples, dataset_type='SV',
        )

        mock_get_variants_for_ids.return_value = []
        with self.assertRaises(InvalidSearchException) as cm:
            get_single_variant(family, '10-10334333-A-G')
        self.assertEqual(str(cm.exception), 'Variant 10-10334333-A-G not found')

    def _assert_expected_get_single_variant_call(self, mock_get_variants_for_ids, variant_id, expected_samples, **kwargs):
        if not isinstance(variant_id, str):
            variant_id = '-'.join([str(v) for v in variant_id])
        mock_get_variants_for_ids.assert_called_with(
            mock.ANY, '37', [variant_id], self.user,
        )
        self.assertSetEqual(set(mock_get_variants_for_ids.call_args.args[0]), expected_samples)

    @mock.patch('seqr.utils.search.utils.MAX_FAMILY_COUNTS', {'WES': 2, 'WGS': 1})
    @mock.patch('seqr.utils.search.utils.MAX_NO_LOCATION_COMP_HET_FAMILIES', 1)
    def _test_invalid_search_params(self, search_func):
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model, user=self.user, page=200)
        self.assertEqual(str(cm.exception), 'Unable to load more than 10000 variants (20000 requested)')

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

        build_specific_genes = 'DDX11L1, OR4F29, ENSG00000223972, ENSG00000256186'
        self.search_model.search['locus']['rawItems'] = build_specific_genes
        with self.assertRaises(InvalidSearchException) as cm:
            search_func(self.results_model, user=self.user)
        self.assertEqual(str(cm.exception), 'Invalid genes/intervals: DDX11L1, ENSG00000223972')

        self.search_model.search['exclude'] = self.search_model.search['locus']
        with self.assertRaises(InvalidSearchException) as cm:
            search_func(self.results_model, user=self.user)
        self.assertEqual(str(cm.exception), 'Cannot specify both Location and Excluded Genes/Intervals')

        self.search_model.search['locus'] = {}
        with self.assertRaises(InvalidSearchException) as cm:
            search_func(self.results_model, user=self.user)
        self.assertEqual(str(cm.exception), 'Invalid genes/intervals: DDX11L1, ENSG00000223972')

        self.search_model.search['pathogenicity'] = {'clinvar': ['pathogenic', 'vus']}
        self.search_model.search['exclude'] = {'clinvar': ['benign', 'vus']}
        with self.assertRaises(InvalidSearchException) as cm:
            search_func(self.results_model, user=self.user)
        self.assertEqual(str(cm.exception), 'ClinVar pathogenicity vus is both included and excluded')

        self.search_model.search['exclude'] = {}
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
        self.search_model.search['pathogenicity'] = {}
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

        self._test_invalid_no_location_search_params()

        self.results_model.families.set(Family.objects.filter(guid='F000014_14'))
        self.search_model.search['locus']['rawItems'] = build_specific_genes
        with self.assertRaises(InvalidSearchException) as cm:
            search_func(self.results_model, user=self.user)
        self.assertEqual(str(cm.exception), 'Invalid genes/intervals: OR4F29, ENSG00000256186')

    def _test_invalid_no_location_search_params(self):
        self.results_model.families.set(self.families)
        self.search_model.search['inheritance'] = {}
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model)
        self.assertEqual(str(cm.exception), 'Location must be specified to search across multiple families in large projects')

        self.results_model.families.set(Family.objects.filter(id__in=[2, 11]))
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model)
        self.assertEqual(str(cm.exception), 'Location must be specified to search across multiple projects')

    def test_invalid_search_query_variants(self):
        with self.assertRaises(InvalidSearchException) as se:
            query_variants(self.results_model, sort='prioritized_gene', num_results=2)
        self.assertEqual(str(se.exception), 'Phenotype sort is only supported for single-family search.')

        self.set_cache({'total_results': 20000})
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(self.results_model, page=1, num_results=2, load_all=True)
        self.assertEqual(str(cm.exception), 'Unable to export more than 1000 variants (20000 requested)')

        self._test_invalid_search_params(query_variants)

    def _get_expected_search_call(self, results_cache, search_fields=None, has_gene_search=False,
                                   rs_ids=None, variant_ids=None, parsed_variant_ids=None, inheritance_mode='de_novo',
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
        }
        if not genes:
            expected_search.update({
                'parsed_variant_ids': parsed_variant_ids,
                'rs_ids': rs_ids,
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


    def test_query_variants(self, mock_get_variants):
        parsed_variants = [{**v, 'key': (i+1) * 1000 } for i, v in enumerate(PARSED_VARIANTS)]
        def _mock_get_variants(families, search, user, previous_search_results, genome_version, **kwargs):
            previous_search_results['all_results'] =parsed_variants
            previous_search_results['total_results'] = 5
            return parsed_variants
        mock_get_variants.side_effect = _mock_get_variants

        variants, total = query_variants(self.results_model, user=self.user)
        self.assertListEqual(variants, parsed_variants)
        self.assertEqual(total, 5)
        results_cache = {'all_results': parsed_variants, 'total_results': 5}
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
            rs_ids=[],  variant_ids=['1-248367227-TC-T', '2-103343353-GAGA-G'],
            parsed_variant_ids=[('1', 248367227, 'TC', 'T'), ('2', 103343353, 'GAGA', 'G')], dataset_type='SNV_INDEL',
            omitted_sample_guids=['S000145_hg00731', 'S000146_hg00732', 'S000148_hg00733', 'S000149_hg00733'],
        )

        self.search_model.search['locus']['rawVariantItems'] = 'rs9876'
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            rs_ids=['rs9876'], variant_ids=[], parsed_variant_ids=[], omitted_sample_guids=SV_SAMPLES, dataset_type='SNV_INDEL',
        )

        locus_items = 'WASH7P, chr2:1234-5678, chr7:100-10100%10, ENSG00000186092'
        self.search_model.search['locus']['rawItems'] = locus_items
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            has_gene_search=True, omitted_sample_guids=MITO_SAMPLES,
        )

        self.search_model.search['locus']['rawItems'] = 'WASH7P'
        query_variants(self.results_model, user=self.user)
        self._test_expected_search_call(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            has_gene_search=True, single_gene_search=True, omitted_sample_guids=MITO_SAMPLES,
        )

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
        }
        previous_search_model = VariantSearch.objects.create(search={'inheritance': {'mode': 'de_novo'}})
        previous_results_model = VariantSearchResults.objects.create(variant_search=previous_search_model, search_hash='abc1234')
        previous_results_model.families.set(self.families)
        query_variants(self.results_model, user=self.user)
        self._test_exclude_previous_search(
            mock_get_variants, results_cache, sort='xpos', page=1, num_results=100, skip_genotype_filter=False,
            inheritance_mode='any_affected', exclude={'clinvar': ['benign']}, search_fields=['exclude'],
        )

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

    def _test_exclude_previous_search(self, mock_get_variants, *args, num_searches=1, **kwargs):
        self._test_expected_search_call(mock_get_variants, *args, **kwargs)
        self.assertEqual(mock_get_variants.call_count, num_searches)

    def test_cached_query_variants(self):
        self.set_cache({'total_results': 4, 'all_results': self.CACHED_VARIANTS})
        variants, total = query_variants(self.results_model, user=self.user)
        self._assert_expected_cached_variants(variants, 4)
        self.assertEqual(total, 4)

        variants, total = query_variants(self.results_model, user=self.user, num_results=2)
        self._assert_expected_cached_variants(variants, 2)
        self.assertEqual(total, 4)

    def _assert_expected_cached_variants(self, variants, num_results):
        self.assertListEqual(variants, self.CACHED_VARIANTS[:num_results])

    def test_invalid_search_get_variant_query_gene_counts(self):
        self._test_invalid_search_params(get_variant_query_gene_counts)

    def test_get_variant_query_gene_counts(self, mock_get_variants):
        def _mock_get_variants(families, search, user, previous_search_results, genome_version, **kwargs):
            previous_search_results['all_results'] = self.GENE_AGG_ALL_RESULTS
            return None
        def _mock_get_gene_counts(families, search, user, previous_search_results, genome_version, **kwargs):
            previous_search_results['gene_aggs'] = GENE_COUNTS
            return GENE_COUNTS

        mock_get_variants.side_effect = _mock_get_variants if hasattr(self, 'GENE_AGG_ALL_RESULTS') else _mock_get_gene_counts

        gene_counts = get_variant_query_gene_counts(self.results_model, self.user)
        self.assertDictEqual(gene_counts, GENE_COUNTS)
        results_cache = {'all_results': self.GENE_AGG_ALL_RESULTS} if hasattr(self, 'GENE_AGG_ALL_RESULTS') else  {'gene_aggs': gene_counts}
        self.assert_cached_results(results_cache)
        kwargs = dict(sort=None, num_results=100)
        if self.HAS_GENE_AGG:
            kwargs['gene_agg'] = True
        self._test_expected_search_call(
            mock_get_variants, results_cache, **kwargs,
        )


@mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', 'testhost')
class ElasticsearchSearchUtilsTests(TestCase, SearchUtilsTests):
    databases = ['default', 'reference_data']
    fixtures = ['users', '1kg_project', 'reference_data']

    HAS_GENE_AGG = True

    def setUp(self):
        self.set_up()

    def _assert_expected_search_samples(self, mock_get_variants, omitted_sample_guids, has_gene_search):
        return super()._assert_expected_search_samples(mock_get_variants, omitted_sample_guids, False)

    def test_variant_lookup(self, *args, **kwargs):
        with self.assertRaises(ValueError) as cm:
            super().test_variant_lookup(mock.MagicMock())
        self.assertEqual(str(cm.exception), 'variant_lookup is disabled without the clickhouse backend')

    @mock.patch('seqr.utils.search.utils.get_es_variants_for_variant_ids')
    def test_get_single_variant(self, mock_get_variants_for_ids):
        mock_get_variants_for_ids.return_value = [PARSED_VARIANTS[0]]
        super(ElasticsearchSearchUtilsTests, self).test_get_single_variant(mock_get_variants_for_ids)

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
            'ENSG00000228198': {'total': 1, 'families': {'F000003_3': 1, 'F000011_11': 1}},
        })

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

    def _test_invalid_no_location_search_params(self):
        # Elasticsearch has no limits on no-location searches
        pass


class ClickhouseSearchUtilsTests(DifferentDbTransactionSupportMixin, TestCase, SearchUtilsTests):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data', 'clickhouse_transcripts']

    PARSED_CACHED_VARIANTS = [VARIANT1, VARIANT2, VARIANT3, VARIANT4]
    CACHED_VARIANTS = [format_cached_variant(v) for v in PARSED_CACHED_VARIANTS]
    GENE_AGG_ALL_RESULTS = CACHED_VARIANTS + [format_cached_variant(PROJECT_2_VARIANT2)]

    def setUp(self):
        self.set_up()

    def _assert_expected_cached_variants(self, variants, num_results):
        self.assertListEqual(
            json.loads(json.dumps(variants, cls=DjangoJSONEncoderWithSets)),
            self.PARSED_CACHED_VARIANTS[:num_results],
        )

    @mock.patch('seqr.utils.search.utils.get_clickhouse_variant_by_id')
    def test_get_single_variant(self, mock_call):
        mock_call.return_value = PARSED_VARIANTS[0]
        super().test_get_single_variant(mock_call)

    def _assert_expected_get_single_variant_call(self, mock_call, variant_id, expected_samples, dataset_type='SNV_INDEL', **kwargs):
        mock_call.assert_called_with(variant_id, mock.ANY, '37', dataset_type)
        self.assertSetEqual(set(mock_call.call_args.args[1]), expected_samples)

    @mock.patch('seqr.utils.search.utils.get_clickhouse_variants')
    def test_query_variants(self, mock_call):
        super().test_query_variants(mock_call)

    def _test_exclude_previous_search(self, mock_get_variants, *args, **kwargs):
        super()._test_exclude_previous_search(
            mock_get_variants, *args, **kwargs,
            exclude_key_pairs={}, exclude_keys={'MITO': [1000, 2000]}, num_searches=2,
        )
        call_args, call_kwargs, _ = self._get_expected_search_call(*args, inheritance_mode='de_novo', sort=None, num_results=100)
        mock_get_variants.assert_has_calls([mock.call(*call_args, **call_kwargs)])

        # Test when previous results are cached
        mock_get_variants.reset_mock()
        self.mock_redis.get.side_effect = [
            None,
            json.dumps({'all_results': [VARIANT1, [VARIANT1, VARIANT2], [VARIANT1, SV_VARIANT1], VARIANT2, [VARIANT4, VARIANT3], SV_VARIANT1]}),
        ]
        self.mock_redis.keys.side_effect = [[], ['search_results__abc1234__gnomad']]
        query_variants(self.results_model, user=self.user)
        super()._test_exclude_previous_search(
            mock_get_variants, *args, **kwargs, num_searches=1,
            exclude_key_pairs={'SNV_INDEL': [[1, 2], [3, 4]], 'SNV_INDEL,SV_WGS': [[1, 12]]},
            exclude_keys={'SNV_INDEL': [1, 2], 'SV_WGS': [12]},
        )

    def test_cached_query_variants(self):
        Project.objects.filter(id=1).update(genome_version='38')
        super().test_cached_query_variants()

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
            {'all_results': [format_cached_variant(v) for v in [VARIANT4, VARIANT3, VARIANT2, VARIANT1]], 'total_results': 4},
            sort='cadd',
        )

    @mock.patch('seqr.utils.search.utils.get_clickhouse_variants')
    def test_get_variant_query_gene_counts(self, mock_call):
        super().test_get_variant_query_gene_counts(mock_call)

    def test_cached_get_variant_query_gene_counts(self):
        self.set_cache({'all_results': self.CACHED_VARIANTS + [SV_VARIANT1], 'total_results': 5})
        gene_counts = get_variant_query_gene_counts(self.results_model, self.user)
        self.assertDictEqual(gene_counts, {
            'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
            'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2}},
            'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
            'ENSG00000171621': {'total': 1, 'families': {'F000014_14': 1}},
        })

    @mock.patch('seqr.utils.search.utils.clickhouse_variant_lookup')
    def test_variant_lookup(self, mock_call):
        super().test_variant_lookup(mock_call)
