from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase
from django.urls.base import reverse
import json
import mock

from clickhouse_search.test_utils import VARIANT1, VARIANT2, VARIANT3, VARIANT4, CACHED_CONSEQUENCES_BY_KEY, \
    VARIANT_ID_SEARCH, VARIANT_IDS, LOCATION_SEARCH, GENE_IDS, SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT, \
    SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_3, COMP_HET_ALL_PASS_FILTERS, \
    SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, SELECTED_ANNOTATION_TRANSCRIPT_MULTI_FAMILY_VARIANT, MULTI_FAMILY_VARIANT, \
    FAMILY_3_VARIANT, PROJECT_2_VARIANT, PROJECT_2_VARIANT1, MULTI_PROJECT_VARIANT1, MULTI_PROJECT_VARIANT2, GENE_COUNTS, \
    MULTI_PROJECT_BOTH_SAMPLE_TYPE_VARIANTS, VARIANT1_BOTH_SAMPLE_TYPES, VARIANT2_BOTH_SAMPLE_TYPES, \
    VARIANT3_BOTH_SAMPLE_TYPES, VARIANT4_BOTH_SAMPLE_TYPES, GRCH37_VARIANT, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3, \
    SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4, SV_GENE_COUNTS, NEW_SV_FILTER, GCNV_VARIANT1, GCNV_VARIANT2, \
    GCNV_VARIANT3, GCNV_VARIANT4, GCNV_MULTI_FAMILY_VARIANT1, GCNV_MULTI_FAMILY_VARIANT2, GCNV_GENE_COUNTS, \
    MULTI_DATA_TYPE_COMP_HET_VARIANT2, ALL_SNV_INDEL_PASS_FILTERS, MULTI_PROJECT_GCNV_VARIANT3, VARIANT_LOOKUP_VARIANT, \
    MITO_GENE_COUNTS, PROJECT_4_COMP_HET_VARIANT, SV_LOOKUP_VARIANT, GCNV_LOOKUP_VARIANT, GCNV_LOOKUP_VARIANT_3, \
    format_cached_variant
from reference_data.models import Omim
from seqr.models import Project, Family, Sample, VariantSearch, VariantSearchResults
from seqr.utils.search.search_utils_tests import SearchTestHelper
from seqr.utils.search.utils import query_variants, variant_lookup, get_variant_query_gene_counts, get_single_variant, InvalidSearchException
from seqr.views.utils.json_utils import DjangoJSONEncoderWithSets
from seqr.views.utils.test_utils import AnvilAuthenticationTestMixin
from seqr.views.apis.variant_search_api import gene_variant_lookup

from settings import DATABASES


class ClickhouseSearchTestCase(AnvilAuthenticationTestMixin, TransactionTestCase):

    def setUp(self):
        super().set_up_test()

    def _fixture_setup(self): # pylint: disable=arguments-differ
        # TransactionTestCase does not call setupTestData in the same way as TestCase
        # https://github.com/django/django/blob/stable/4.2.x/django/test/testcases.py#L1466
        # As a warning to a future reader, this method changes from an instance to a class method
        # between versions 4.x and 6.x (alongside several other impactful method changes).  When
        # Django is updated, our pattern here must be re-visited.
        super()._fixture_setup()
        with connections['clickhouse_write'].cursor() as cursor:
            cursor.execute('SYSTEM RELOAD DICTIONARY "seqrdb_affected_status_dict"')
        for db in DATABASES.keys():
            call_command("loaddata", 'clickhouse_search', database=db)
        with connections['clickhouse_write'].cursor() as cursor:
            for table_base in ['GRCh38/SNV_INDEL', 'GRCh38/MITO', 'GRCh38/SV', 'GRCh37/SNV_INDEL']:
                cursor.execute(f'SYSTEM REFRESH VIEW "{table_base}/project_gt_stats_to_gt_stats_mv"')
                cursor.execute(f'SYSTEM WAIT VIEW "{table_base}/project_gt_stats_to_gt_stats_mv"')
                cursor.execute(f'SYSTEM RELOAD DICTIONARY "{table_base}/gt_stats_dict"')
        Project.objects.update(genome_version='38')
        AnvilAuthenticationTestMixin.set_up_users()


class ClickhouseSearchTests(SearchTestHelper, ClickhouseSearchTestCase):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'variant_searches', 'reference_data', 'clickhouse_transcripts']

    def setUp(self):
        super().set_up()
        super().setUp()
        self.mock_redis.get.return_value = None

    def _assert_expected_search(self, expected_results, gene_counts=None, inheritance_mode=None, inheritance_filter=None, quality_filter=None, cached_variant_fields=None, sort='xpos', results_model=None, **search_kwargs):
        results_model = results_model or self.results_model
        self.search_model.search.update(search_kwargs or {})
        self.search_model.search['qualityFilter'] = quality_filter
        self.search_model.search['inheritance']['mode'] = inheritance_mode
        if inheritance_filter is not None:
            self.search_model.search['inheritance']['filter'] = inheritance_filter

        variants, total = query_variants(results_model, user=self.user, sort=sort)
        encoded_variants = self._assert_expected_variants(variants, expected_results)

        self.assertEqual(total, len(expected_results))
        self._assert_expected_search_cache(encoded_variants, total, cached_variant_fields, sort, results_model)

        if gene_counts:
            gene_counts_json = get_variant_query_gene_counts(results_model, self.user)
            self.assertDictEqual(gene_counts_json, gene_counts)

    def _assert_expected_variants(self, variants, expected_results):
        encoded_variants = json.loads(json.dumps(variants, cls=DjangoJSONEncoderWithSets))
        self.assertListEqual(encoded_variants, expected_results)
        return encoded_variants

    def _assert_expected_search_cache(self, variants, total, cached_variant_fields, sort, results_model):
        cached_variants = [
            self._get_cached_variant(variant, (cached_variant_fields[i] if cached_variant_fields else None))
            for i, variant in enumerate(variants)
        ]
        results_cache = {'all_results': cached_variants, 'total_results': total}
        self.assert_cached_results(results_cache, sort=sort, cache_key=f'search_results__{results_model.guid}__{sort}')

    @classmethod
    def _get_cached_variant(cls, variant, cached_variant_fields):
        if isinstance(variant, list):
            return [
                cls._get_cached_variant(v, cached_variant_fields[i] if cached_variant_fields else None)
                for i, v in enumerate(variant)
            ]
        return {
            **format_cached_variant(variant),
            **(cached_variant_fields or {}),
        }

    def _set_multi_project_search(self):
        self.results_model.families.set(Family.objects.filter(guid__in=['F000002_2', 'F000011_11']))

    def _set_single_family_search(self):
        self.results_model.families.set(self.families.filter(guid='F000002_2'))

    def _set_sv_family_search(self):
        self.results_model.families.set(Family.objects.filter(guid__in=['F000014_14']))

    def _reset_search_families(self):
        self.results_model.families.set(self.families)

    def _set_grch37_search(self):
        Project.objects.filter(id=1).update(genome_version='37')
        Sample.objects.filter(sample_id='HG00732').update(is_active=False)
        Sample.objects.exclude(dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS).update(is_active=False)
        self._set_single_family_search()

    def test_single_family_search(self):
        self._set_single_family_search()
        variant_gene_counts = {
            'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
            'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2}},
            'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}}
        }
        self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT3, VARIANT4], gene_counts=variant_gene_counts, locus={'rawItems': '1:1-100000000'},
            **ALL_SNV_INDEL_PASS_FILTERS,
        )

        self._assert_expected_search(
            [MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], gene_counts=MITO_GENE_COUNTS, locus={'rawItems': 'M:1-100000000'},
            annotations=None, pathogenicity=None,
        )

        self._assert_expected_search(
            [GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], gene_counts=GCNV_GENE_COUNTS,
            locus=None, annotations={'structural': COMP_HET_ALL_PASS_FILTERS['annotations']['structural']},
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4], gene_counts=SV_GENE_COUNTS, annotations=None,
        )

        self.results_model.families.set(Family.objects.filter(guid__in=['F000002_2', 'F000014_14']))
        self._assert_expected_search(
            [VARIANT1, SV_VARIANT1, SV_VARIANT2, VARIANT2, VARIANT3, VARIANT4, SV_VARIANT3, GCNV_VARIANT1,
                         GCNV_VARIANT2, GCNV_VARIANT3, SV_VARIANT4, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            gene_counts={**variant_gene_counts, **MITO_GENE_COUNTS, **GCNV_GENE_COUNTS, **SV_GENE_COUNTS, 'ENSG00000277258': {'total': 2, 'families': {'F000002_2': 2}}},
        )

        self._set_grch37_search()
        self._assert_expected_search([GRCH37_VARIANT])

    def test_standard_searches(self):
        results_model = self._saved_search_results_model('De Novo/Dominant Restrictive')
        self._assert_expected_search(
            [VARIANT1, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], results_model=results_model, cached_variant_fields=[
                {'selectedTranscript': None}, {}, {}, {},
            ],
        )

        results_model = self._saved_search_results_model('De Novo/Dominant Permissive')
        self._assert_expected_search(
            [VARIANT1, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], results_model=results_model, cached_variant_fields=[
                {'selectedTranscript': None}, {}, {}, {},
            ],
        )

        results_model = self._saved_search_results_model('Recessive Restrictive')
        self._assert_expected_search([VARIANT2, MITO_VARIANT3], results_model=results_model, cached_variant_fields=[
            {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][0]}, {},
        ])

        results_model = self._saved_search_results_model('Recessive Permissive')
        self._assert_expected_search([VARIANT2, [VARIANT3, VARIANT4], MITO_VARIANT3], results_model=results_model, cached_variant_fields=[
            {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][0]}, [
                {'selectedGeneId': 'ENSG00000097046', 'selectedTranscript': None,},
                {'selectedGeneId': 'ENSG00000097046', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][0]},
            ], {},
        ])

    def _saved_search_results_model(self, name):
        results_model = VariantSearchResults.objects.create(variant_search=VariantSearch.objects.get(name=name), search_hash=name)
        results_model.families.set(self.families.filter(guid='F000002_2'))
        return results_model

    def test_single_project_search(self):
        variant_gene_counts = {
            'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2, 'F000003_3': 1}},
            'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2, 'F000003_3': 1}},
            'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
            **MITO_GENE_COUNTS,
        }
        self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2,
             GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            gene_counts={**variant_gene_counts, **GCNV_GENE_COUNTS, 'ENSG00000277258': {'total': 2, 'families': {'F000002_2': 2}}}
        )

        self._add_sample_type_samples('WES', dataset_type='SV', guid__in=['S000135_na20870'])
        self._assert_expected_search(
            [GCNV_MULTI_FAMILY_VARIANT1, GCNV_MULTI_FAMILY_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], gene_counts={
                'ENSG00000129562': {'total': 1, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000013364': {'total': 1, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000079616': {'total': 1, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000103495': {'total': 1, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000167371': {'total': 1, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000280789': {'total': 1, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000280893': {'total': 1, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000281348': {'total': 1, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000275023': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000277972': {'total': 1, 'families': {'F000002_2': 1}},
            }, annotations={'structural': COMP_HET_ALL_PASS_FILTERS['annotations']['structural']},
        )

    def test_multi_project_search(self):
        self._set_multi_project_search()
        gene_counts = {
            **GENE_COUNTS,
            **MITO_GENE_COUNTS,
            **GCNV_GENE_COUNTS,
            'ENSG00000277258': {'total': 2, 'families': {'F000002_2': 2, 'F000011_11': 1}},
        }
        self._assert_expected_search(
            [PROJECT_2_VARIANT, MULTI_PROJECT_VARIANT1, MULTI_PROJECT_VARIANT2, VARIANT3, VARIANT4,
             GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            gene_counts=gene_counts, locus={'rawItems': 'chr1:1-100000000, chr13:1-100000000, chr14:1-100000000, chr16:1-100000000, chr17:1-100000000, M:1-100000000'},
        )

        self.results_model.families.set(Family.objects.filter(guid__in=['F000002_2', 'F000011_11', 'F000014_14']))
        self._assert_expected_search(
            [PROJECT_2_VARIANT, MULTI_PROJECT_VARIANT1, SV_VARIANT1, SV_VARIANT2, MULTI_PROJECT_VARIANT2, VARIANT3,
             VARIANT4, SV_VARIANT3, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, SV_VARIANT4, GCNV_VARIANT4, MITO_VARIANT1,
             MITO_VARIANT2, MITO_VARIANT3], gene_counts={**gene_counts, **SV_GENE_COUNTS},
        )

    def test_both_sample_types_search(self):
        Sample.objects.filter(dataset_type='MITO').update(is_active=False)

        # One family (F000011_11) in a multi-project search has identical exome and genome data.
        self._set_multi_project_search()
        self._add_sample_type_samples('WES', individual__family__guid='F000011_11')

        self._assert_expected_search(
            MULTI_PROJECT_BOTH_SAMPLE_TYPE_VARIANTS, gene_counts=GENE_COUNTS, locus={'rawItems': 'chr1:1-100000000'},
        )

        self._set_single_family_search()
        self._add_sample_type_samples('WGS', guid__in=['S000132_hg00731'])

        # Variant 1 is de novo in exome but inherited and homozygous in genome.
        # Variant 2 is inherited and homozygous in exome and de novo and homozygous in genome, so it fails de-novo inheritance when parental data is missing in genome.
        # Variant 3 is inherited in both sample types.
        # Variant 4 is de novo in exome, but inherited in genome in the same parent that has variant 3.
        self._assert_expected_search(
            [VARIANT1_BOTH_SAMPLE_TYPES, VARIANT2_BOTH_SAMPLE_TYPES, VARIANT3_BOTH_SAMPLE_TYPES, VARIANT4_BOTH_SAMPLE_TYPES,
             GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            inheritance_mode='any_affected', locus=None,
        )

        self._assert_expected_search(
            [VARIANT2_BOTH_SAMPLE_TYPES, VARIANT3_BOTH_SAMPLE_TYPES, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT4],
            inheritance_mode='any_affected', quality_filter={'min_gq': 40, 'min_qs': 20},
        )

        self._assert_expected_search(
            [VARIANT1_BOTH_SAMPLE_TYPES, VARIANT4_BOTH_SAMPLE_TYPES, GCNV_VARIANT1],
            inheritance_mode='de_novo', quality_filter=None,
        )

        self._add_sample_type_samples('WGS', guid__in=['S000133_hg00732', 'S000134_hg00733'])
        self._assert_expected_search(
            [VARIANT1_BOTH_SAMPLE_TYPES, VARIANT2_BOTH_SAMPLE_TYPES, VARIANT3_BOTH_SAMPLE_TYPES,
             VARIANT4_BOTH_SAMPLE_TYPES, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            inheritance_mode='any_affected',
        )

        self._assert_expected_search(
            [VARIANT1_BOTH_SAMPLE_TYPES, VARIANT2_BOTH_SAMPLE_TYPES, VARIANT4_BOTH_SAMPLE_TYPES, GCNV_VARIANT1],
            inheritance_mode='de_novo',
        )

        self._assert_expected_search(
            [VARIANT2_BOTH_SAMPLE_TYPES, GCNV_VARIANT1],
            inheritance_mode='de_novo', quality_filter={'min_gq': 40}
        )

        self.maxDiff = None
        self._assert_expected_search(
            [VARIANT1_BOTH_SAMPLE_TYPES, VARIANT2_BOTH_SAMPLE_TYPES,
             [{**VARIANT2_BOTH_SAMPLE_TYPES, 'selectedMainTranscriptId': 'ENST00000450625'}, GCNV_VARIANT4],
             [VARIANT3_BOTH_SAMPLE_TYPES, VARIANT4_BOTH_SAMPLE_TYPES],
             GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode='recessive', **COMP_HET_ALL_PASS_FILTERS, quality_filter=None, cached_variant_fields=[
                {}, {}, [{'selectedGeneId': 'ENSG00000277258'}, {'selectedGeneId': 'ENSG00000277258'}],
                [{'selectedGeneId':  'ENSG00000097046'}, {'selectedGeneId':  'ENSG00000097046'}], {},
                [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
            ]
        )

    @staticmethod
    def _add_sample_type_samples(sample_type, dataset_type=None, **sample_filter):
        for sample in Sample.objects.filter(**sample_filter):
            sample.pk = None
            sample.sample_type = sample_type
            if dataset_type:
                sample.dataset_type = dataset_type
            sample.save()

    def test_inheritance_filter(self):
        inheritance_mode = 'any_affected'
        self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3,
             GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            inheritance_mode=inheritance_mode,
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4], inheritance_mode=inheritance_mode,
        )

        self._assert_expected_search(
            [SV_VARIANT2], inheritance_mode=inheritance_mode, annotations=NEW_SV_FILTER,
        )

        self._reset_search_families()
        self._assert_expected_search(
            [GCNV_VARIANT3], inheritance_mode=inheritance_mode, annotations=NEW_SV_FILTER,
        )

        inheritance_mode = 'de_novo'
        self._assert_expected_search(
            [VARIANT1, FAMILY_3_VARIANT, VARIANT4, GCNV_VARIANT1, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            inheritance_mode=inheritance_mode, annotations=None,
        )

        self._set_sv_family_search()
        sv_affected = {'affected': {'I000019_na21987': 'N'}}
        self._assert_expected_search(
            [SV_VARIANT1], inheritance_mode=inheritance_mode, inheritance_filter=sv_affected,
        )

        inheritance_mode = 'x_linked_recessive'
        self._reset_search_families()
        self._assert_expected_search([], inheritance_mode=inheritance_mode)
        # self._assert_expected_search([], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA_WITH_SEX)

        inheritance_mode = 'homozygous_recessive'
        self._assert_expected_search(
            [VARIANT2, GCNV_VARIANT3, MITO_VARIANT3],
            inheritance_mode=inheritance_mode,
        )

        self._set_multi_project_search()
        self._assert_expected_search(
            [PROJECT_2_VARIANT1, VARIANT2, GCNV_VARIANT3, MITO_VARIANT3],
            inheritance_mode=inheritance_mode, locus={'rawItems': 'chr1:1-100000000, chr14:1-100000000, chr16:1-100000000, chr17:1-100000000, M:1-100000000'},
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT4], inheritance_mode=inheritance_mode, locus=None,
        )

        gt_inheritance_filter = {'genotype': {'I000006_hg00733': 'ref_ref', 'I000005_hg00732': 'has_alt'}}
        self._set_single_family_search()
        self._assert_expected_search([VARIANT2, GCNV_VARIANT3], inheritance_filter=gt_inheritance_filter)

        self._assert_expected_search(
            [VARIANT2, GCNV_VARIANT2, GCNV_VARIANT3], inheritance_mode='any_affected', inheritance_filter={'affected': {
                'I000004_hg00731': 'N', 'I000005_hg00732': 'A', 'I000006_hg00733': 'U',
            }},
        )

        inheritance_mode = 'compound_het'
        self._reset_search_families()
        self._assert_expected_search(
            [[VARIANT3, VARIANT4]], inheritance_mode=inheritance_mode, inheritance_filter={}, gene_counts={
                'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000177000': {'total': 1, 'families': {'F000002_2': 1}},
            }, **ALL_SNV_INDEL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId':  'ENSG00000097046'}, {'selectedGeneId':  'ENSG00000097046'}],
            ],
        )

        self._assert_expected_search(
            [[GCNV_VARIANT3, GCNV_VARIANT4]], inheritance_mode=inheritance_mode, gene_counts={
                'ENSG00000275023': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000277972': {'total': 1, 'families': {'F000002_2': 1}},
            }, cached_variant_fields=[
                [{'selectedGeneId':  'ENSG00000275023'}, {'selectedGeneId':  'ENSG00000275023'}],
            ], annotations={'structural': COMP_HET_ALL_PASS_FILTERS['annotations']['structural']}, pathogenicity=None,
        )

        self._assert_expected_search(
            [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, VARIANT4], [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode=inheritance_mode, gene_counts={
                'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000275023': {'total': 3, 'families': {'F000002_2': 3}},
                'ENSG00000277258': {'total': 3, 'families': {'F000002_2': 3}},
                'ENSG00000277972': {'total': 2, 'families': {'F000002_2': 2}},
            }, **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId':  'ENSG00000277258'}, {'selectedGeneId':  'ENSG00000277258'}],
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}],
                [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
            ]
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2]], inheritance_mode=inheritance_mode,
            **COMP_HET_ALL_PASS_FILTERS, gene_counts={'ENSG00000171621': {'total': 2, 'families': {'F000014_14': 2}}},
            inheritance_filter=sv_affected, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000171621'}, {'selectedGeneId': 'ENSG00000171621'}],
            ],
        )

        self.results_model.families.set(Family.objects.filter(guid__in=['F000002_2', 'F000014_14']))
        self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2], [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, VARIANT4], [GCNV_VARIANT3, GCNV_VARIANT4]], inheritance_mode=inheritance_mode,
            **COMP_HET_ALL_PASS_FILTERS, gene_counts={
                'ENSG00000171621': {'total': 2, 'families': {'F000014_14': 2}},
                'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000275023': {'total': 3, 'families': {'F000002_2': 3}},
                'ENSG00000277258': {'total': 3, 'families': {'F000002_2': 3}},
                'ENSG00000277972': {'total': 2, 'families': {'F000002_2': 2}},
            }, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000171621'}, {'selectedGeneId': 'ENSG00000171621'}],
                [{'selectedGeneId': 'ENSG00000277258'}, {'selectedGeneId': 'ENSG00000277258'}],
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}],
                [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
            ],
        )

        inheritance_mode = 'recessive'
        self._set_multi_project_search()
        self._assert_expected_search(
                [PROJECT_2_VARIANT1, VARIANT2, [VARIANT3, VARIANT4], MITO_VARIANT3], inheritance_mode=inheritance_mode, gene_counts={
                'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000198727': {'total': 1, 'families': {'F000002_2': 1}},
            }, cached_variant_fields=[
                {}, {},
                [{'selectedGeneId':  'ENSG00000097046'}, {'selectedGeneId':  'ENSG00000097046'}], {},
            ], **ALL_SNV_INDEL_PASS_FILTERS, locus={'rawItems': 'chr1:1-100000000, chr14:1-100000000, chr16:1-100000000, chr17:1-100000000, M:1-100000000'},
        )

        self._set_single_family_search()
        self._assert_expected_search(
            [VARIANT2, [VARIANT3, VARIANT4], MITO_VARIANT3], inheritance_mode=inheritance_mode, cached_variant_fields=[
                {},
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}], {},
            ], locus=None,
        )
        self._reset_search_families()

        self._assert_expected_search(
            [GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]], inheritance_mode=inheritance_mode, gene_counts={
                'ENSG00000275023': {'total': 3, 'families': {'F000002_2': 3}},
                'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000277972': {'total': 1, 'families': {'F000002_2': 1}},
            }, annotations={'structural': COMP_HET_ALL_PASS_FILTERS['annotations']['structural']}, pathogenicity=None,
            cached_variant_fields=[
                {}, [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
            ],
        )

        self._assert_expected_search(
            [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, VARIANT4], GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4], MITO_VARIANT3],
            inheritance_mode=inheritance_mode, gene_counts={
                'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000177000': {'total': 3, 'families': {'F000002_2': 3}},
                'ENSG00000275023': {'total': 4, 'families': {'F000002_2': 4}},
                'ENSG00000277258': {'total': 4, 'families': {'F000002_2': 4}},
                'ENSG00000277972': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000198727': {'total': 1, 'families': {'F000002_2': 1}},
            }, **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                {},
                [{'selectedGeneId':  'ENSG00000277258'}, {'selectedGeneId':  'ENSG00000277258'}],
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}],
                {},
                [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
                {},
            ],
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2], SV_VARIANT4], inheritance_mode=inheritance_mode,
            **COMP_HET_ALL_PASS_FILTERS, gene_counts={
                'ENSG00000171621': {'total': 2, 'families': {'F000014_14': 2}},
                'ENSG00000184986': {'total': 1, 'families': {'F000014_14': 1}},
            }, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000171621'}, {'selectedGeneId': 'ENSG00000171621'}], {},
            ],
        )

        # Test deletion in trans with hom alt snp/indel
        for sample in Sample.objects.filter(individual__family_id=14):
            sample.pk = None
            sample.dataset_type = 'SNV_INDEL'
            sample.save()
        self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2], [SV_VARIANT1, PROJECT_4_COMP_HET_VARIANT], PROJECT_4_COMP_HET_VARIANT, SV_VARIANT4],
            inheritance_mode=inheritance_mode, **COMP_HET_ALL_PASS_FILTERS,
            cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000171621'}, {'selectedGeneId': 'ENSG00000171621'}],
                [{'selectedGeneId': 'ENSG00000171621'}, {'selectedGeneId': 'ENSG00000171621'}],
                {}, {},
            ],
        )

        self._set_grch37_search()
        self._assert_expected_search([], inheritance_mode=inheritance_mode)
        self._assert_expected_search(
            [GRCH37_VARIANT], inheritance_mode=inheritance_mode, inheritance_filter={'allowNoCall': True},
        )

    def test_exclude_previous_search_results(self):
        VariantSearchResults.objects.create(variant_search_id=79516, search_hash='abc1234')
        self.mock_redis.get.side_effect = [None, json.dumps({'all_results': [
            VARIANT1, VARIANT2, [VARIANT3, VARIANT2], [GCNV_VARIANT4, GCNV_VARIANT3],
        ]})]
        self.mock_redis.keys.side_effect = [[], ['search_results__abc1234__gnomad']]

        self._assert_expected_search(
            [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, VARIANT4], GCNV_VARIANT3, MITO_VARIANT3],
            inheritance_mode='recessive', **COMP_HET_ALL_PASS_FILTERS,
            exclude={'previousSearch': True, 'previousSearchHash': 'abc1234'}, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000277258'}, {'selectedGeneId': 'ENSG00000277258'}],
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}],
                {}, {},
            ],
        )

        self.mock_redis.get.side_effect = [None, json.dumps({'all_results': [
            [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, VARIANT4], GCNV_VARIANT3, MITO_VARIANT3,
        ]})]
        self.mock_redis.keys.side_effect = [[], ['search_results__abc1234__gnomad']]
        self._assert_expected_search(
            [VARIANT2, [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode='recessive', cached_variant_fields=[
                {}, [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
            ],
        )

    def test_quality_filter(self):
        quality_filter = {'vcf_filter': 'pass'}
        self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2],
            quality_filter=quality_filter
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT4], quality_filter=quality_filter,
        )

        gcnv_quality_filter = {'min_gq': 40, 'min_qs': 20, 'min_hl': 5}
        self._reset_search_families()
        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT3], quality_filter=gcnv_quality_filter,
        )

        self._assert_expected_search(
            [], annotations=NEW_SV_FILTER, quality_filter=gcnv_quality_filter, omit_data_type='SNV_INDEL',
        )

        sv_quality_filter = {'min_gq_sv': 40}
        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT3, SV_VARIANT4], quality_filter=sv_quality_filter, annotations=None,
        )

        self._assert_expected_search(
            [], annotations=NEW_SV_FILTER, quality_filter=sv_quality_filter,
        )

        self._reset_search_families()
        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, MITO_VARIANT1, MITO_VARIANT2], quality_filter={'min_gq': 40, 'min_qs': 30, 'vcf_filter': 'pass'},
            annotations=None,
        )

        self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            quality_filter={'min_gq': 60, 'min_qs': 10, 'affected_only': True},
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT4], quality_filter={'min_gq_sv': 60, 'affected_only': True},
        )

        self._reset_search_families()
        self._assert_expected_search(
            [VARIANT1, VARIANT2, FAMILY_3_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4,MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], quality_filter={'min_ab': 50},
        )

        self._assert_expected_search(
            [VARIANT2, VARIANT3, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], quality_filter={'min_ab': 70, 'affected_only': True},
        )

        quality_filter.update({'min_gq': 40, 'min_ab': 50, 'min_hl': 5})
        self._assert_expected_search(
            [VARIANT2, FAMILY_3_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1], quality_filter=quality_filter,
        )

        # Ensure no variants are filtered out by annotation/path filters
        annotations = {'splice_ai': '0.0', 'consequences': ['non_coding_transcript_exon_variant', 'missense_variant', 'synonymous_variant']}
        selected_family_3_variant = {**FAMILY_3_VARIANT, 'selectedMainTranscriptId': 'ENST00000497611'}
        cached_variant_fields = [
            {'selectedTranscript': None},
            {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][0]},
            {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][3]},
            {},
            {},
        ]

        quality_filter['min_gq'] = 50
        self._assert_expected_search(
            [VARIANT1, selected_family_3_variant, MITO_VARIANT1, MITO_VARIANT3], quality_filter=quality_filter,
            annotations=annotations, pathogenicity={'clinvar': ['likely_pathogenic', 'vus_or_conflicting']},
            cached_variant_fields=cached_variant_fields[:1] + cached_variant_fields[2:],
        )

        pathogenicity = {'clinvar': ['likely_pathogenic', 'conflicting_p_lp', 'vus_or_conflicting']}
        self._assert_expected_search(
            [VARIANT1, VARIANT2, selected_family_3_variant, MITO_VARIANT1, MITO_VARIANT3], quality_filter=quality_filter,
            annotations=annotations, pathogenicity=pathogenicity,
            cached_variant_fields=cached_variant_fields,
        )

        self._assert_expected_search(
            [VARIANT2, selected_family_3_variant, MITO_VARIANT1],  quality_filter=quality_filter,
            annotations=annotations, pathogenicity={**pathogenicity, 'clinvarMinStars': 1},
            cached_variant_fields=cached_variant_fields[1:],
        )

        self._assert_expected_search(
            [VARIANT2, selected_family_3_variant, MITO_VARIANT1], quality_filter=quality_filter,
            annotations=annotations, pathogenicity={'clinvar': ['pathogenic', 'conflicting_p_lp']}, cached_variant_fields=cached_variant_fields[1:],
        )

        self._set_grch37_search()
        quality_filter = {'min_gq': 1, 'min_ab': 10}
        self._assert_expected_search([], quality_filter=quality_filter, annotations=None, pathogenicity=None)
        self._assert_expected_search(
            [GRCH37_VARIANT], quality_filter=quality_filter, inheritance_filter={'allowNoCall': True},
        )

    def test_location_search(self):
        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4], **LOCATION_SEARCH, cached_variant_fields=[
                {'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}
            ],
        )

        sv_locus = {'rawItems': 'ENSG00000275023, ENSG00000171621'}
        self._assert_expected_search(
            [GCNV_VARIANT3, GCNV_VARIANT4], locus=sv_locus,
        )

        self._set_sv_family_search()
        # For gene search, return SVs annotated in gene even if they fall outside the gene interval
        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2], locus=sv_locus,
        )
        self._assert_expected_search(
            [SV_VARIANT1], locus={'rawItems': 'chr1:9297894-9369732%10'}
        )

        self._reset_search_families()
        self._assert_expected_search(
            [VARIANT1, VARIANT2, GCNV_VARIANT1, GCNV_VARIANT2, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], exclude={
                'rawItems': ','.join([LOCATION_SEARCH['locus']['rawItems'], sv_locus['rawItems']])
            }, locus=None,
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT2, SV_VARIANT3], exclude=sv_locus,
        )

        self._reset_search_families()
        self._assert_expected_search(
            [SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT, VARIANT4],
            locus={'rawItems': f'{GENE_IDS[1]}\n1:91500851-91525764'}, exclude=None, cached_variant_fields=[
                {'selectedGeneId': 'ENSG00000177000'}, {'selectedGeneId': None},
            ],
        )

        self._add_sample_type_samples('WES', individual__family__guid='F000014_14')
        self.results_model.families.set(Family.objects.filter(guid__in=['F000002_2', 'F000014_14']))
        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2, MULTI_PROJECT_GCNV_VARIANT3, GCNV_VARIANT4], locus=sv_locus,
        )

        self._set_grch37_search()
        self._assert_expected_search([GRCH37_VARIANT], locus={'rawItems': '7:143268894-143271480'})

    def test_variant_id_search(self):
        self._assert_expected_search([VARIANT2], locus={'rawVariantItems': 'rs1801131'})

        self._assert_expected_search([VARIANT1], **VARIANT_ID_SEARCH)

        self._assert_expected_search(
            [VARIANT1], locus={'rawVariantItems': VARIANT_IDS[0]},
        )

        self._assert_expected_search(
            [],locus={'rawVariantItems': VARIANT_IDS[1]},
        )

    @mock.patch('clickhouse_search.search.MAX_VARIANTS', 3)
    def test_invalid_search(self):
        with self.assertRaises(InvalidSearchException) as cm:
            self._assert_expected_search([])
        self.assertEqual(str(cm.exception),'This search returned too many results')

        Sample.objects.filter(guid='S000143_na20885').update(sample_id='HG00732')
        self._set_multi_project_search()
        with self.assertRaises(InvalidSearchException) as cm:
            self._assert_expected_search([], locus={'rawItems': GENE_IDS[0]})
        self.assertEqual(
            str(cm.exception),
            'The following samples are incorrectly configured and have different affected statuses in different projects: '
            'HG00732 (1kg project nåme with uniçøde/ Test Reprocessed Project)',
        )

    @mock.patch('seqr.utils.search.utils.LiftOver')
    def test_variant_lookup(self, mock_liftover):
        mock_convert_coordinate = mock_liftover.return_value.convert_coordinate
        mock_convert_coordinate.side_effect = lambda chrom, pos: [(chrom, pos + 10000)]

        variants = variant_lookup(self.user, '1-10439-AC-A', '38')
        self._assert_expected_variants(variants, [VARIANT_LOOKUP_VARIANT])

        with self.assertRaises(ObjectDoesNotExist) as cm:
            variant_lookup(self.user, '1-91511686-TCA-G', '38')
        self.assertEqual(str(cm.exception), 'Variant not present in seqr')

        variants = variant_lookup(self.user, '7-143270172-A-G', '37')
        grch37_lookup_variant = {
            **{k: v for k, v in GRCH37_VARIANT.items() if k not in {'familyGuids', 'genotypes'}},
            'familyGenotypes': {GRCH37_VARIANT['familyGuids'][0]: sorted([
                {k: v for k, v in g.items() if k != 'individualGuid'} for g in GRCH37_VARIANT['genotypes'].values()
            ], key=lambda x: x['sampleId'], reverse=True)},
        }
        self._assert_expected_variants(variants, [grch37_lookup_variant])

        # Lookup works if variant is only present on a different build
        variants = variant_lookup(self.user, '7-143260172-A-G', '38')
        self._assert_expected_variants(variants, [grch37_lookup_variant])
        mock_liftover.assert_called_with('hg38', 'hg19')
        mock_convert_coordinate.assert_called_with('chr7', 143260172)

        variants = variant_lookup(self.user, 'M-4429-G-A', '38')
        self._assert_expected_variants(variants, [{
            **{k: v for k, v in MITO_VARIANT1.items() if k not in {'familyGuids', 'genotypes'}},
            'familyGenotypes': {MITO_VARIANT1['familyGuids'][0]: [
                {k: v for k, v in g.items() if k != 'individualGuid'} for g in MITO_VARIANT1['genotypes'].values()
            ]},
        }])

        variants = variant_lookup(self.user, 'phase2_DEL_chr14_4640', '38', sample_type='WGS')
        self._assert_expected_variants(variants, [SV_LOOKUP_VARIANT, GCNV_LOOKUP_VARIANT])

        # reciprocal overlap does not meet the threshold for smaller events
        variants = variant_lookup(self.user, 'suffix_140608_DUP', '38', sample_type='WES')
        self._assert_expected_variants(variants, [GCNV_LOOKUP_VARIANT])

        variants = variant_lookup(self.user, 'suffix_140593_DUP', '38', sample_type='WES')
        self._assert_expected_variants(variants, [GCNV_LOOKUP_VARIANT_3])

    def test_get_single_variant(self):
        self._set_single_family_search()
        variant = get_single_variant(self.results_model.families.first(), VARIANT_IDS[0])
        self._assert_expected_variants([variant], [VARIANT1])

        with self.assertRaises(InvalidSearchException) as cm:
            get_single_variant(self.results_model.families.first(), VARIANT_IDS[1])
        self.assertEqual(str(cm.exception), 'Variant 1-91511686-TCA-G not found')

        variant = get_single_variant(self.results_model.families.first(), 'M-4429-G-A')
        self._assert_expected_variants([variant], [MITO_VARIANT1])

        variant = get_single_variant(self.results_model.families.first(), 'suffix_140608_DUP')
        self._assert_expected_variants([variant], [GCNV_VARIANT4])

        self._set_sv_family_search()
        variant = get_single_variant(self.results_model.families.first(), 'phase2_DEL_chr14_4640')
        self._assert_expected_variants([variant], [SV_VARIANT4])

        self._set_grch37_search()
        variant = get_single_variant(self.results_model.families.first(), '7-143270172-A-G')
        self._assert_expected_variants([variant], [GRCH37_VARIANT])


    def test_frequency_filter(self):
        sv_callset_filter = {'sv_callset': {'af': 0.05}}
        # seqr af filter is ignored for SNV_INDEL
        self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            freqs={'callset': {'af': 0.2},  **sv_callset_filter},
        )

        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            freqs={'callset': {'ac': 7}, **sv_callset_filter},
        )

        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], freqs={'callset': {'hh': 1}},
        )

        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, GCNV_VARIANT3, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], freqs={'callset': {'ac': 7, 'hh': 0}, 'sv_callset': {'ac': 50}},
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT1], freqs={'sv_callset': {'ac': 1}},
        )

        self._reset_search_families()
        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2], freqs={'gnomad_genomes': {'af': 0.03}, 'gnomad_mito': {'af': 0.05}},
        )

        self._assert_expected_search(
            [VARIANT2, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2], freqs={'gnomad_genomes': {'af': 0.05, 'hh': 0}, 'gnomad_mito': {'af': 0.05}},
        )

        self._assert_expected_search(
            [VARIANT4, GCNV_VARIANT3, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            freqs={'topmed': {'af': 0.05, 'hh': 1}, 'sv_callset': {'ac': 50}},
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT3, SV_VARIANT4], freqs={'gnomad_svs': {'af': 0.001}},
        )
        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT3, SV_VARIANT4], freqs={'gnomad_svs': {'ac': 4000}},
        )

        self._reset_search_families()
        self._assert_expected_search(
            [VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2],
            freqs={'callset': {'ac': 6}, 'gnomad_genomes': {'ac': 50}, 'gnomad_mito': {'ac': 10}},
        )

        self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            freqs={'callset': {}, 'gnomad_genomes': {'af': None}},
        )

        annotations = {'splice_ai': '0.0'}  # Ensures no variants are filtered out by annotation/path filters
        self._assert_expected_search(
            [VARIANT1, VARIANT4, MITO_VARIANT1],
            freqs={'gnomad_genomes': {'af': 0.002, 'hh': 10}, 'gnomad_mito': {'af': 0.01}},
            annotations=annotations, pathogenicity={'clinvar': ['pathogenic', 'likely_pathogenic', 'vus']},
        )

        self._assert_expected_search(
            [VARIANT2, VARIANT4, MITO_VARIANT1], freqs={'gnomad_genomes': {'af': 0.002}, 'gnomad_mito': {'af': 0.01}},
            annotations=annotations, pathogenicity={'clinvar': ['pathogenic', 'conflicting_p_lp', 'vus']},
        )

    def test_annotations_filter(self):
        self._assert_expected_search([VARIANT2], pathogenicity={'hgmd': ['hgmd_other']})
        self._assert_expected_search([], pathogenicity={'hgmd': ['disease_causing', 'likely_disease_causing']})

        clinvar_paths = ['likely_pathogenic', 'conflicting_p_lp', 'conflicting_no_p', 'vus', 'benign']
        pathogenicity = {'clinvar': clinvar_paths, 'hgmd': []}
        self._assert_expected_search(
            [VARIANT1, VARIANT2, MITO_VARIANT1, MITO_VARIANT3], pathogenicity=pathogenicity,
        )

        self._assert_expected_search(
            [VARIANT2, MITO_VARIANT1], pathogenicity={**pathogenicity, 'clinvarMinStars': 1},
        )

        self._assert_expected_search([VARIANT2], pathogenicity={'clinvar': ['conflicting_p_lp']})
        self._assert_expected_search([], pathogenicity={'clinvar': ['conflicting_no_p']})

        exclude = {'clinvar': clinvar_paths[2:]}
        pathogenicity['clinvar'] = clinvar_paths[:2]
        snv_38_only_annotations = {'SCREEN': ['CTCF-only', 'DNase-only'], 'UTRAnnotator': ['5_prime_UTR_stop_codon_loss_variant']}
        selected_transcript_variant_2 = {**VARIANT2, 'selectedMainTranscriptId': 'ENST00000408919'}
        self._assert_expected_search(
            [VARIANT1, selected_transcript_variant_2, VARIANT4, MITO_VARIANT3], exclude=exclude, pathogenicity=pathogenicity, annotations=snv_38_only_annotations,
            cached_variant_fields=[
                {'selectedTranscript': None},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][1]},
                {'selectedTranscript': None},
                {},
            ]
        )

        exclude['clinvar'] = clinvar_paths[1:]
        pathogenicity['clinvar'] = clinvar_paths[:1]
        self._assert_expected_search(
            [VARIANT1, VARIANT4, MITO_VARIANT3], exclude=exclude, pathogenicity=pathogenicity,
            annotations=snv_38_only_annotations, cached_variant_fields=[
                {'selectedTranscript': None}, {'selectedTranscript': None}, {},
            ]
        )

        annotations = {
            'missense': ['missense_variant'], 'in_frame': ['inframe_insertion', 'inframe_deletion'], 'frameshift': None,
        }
        self._assert_expected_search(
            [VARIANT1, VARIANT2, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4, MITO_VARIANT2, MITO_VARIANT3], pathogenicity=pathogenicity,
            annotations=annotations, exclude=None, cached_variant_fields=[
                {'selectedTranscript': None},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][0]},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][1]},
                {}, {},
            ]
        )

        annotations['structural_consequence'] = ['INTRONIC', 'LOF']
        self._assert_expected_search(
            [VARIANT2, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT2], annotations=annotations, pathogenicity=None,
            cached_variant_fields = [
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][0]},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][1]},
                {}, {}, {},
            ],
        )

        self._set_sv_family_search()
        self._assert_expected_search([SV_VARIANT1], annotations=annotations)

        annotations['splice_ai'] = '0.005'
        annotations['structural'] = ['gCNV_DUP', 'DEL']
        self._reset_search_families()
        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT2],
            annotations=annotations, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][0]},
                {'selectedTranscript': None},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][1]},
                {}, {}, {}, {}, {},
            ]
        )

        self._set_sv_family_search()
        self._assert_expected_search([SV_VARIANT1, SV_VARIANT4], annotations=annotations)

        annotations = {'other': ['non_coding_transcript_exon_variant__canonical', 'non_coding_transcript_exon_variant']}
        self._set_single_family_search()
        self._assert_expected_search(
            [VARIANT1, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_3, MITO_VARIANT1, MITO_VARIANT3],
            pathogenicity=pathogenicity, annotations=annotations, cached_variant_fields=[
                {'selectedTranscript': None},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][5]},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][3]},
                {}, {},
            ],
        )
        self._reset_search_families()

        self._assert_expected_search(
            [SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2],
            locus={'rawItems': f'{GENE_IDS[1]}\n1:11785723-91525764'}, pathogenicity=None, annotations=annotations,
            cached_variant_fields=[{
                'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][5],
            }],
        )

        annotations['other'].append('intron_variant')
        self._assert_expected_search(
            [SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT],
            annotations=annotations,  cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][5]},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][1]},
            ],
        )

        annotations['other'] = annotations['other'][:1]
        annotations['splice_ai'] = '0.005'
        self._set_single_family_search()
        self._assert_expected_search(
            [VARIANT1, VARIANT3, MITO_VARIANT1, MITO_VARIANT3],
            pathogenicity=pathogenicity, annotations=annotations, locus=None, cached_variant_fields=[
                {'selectedTranscript': None}, {'selectedTranscript': None}, {}, {},
            ],
        )

        annotations['extended_splice_site'] = ['extended_intronic_splice_region_variant']
        self._assert_expected_search(
            [VARIANT1, VARIANT3, VARIANT4, MITO_VARIANT1, MITO_VARIANT3],
            pathogenicity=pathogenicity, annotations=annotations, cached_variant_fields=[
                {'selectedTranscript': None},
                {'selectedTranscript': None},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][0]},
                {}, {},
            ],
        )

        annotations = {'extended_splice_site': ['5_prime_UTR_variant']}
        self._assert_expected_search(
            [selected_transcript_variant_2], pathogenicity=None, annotations=annotations, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][1]},
            ],
        )

        annotations['extended_splice_site'].append('extended_intronic_splice_region_variant')
        self._assert_expected_search(
            [selected_transcript_variant_2, VARIANT4], annotations=annotations, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][1]},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][0]},
            ],
        )

        annotations = {'motif_feature': ['TF_binding_site_variant'], 'regulatory_feature': ['regulatory_region_variant']}
        self._assert_expected_search(
            [VARIANT3, VARIANT4], annotations=annotations, pathogenicity=None,
        )

        self._set_grch37_search()
        self._assert_expected_search([], pathogenicity=pathogenicity, annotations=snv_38_only_annotations)
        annotations['missense'] = ['missense_variant']
        self._assert_expected_search(
            [GRCH37_VARIANT], pathogenicity=None, annotations=annotations,
            cached_variant_fields=[{'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[11][0]}],
        )

    def test_secondary_annotations_filter(self):
        annotations_1 = {'missense': ['missense_variant']}
        annotations_2 = {'other': ['intron_variant']}

        comp_het_cached_fields = [
            {'selectedGeneId':  'ENSG00000097046', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][0]},
            {'selectedGeneId':  'ENSG00000097046', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][1]},
        ]

        self._assert_expected_search(
            [[VARIANT3, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4]], inheritance_mode='compound_het',
            annotations=annotations_1, annotations_secondary=annotations_2, cached_variant_fields=[comp_het_cached_fields],
        )

        self._assert_expected_search(
            [VARIANT2, [VARIANT3, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4]], inheritance_mode='recessive',
            annotations=annotations_1, annotations_secondary=annotations_2, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][0]}, comp_het_cached_fields
            ],
        )

        self._assert_expected_search(
            [[VARIANT3, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4]], inheritance_mode='recessive',
            annotations=annotations_2, annotations_secondary=annotations_1, cached_variant_fields=[comp_het_cached_fields],
        )

        gcnv_annotations_1 = {'structural': ['gCNV_DUP']}
        gcnv_annotations_2 = {'structural_consequence': ['LOF'], 'structural': []}

        self._assert_expected_search(
            [[GCNV_VARIANT3, GCNV_VARIANT4]], inheritance_mode='compound_het',
            annotations=gcnv_annotations_1, annotations_secondary=gcnv_annotations_2,
            cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
            ],
        )

        self._assert_expected_search(
            [GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]], inheritance_mode='recessive',
            annotations=gcnv_annotations_2, annotations_secondary=gcnv_annotations_1,
            cached_variant_fields=[
                {}, [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
            ],
        )

        # Do not return pairs where annotations match in a non-paired gene
        gcnv_annotations_no_pair = {'structural_consequence': ['COPY_GAIN']}
        self._assert_expected_search(
            [], inheritance_mode='compound_het',
            annotations=gcnv_annotations_1, annotations_secondary=gcnv_annotations_no_pair,
        )

        self._assert_expected_search(
            [], inheritance_mode='compound_het',
            annotations={**gcnv_annotations_1, **gcnv_annotations_no_pair},
        )

        self._assert_expected_search(
            [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4]], inheritance_mode='compound_het',
            annotations=annotations_1, annotations_secondary=gcnv_annotations_2, cached_variant_fields=[[
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]},
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': {'geneId': 'ENSG00000277258', 'majorConsequence': 'LOF'}},
            ]],
        )

        self._assert_expected_search(
            [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4], GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode='recessive',
            annotations={**annotations_1, **gcnv_annotations_1}, annotations_secondary={**annotations_2, **gcnv_annotations_2}, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][0]}, [
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]},
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': {'geneId': 'ENSG00000277258', 'majorConsequence': 'LOF'}},
            ], [
                {'selectedGeneId':  'ENSG00000097046', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][0]},
                {'selectedGeneId':  'ENSG00000097046', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][1]},
            ], {}, [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}]],
        )

        self._assert_expected_search(
            [MULTI_DATA_TYPE_COMP_HET_VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode='recessive',
            annotations={**annotations_1, 'structural': ['gCNV_DEL'], 'structural_consequence': ['INTRONIC']},
            annotations_secondary={**annotations_2, **gcnv_annotations_1},
            locus={'rawItems': 'ENSG00000277258,ENSG00000275023'}, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]}, [
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]},
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': None},
            ], [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}]],
        )

        self._assert_expected_search(
            [MULTI_DATA_TYPE_COMP_HET_VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4]],
            inheritance_mode='recessive', annotations={**annotations_1, 'structural': [], 'structural_consequence': []},
            annotations_secondary=gcnv_annotations_2, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]}, [
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]},
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': {'geneId': 'ENSG00000277258', 'majorConsequence': 'LOF'}},
            ]],
        )

        sv_annotations_1 = {'structural': ['INS', 'LOF']}
        sv_annotations_2 = {'structural': ['DEL', 'gCNV_DUP'], 'structural_consequence': ['INTRONIC']}

        self._set_sv_family_search()
        self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2]], inheritance_mode='compound_het', locus=None,
            annotations=sv_annotations_1, annotations_secondary=sv_annotations_2, inheritance_filter={'affected': {
                'I000019_na21987': 'N',
            }}, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000171621'}, {'selectedGeneId': 'ENSG00000171621'}],
            ],
        )

        self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2], SV_VARIANT4], inheritance_mode='recessive',
            annotations=sv_annotations_2, annotations_secondary=sv_annotations_1, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000171621'}, {'selectedGeneId': 'ENSG00000171621'}], {},
            ],
        )

        pathogenicity = {'clinvar': ['likely_pathogenic', 'conflicting_p_lp', 'conflicting_no_p', 'vus']}
        self._reset_search_families()
        self._assert_expected_search(
            [VARIANT2, [VARIANT3, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4], MITO_VARIANT3], inheritance_mode='recessive',
            annotations=annotations_2, annotations_secondary=annotations_1, pathogenicity=pathogenicity, cached_variant_fields=[
                {'selectedTranscript': None},
                comp_het_cached_fields,
                {},
            ],
        )

        self._assert_expected_search(
            [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode='compound_het', pathogenicity=pathogenicity,
            annotations=gcnv_annotations_2, annotations_secondary=gcnv_annotations_1, cached_variant_fields=[[
                {'selectedGeneId': 'ENSG00000277258'},
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': {'geneId': 'ENSG00000277258', 'majorConsequence': 'LOF'}},
            ], [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}]],
        )

        self._assert_expected_search(
            [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4], MITO_VARIANT3],
            inheritance_mode='recessive', pathogenicity=pathogenicity,
            annotations=gcnv_annotations_2, annotations_secondary=gcnv_annotations_1, cached_variant_fields=[{}, [
                {'selectedGeneId': 'ENSG00000277258'},
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': {'geneId': 'ENSG00000277258', 'majorConsequence': 'LOF'}},
            ], {}, [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}], {}],
        )

        selected_transcript_annotations = {'other': ['non_coding_transcript_exon_variant']}
        self._assert_expected_search(
            [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], GCNV_VARIANT3, MITO_VARIANT3],
            inheritance_mode='recessive', pathogenicity=pathogenicity,
            annotations=gcnv_annotations_2, annotations_secondary=selected_transcript_annotations, cached_variant_fields=[{}, [
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': None},
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': {'geneId': 'ENSG00000277258', 'majorConsequence': 'LOF'}},
            ], {}, {}],
        )

        # Do not return pairs where annotations match in a non-paired gene
        self._assert_expected_search(
            [GCNV_VARIANT3], inheritance_mode='recessive', pathogenicity=None,
            annotations=gcnv_annotations_2, annotations_secondary=selected_transcript_annotations,
        )

        screen_annotations = {'SCREEN': ['CTCF-only']}
        self._assert_expected_search(
            [], inheritance_mode='recessive',
            annotations=screen_annotations, annotations_secondary=annotations_1, pathogenicity=None,
        )

        self._assert_expected_search(
            [[VARIANT3, VARIANT4]], inheritance_mode='recessive',
            annotations=screen_annotations, annotations_secondary=annotations_2, cached_variant_fields=[
                [{'selectedGeneId':  'ENSG00000097046', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][0]}, {'selectedGeneId':  'ENSG00000097046'}],
            ],
        )

        self._assert_expected_search(
            [VARIANT2, [SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_3, VARIANT4], MITO_VARIANT3], inheritance_mode='recessive',
            annotations=screen_annotations, annotations_secondary=selected_transcript_annotations,
            pathogenicity=pathogenicity, cached_variant_fields=[
                {}, [
                    {'selectedGeneId':  'ENSG00000097046', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][3]},
                    {'selectedGeneId':  'ENSG00000097046'},
                ], {},
            ],
        )

        self._assert_expected_search(
            [SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, [VARIANT3, VARIANT4], MITO_VARIANT3],
            annotations={**selected_transcript_annotations, **screen_annotations}, annotations_secondary=annotations_2,
            inheritance_mode='recessive', cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][5]}, [
                    {'selectedGeneId': 'ENSG00000097046', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][0]},
                    {'selectedGeneId': 'ENSG00000097046', 'selectedTranscript': None},
                ], {},
            ],
        )

        self._add_sample_type_samples('WES', individual__family__guid='F000014_14')
        self.results_model.families.set(Family.objects.filter(guid__in=['F000002_2', 'F000011_11', 'F000014_14']))
        self._assert_expected_search(
            [MULTI_DATA_TYPE_COMP_HET_VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], MULTI_PROJECT_GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode='recessive',
            annotations={**annotations_1, **gcnv_annotations_1}, annotations_secondary={**annotations_2, **gcnv_annotations_2},
            locus={'rawItems': 'ENSG00000277258,ENSG00000275023'}, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]}, [
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]},
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': {'geneId': 'ENSG00000277258', 'majorConsequence': 'LOF'}},
            ], {}, [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}]],
        )

        # Search works with a different number of samples within the family
        self._reset_search_families()
        missing_gt_gcnv_variant = {
            **GCNV_VARIANT4,
            'familyGuids': ['F000002_2_x'],
            'genotypes': {k: {**v, 'familyGuid': 'F000002_2_x'} for k, v in GCNV_VARIANT4['genotypes'].items() if k != 'I000005_hg00732'}
        }
        missing_gt_comp_het_variant = {
            **MULTI_DATA_TYPE_COMP_HET_VARIANT2,
            'familyGuids': ['F000002_2_x'],
            'genotypes': {k: {**v, 'familyGuid': 'F000002_2_x'} for k, v in MULTI_DATA_TYPE_COMP_HET_VARIANT2['genotypes'].items()}
        }
        Sample.objects.filter(guid='S000146_hg00732').update(is_active=False)
        Family.objects.filter(guid='F000002_2').update(guid='F000002_2_x')
        self._assert_expected_search(
            [[missing_gt_comp_het_variant, missing_gt_gcnv_variant]],
            inheritance_mode='compound_het', pathogenicity=pathogenicity, locus=None,
            annotations=gcnv_annotations_2, annotations_secondary=selected_transcript_annotations, cached_variant_fields=[[
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': None},
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': {'geneId': 'ENSG00000277258', 'majorConsequence': 'LOF'}},
            ]],
        )

    def test_in_silico_filter(self):
        main_in_silico = {'eigen': '3.5', 'mut_taster': 'N', 'vest': 0.5}
        self._assert_expected_search(
           [VARIANT1, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], in_silico=main_in_silico,
        )

        in_silico = {**main_in_silico, 'requireScore': True}
        in_silico.pop('eigen')
        self._assert_expected_search(
           [VARIANT4, MITO_VARIANT2], in_silico=in_silico,
        )

        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT], in_silico={'gnomad_noncoding': 0.5, 'requireScore': True},
        )

        self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            in_silico={'alphamissense': 0.5},
        )
        self._assert_expected_search([VARIANT2], in_silico={'alphamissense': 0.5, 'requireScore': True})

        sv_in_silico = {'strvctvre': 0.1, 'requireScore': True}
        self._assert_expected_search(
            [GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], in_silico=sv_in_silico,
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT4], in_silico=sv_in_silico,
        )

        self._set_grch37_search()
        self._assert_expected_search([GRCH37_VARIANT], in_silico=main_in_silico)

    def test_sort(self):
        self._set_single_family_search()
        self._assert_expected_search(
            [VARIANT4, GCNV_VARIANT3, GCNV_VARIANT4, GCNV_VARIANT2, GCNV_VARIANT1, VARIANT2, MITO_VARIANT2, MITO_VARIANT3, MITO_VARIANT1, VARIANT3, VARIANT1],
            sort='protein_consequence',
        )
        self._reset_search_families()

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4],
             sort='protein_consequence',
        )

        self._reset_search_families()
        self._assert_expected_search(
            [VARIANT4, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, MITO_VARIANT1, SELECTED_ANNOTATION_TRANSCRIPT_MULTI_FAMILY_VARIANT],
            sort='protein_consequence',
            annotations={'other': ['non_coding_transcript_exon_variant'], 'splice_ai': '0'}, cached_variant_fields=[
                {'selectedTranscript': None},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][5]},
                {},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][3]},
            ],
        )

        self._assert_expected_search(
            [VARIANT1, MITO_VARIANT3, VARIANT2, MITO_VARIANT1, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT2], sort='pathogenicity', annotations=None,
        )

        self._set_single_family_search()
        self._assert_expected_search(
            [VARIANT1, MITO_VARIANT3, VARIANT2, MITO_VARIANT1, VARIANT3, VARIANT4,  GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT2],
            sort='pathogenicity_hgmd',
        )

        self._assert_expected_search(
            [MITO_VARIANT1, MITO_VARIANT2, VARIANT4, VARIANT2, VARIANT3, VARIANT1, MITO_VARIANT3, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            sort='gnomad',
        )

        self._reset_search_families()
        self._assert_expected_search(
            [VARIANT1, MULTI_FAMILY_VARIANT, VARIANT4, VARIANT2, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            sort='gnomad_exomes',
        )

        self._assert_expected_search(
            [MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3, VARIANT4, MULTI_FAMILY_VARIANT, VARIANT1, VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, GCNV_VARIANT2, GCNV_VARIANT1],
            sort='callset_af',
        )

        self._assert_expected_search(
            [VARIANT4, MULTI_FAMILY_VARIANT, VARIANT2, VARIANT1, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            sort='cadd',
        )

        self._assert_expected_search(
            [VARIANT4, VARIANT2, VARIANT1, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='revel',
        )

        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT2, VARIANT4, VARIANT1, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='splice_ai',
        )

        self._assert_expected_search(
            [VARIANT2, VARIANT4, VARIANT1, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='alphamissense',
        )

        sort = 'in_omim'
        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT2, VARIANT4, GCNV_VARIANT3, GCNV_VARIANT4, VARIANT1, GCNV_VARIANT1, GCNV_VARIANT2, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort=sort
        )

        Omim.objects.filter(gene_id=61).delete()
        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT3, GCNV_VARIANT4, VARIANT1, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort=sort,
        )

        sort = 'constraint'
        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT3, GCNV_VARIANT4, VARIANT4, VARIANT1, GCNV_VARIANT1, GCNV_VARIANT2, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort=sort,
        )

        self._set_single_family_search()
        self._assert_expected_search([VARIANT2, VARIANT3, VARIANT1, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='prioritized_gene')

        self._set_multi_project_search()
        self._assert_expected_search(
            [MULTI_PROJECT_VARIANT1, MULTI_PROJECT_VARIANT2, VARIANT3, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3, PROJECT_2_VARIANT],
            sort='family_guid', locus={'rawItems': 'chr1:1-100000000, chr14:1-100000000, chr16:1-100000000, chr17:1-100000000, M:1-100000000'},
        )

        # size sort only applies to SVs, so has no impact on other variant
        self._reset_search_families()
        self._assert_expected_search(
            [GCNV_VARIANT1, GCNV_VARIANT4, GCNV_VARIANT2, GCNV_VARIANT3, VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='size', locus=None,
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT4, SV_VARIANT1, SV_VARIANT3, SV_VARIANT2], sort='size',
        )

        # sort applies to compound hets
        self._set_single_family_search()
        self._assert_expected_search(
            [[VARIANT4, VARIANT3], VARIANT2, MITO_VARIANT3],
            sort='revel', inheritance_mode='recessive', **ALL_SNV_INDEL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId':  'ENSG00000097046'}, {'selectedGeneId':  'ENSG00000097046'}], {}, {},
            ],
        )

        self._assert_expected_search(
            [[VARIANT3, VARIANT4], VARIANT2, MITO_VARIANT3],
            sort='splice_ai', inheritance_mode='recessive', **ALL_SNV_INDEL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId':  'ENSG00000097046'}, {'selectedGeneId':  'ENSG00000097046'}], {}, {},
            ],
        )

        self._assert_expected_search(
            [MITO_VARIANT3, [VARIANT4, VARIANT3], VARIANT2],
            sort='callset_af', inheritance_mode='recessive', **ALL_SNV_INDEL_PASS_FILTERS, cached_variant_fields=[
                {}, [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}], {},
            ],
        )

    def test_multi_data_type_comp_het_sort(self):
        self._assert_expected_search(
            [[VARIANT4, VARIANT3], GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4],
             [GCNV_VARIANT4, MULTI_DATA_TYPE_COMP_HET_VARIANT2], VARIANT2, MITO_VARIANT3],
            sort='protein_consequence', inheritance_mode='recessive', **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}], {},
                [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
                [{'selectedGeneId': 'ENSG00000277258'}, {'selectedGeneId': 'ENSG00000277258'}], {}, {}]
        )

        self._assert_expected_search(
            [[GCNV_VARIANT4, GCNV_VARIANT3], [GCNV_VARIANT4, MULTI_DATA_TYPE_COMP_HET_VARIANT2],
             [VARIANT3, VARIANT4]],
            sort='size', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
                [{'selectedGeneId': 'ENSG00000277258'}, {'selectedGeneId': 'ENSG00000277258'}],
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}],

            ]
        )

        self._assert_expected_search(
            [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4],
             [VARIANT3, VARIANT4], [GCNV_VARIANT3, GCNV_VARIANT4]],
            sort='pathogenicity', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000277258'}, {'selectedGeneId': 'ENSG00000277258'}],
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}],
                [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
            ]
        )

        self._assert_expected_search(
            [[VARIANT4, VARIANT3], VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4],
             GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4], MITO_VARIANT3],
            sort='mpc', inheritance_mode='recessive', **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}], {},
                [{'selectedGeneId': 'ENSG00000277258'}, {'selectedGeneId': 'ENSG00000277258'}], {},
                [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}], {},
            ]
        )

        self._assert_expected_search(
            [[VARIANT3, VARIANT4], [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4],
             [GCNV_VARIANT3, GCNV_VARIANT4]],
            sort='splice_ai', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}],
                [{'selectedGeneId': 'ENSG00000277258'}, {'selectedGeneId': 'ENSG00000277258'}],
                [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
            ]
        )

        self._assert_expected_search(
            [[VARIANT4, VARIANT3], [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4],
             [GCNV_VARIANT3, GCNV_VARIANT4]],
            sort='callset_af', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}],
                [{'selectedGeneId': 'ENSG00000277258'}, {'selectedGeneId': 'ENSG00000277258'}],
                [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
            ]
        )

        self._assert_expected_search(
            [[VARIANT3, VARIANT4], [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4],
             [GCNV_VARIANT3, GCNV_VARIANT4]],
            sort='gnomad_exomes', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}],
                [{'selectedGeneId': 'ENSG00000277258'}, {'selectedGeneId': 'ENSG00000277258'}],
                [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
            ]
        )

        self._assert_expected_search(
            [[VARIANT3, VARIANT4], [GCNV_VARIANT3, GCNV_VARIANT4],
             [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4]],
            sort='in_omim', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}],
                [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
                [{'selectedGeneId': 'ENSG00000277258'}, {'selectedGeneId': 'ENSG00000277258'}],
            ]
        )

    def test_gene_variant_lookup(self):
        url = reverse(gene_variant_lookup)
        self.check_require_login(url)

        body = {
            'genomeVersion': '38',
            'geneId': 'ENSG00000097046',
            'annotations': {
                'missense': ['missense_variant'],
                'other': ['non_coding_transcript_exon_variant'],
            },
            'freqs': {
                'callset': {'ac': 3000},
                'gnomad_genomes': {'af': 0.003},
                'gnomad_exomes': {'af': 0.003},
            },
        }
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        variant4 = {**VARIANT4, 'selectedMainTranscriptId': 'ENST00000350997'}
        del variant4['familyGuids']
        del variant4['genotypes']
        expected_response = {
            'searchedVariants': [variant4],
            'genesById': {'ENSG00000097046': mock.ANY},
            'omimIntervals': {},
            'totalSampleCounts': {
                'MITO': {'WES': 1},
                'SNV_INDEL': {'WES': 7},
                'SV': {'WES': 3, 'WGS': 3},
            },
        }
        self.assertDictEqual(response.json(), expected_response)

        body['freqs'] = {}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        variant3 = {**VARIANT3, 'selectedMainTranscriptId': 'ENST00000497611'}
        del variant3['familyGuids']
        del variant3['genotypes']
        expected_response['searchedVariants'].insert(0, variant3)
        expected_response['genesById']['ENSG00000177000'] = mock.ANY
        self.assertDictEqual(response.json(), expected_response)

        body['geneId'] = 'ENSG00000229905'
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            **expected_response,
            'searchedVariants': [],
            'genesById': {},
        })
