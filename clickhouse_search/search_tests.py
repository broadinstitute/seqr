from django.core.exceptions import ObjectDoesNotExist
from django.db import connections
from django.test import TestCase
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
    format_cached_variant
from reference_data.models import Omim
from seqr.models import Project, Family, Sample
from seqr.utils.search.search_utils_tests import SearchTestHelper
from seqr.utils.search.utils import query_variants, variant_lookup, sv_variant_lookup
from seqr.views.utils.json_utils import DjangoJSONEncoderWithSets


@mock.patch('clickhouse_search.search.CLICKHOUSE_SERVICE_HOSTNAME', 'localhost')
class ClickhouseSearchTests(SearchTestHelper, TestCase):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data', 'clickhouse_search', 'clickhouse_transcripts']

    def setUp(self):
        super().set_up()
        with connections['clickhouse'].cursor() as cursor:
            for table_base in ['GRCh38/SNV_INDEL', 'GRCh38/MITO', 'GRCh38/SV', 'GRCh37/SNV_INDEL']:
                cursor.execute(f'SYSTEM REFRESH VIEW "{table_base}/project_gt_stats_to_gt_stats_mv"')
        Project.objects.update(genome_version='38')

    def _assert_expected_search(self, expected_results, gene_counts=None, inheritance_mode=None, inheritance_filter=None, quality_filter=None, cached_variant_fields=None, sort='xpos', **search_kwargs):
        self.search_model.search.update(search_kwargs or {})
        self.search_model.search['qualityFilter'] = quality_filter
        self.search_model.search['inheritance']['mode'] = inheritance_mode
        if inheritance_filter is not None:
            self.search_model.search['inheritance']['filter'] = inheritance_filter

        variants, total = query_variants(self.results_model, user=self.user, sort=sort)
        encoded_variants = self._assert_expected_variants(variants, expected_results)

        self.assertEqual(total, len(expected_results))
        self._assert_expected_search_cache(encoded_variants, total, cached_variant_fields, sort)

    def _assert_expected_variants(self, variants, expected_results):
        encoded_variants = json.loads(json.dumps(variants, cls=DjangoJSONEncoderWithSets))
        self.assertListEqual(encoded_variants, expected_results)
        return encoded_variants

    def _assert_expected_search_cache(self, variants, total, cached_variant_fields, sort):
        cached_variants = [
            self._get_cached_variant(variant, (cached_variant_fields[i] if cached_variant_fields else None))
            for i, variant in enumerate(variants)
        ]
        results_cache = {'all_results': cached_variants, 'total_results': total}
        self.assert_cached_results(results_cache, sort=sort)

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

        mito_gene_counts = {
            'ENSG00000210112': {'total': 1, 'families': {'F000002_2': 1}},
            'ENSG00000198886': {'total': 1, 'families': {'F000002_2': 1}},
            'ENSG00000198727': {'total': 1, 'families': {'F000002_2': 1}},
        }
        self._assert_expected_search(
            [MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], gene_counts=mito_gene_counts, locus={'rawItems': 'M:1-100000000'},
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
            [VARIANT1, SV_VARIANT1, SV_VARIANT2, VARIANT2, VARIANT3, VARIANT4, SV_VARIANT3, GCNV_VARIANT1, SV_VARIANT4,
                         GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            gene_counts={**variant_gene_counts, **mito_gene_counts, **GCNV_GENE_COUNTS, **SV_GENE_COUNTS, 'ENSG00000277258': {'total': 2, 'families': {'F000002_2': 2}}},
        )

        self._set_grch37_search()
        self._assert_expected_search([GRCH37_VARIANT])

    def test_single_project_search(self):
        variant_gene_counts = {
            'ENSG00000097046': {'total': 3, 'families': {'F000002_2': 2, 'F000003_3': 1}},
            'ENSG00000177000': {'total': 3, 'families': {'F000002_2': 2, 'F000003_3': 1}},
            'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
            'ENSG00000210112': {'total': 1, 'families': {'F000002_2': 1}},
            'ENSG00000198886': {'total': 1, 'families': {'F000002_2': 1}},
            'ENSG00000198727': {'total': 1, 'families': {'F000002_2': 1}},
        }
        self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2,
             GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            gene_counts={**variant_gene_counts, **GCNV_GENE_COUNTS, 'ENSG00000277258': {'total': 2, 'families': {'F000002_2': 2}}}
        )

        self._add_sample_type_samples('WES', dataset_type='SV', guid__in=['S000135_na20870'])
        self._assert_expected_search(
            [GCNV_MULTI_FAMILY_VARIANT1, GCNV_MULTI_FAMILY_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], gene_counts={
                'ENSG00000129562': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000013364': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000079616': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000103495': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000167371': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000280789': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000280893': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000281348': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000275023': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000277972': {'total': 1, 'families': {'F000002_2': 1}},
            }, annotations={'structural': COMP_HET_ALL_PASS_FILTERS['annotations']['structural']},
        )

    def test_multi_project_search(self):
        self._set_multi_project_search()
        self._assert_expected_search(
            [PROJECT_2_VARIANT, MULTI_PROJECT_VARIANT1, MULTI_PROJECT_VARIANT2, VARIANT3, VARIANT4,
             GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            gene_counts=GENE_COUNTS,
        )

        self.results_model.families.set(Family.objects.filter(guid__in=['F000002_2', 'F000011_11', 'F000014_14']))
        self._assert_expected_search(
            [PROJECT_2_VARIANT, MULTI_PROJECT_VARIANT1, SV_VARIANT1, SV_VARIANT2, MULTI_PROJECT_VARIANT2, VARIANT3,
             VARIANT4, SV_VARIANT3, GCNV_VARIANT1, SV_VARIANT4, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1,
             MITO_VARIANT2, MITO_VARIANT3], gene_counts={**GENE_COUNTS, **SV_GENE_COUNTS},
        )

    def test_both_sample_types_search(self):
        Sample.objects.exclude(dataset_type='SNV_INDEL').update(is_active=False)

        # One family (F000011_11) in a multi-project search has identical exome and genome data.
        self._set_multi_project_search()
        self._add_sample_type_samples('WES', individual__family__guid='F000011_11')

        self._assert_expected_search(
            MULTI_PROJECT_BOTH_SAMPLE_TYPE_VARIANTS, gene_counts=GENE_COUNTS,
        )

        self._set_single_family_search()
        self._add_sample_type_samples('WGS', guid__in=['S000132_hg00731'])

        # Variant 1 is de novo in exome but inherited and homozygous in genome.
        # Variant 2 is inherited and homozygous in exome and de novo and homozygous in genome, so it fails de-novo inheritance when parental data is missing in genome.
        # Variant 3 is inherited in both sample types.
        # Variant 4 is de novo in exome, but inherited in genome in the same parent that has variant 3.
        self._assert_expected_search(
            [VARIANT1_BOTH_SAMPLE_TYPES, VARIANT4_BOTH_SAMPLE_TYPES],
            inheritance_mode='de_novo',
        )

        self._add_sample_type_samples('WGS', guid__in=['S000133_hg00732', 'S000134_hg00733'])
        self._assert_expected_search(
            [VARIANT1_BOTH_SAMPLE_TYPES, VARIANT2_BOTH_SAMPLE_TYPES, VARIANT4_BOTH_SAMPLE_TYPES],
            inheritance_mode='de_novo',
        )

        self._assert_expected_search(
            [VARIANT1_BOTH_SAMPLE_TYPES, VARIANT2_BOTH_SAMPLE_TYPES, [VARIANT3_BOTH_SAMPLE_TYPES, VARIANT4_BOTH_SAMPLE_TYPES]],
            inheritance_mode='recessive', **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                {}, {}, [{'selectedGeneId':  'ENSG00000097046'}, {'selectedGeneId':  'ENSG00000097046'}],
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
            inheritance_mode=inheritance_mode,
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT4], inheritance_mode=inheritance_mode,
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
                'ENSG00000177000': {'total': 1, 'families': {'F000002_2': 1}},
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
            }, cached_variant_fields=[
                {}, {},
                [{'selectedGeneId':  'ENSG00000097046'}, {'selectedGeneId':  'ENSG00000097046'}], {},
            ], **ALL_SNV_INDEL_PASS_FILTERS,
        )

        self._set_single_family_search()
        self._assert_expected_search(
            [VARIANT2, [VARIANT3, VARIANT4], MITO_VARIANT3], inheritance_mode=inheritance_mode, cached_variant_fields=[
                {},
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}], {},
            ],
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
                'ENSG00000171621': {'total': 2, 'families': {'F000011_11': 2}},
                'ENSG00000184986': {'total': 1, 'families': {'F000011_11': 1}},
            }, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000171621'}, {'selectedGeneId': 'ENSG00000171621'}], {},
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

        self._assert_expected_search(
            [VARIANT1, VARIANT2, selected_family_3_variant, MITO_VARIANT1, MITO_VARIANT3], quality_filter=quality_filter,
            annotations=annotations, pathogenicity={'clinvar': ['likely_pathogenic', 'vus_or_conflicting']}, cached_variant_fields=cached_variant_fields,
        )

        self._assert_expected_search(
            [VARIANT2, selected_family_3_variant, MITO_VARIANT1], quality_filter=quality_filter,
            annotations=annotations, pathogenicity={'clinvar': ['pathogenic']}, cached_variant_fields=cached_variant_fields[1:],
        )
#
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
            [SV_VARIANT1], locus={'rawItems': 'chr1:9292894-9369532'}
        )

        self._reset_search_families()
        self._assert_expected_search(
            [VARIANT1, VARIANT2, GCNV_VARIANT1, GCNV_VARIANT2, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], exclude={
                'rawItems': ','.join([LOCATION_SEARCH['locus']['rawItems'], sv_locus['rawItems']])
            }, locus=None,
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT2, SV_VARIANT3, SV_VARIANT4], exclude=sv_locus,
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

    def test_variant_lookup(self):
        variant = variant_lookup(self.user, ('1', 10439, 'AC', 'A'))
        self._assert_expected_variants([variant], [VARIANT_LOOKUP_VARIANT])

        with self.assertRaises(ObjectDoesNotExist) as cm:
            variant_lookup(self.user, ('1', 91511686, 'TCA', 'G'))
        self.assertEqual(str(cm.exception), 'Variant not present in seqr')

        variant = variant_lookup(self.user, ('7', 143270172, 'A', 'G'), genome_version='37')
        self._assert_expected_variants([variant], [{
            **{k: v for k, v in GRCH37_VARIANT.items() if k not in {'familyGuids', 'genotypes'}},
            'familyGenotypes': {GRCH37_VARIANT['familyGuids'][0]: sorted([
                {k: v for k, v in g.items() if k != 'individualGuid'} for g in GRCH37_VARIANT['genotypes'].values()
            ], key=lambda x: x['sampleId'], reverse=True)},
        }])

        variant = variant_lookup(self.user, ('M', 4429, 'G', 'A'), genome_version='38')
        self._assert_expected_variants([variant], [{
            **{k: v for k, v in MITO_VARIANT1.items() if k not in {'familyGuids', 'genotypes'}},
            'familyGenotypes': {MITO_VARIANT1['familyGuids'][0]: [
                {k: v for k, v in g.items() if k != 'individualGuid'} for g in MITO_VARIANT1['genotypes'].values()
            ]},
        }])

        variant = sv_variant_lookup(self.user, 'phase2_DEL_chr14_4640', self.families, sample_type='WGS')
        self._assert_expected_variants([variant], [SV_VARIANT4])
#
#         body.update({'variant_id': 'suffix_140608_DUP', 'data_type': 'SV_WES', 'sample_data': EXPECTED_SAMPLE_DATA['SV_WES']})
#         async with self.client.request('POST', '/lookup', json=body) as resp:
#             self.assertEqual(resp.status, 200)
#             resp_json = resp.json()
#         self.assertDictEqual(resp_json, {
#             **NO_GENOTYPE_GCNV_VARIANT, 'genotypes': {
#                 individual: {k: v for k, v in genotype.items() if k not in {'start', 'end', 'numExon', 'geneIds'}}
#                 for individual, genotype in GCNV_VARIANT4['genotypes'].items()
#             }
#         })
#
#         body['variant_id'] = 'suffix_140608_DEL'
#         async with self.client.request('POST', '/lookup', json=body) as resp:
#             self.assertEqual(resp.status, 404)

    #         self._assert_expected_search(
    #             [GCNV_VARIANT4], padded_interval={'chrom': '17', 'start': 38720781, 'end': 38738703, 'padding': 0.2},
    #             omit_data_type='SNV_INDEL',
    #         )
    #
    #         self._assert_expected_search(
    #             [], padded_interval={'chrom': '17', 'start': 38720781, 'end': 38738703, 'padding': 0.1},
    #             omit_data_type='SNV_INDEL',
    #         )
    #
    #         self._assert_expected_search(
    #             [SV_VARIANT4], padded_interval={'chrom': '14', 'start': 106692244, 'end': 106742587, 'padding': 0.1},
    #             sample_data=SV_WGS_SAMPLE_DATA,
    #         )

#     def test_multi_variant_lookup(self):
#         self._test_multi_lookup(VARIANT_ID_SEARCH['variant_ids'], 'SNV_INDEL', [VARIANT1])
#
#         self._test_multi_lookup([['7', 143270172, 'A', 'G']], 'SNV_INDEL', [GRCH37_VARIANT], genome_version='GRCh37')
#
#         self._test_multi_lookup([['M', 4429, 'G', 'A'], ['M', 14783, 'T', 'C']], 'MITO', [MITO_VARIANT1, MITO_VARIANT3])
#
#         self._test_multi_lookup(
#             ['cohort_2911.chr1.final_cleanup_INS_chr1_160', 'phase2_DEL_chr14_4640'],
#             'SV_WGS', [SV_VARIANT2, SV_VARIANT4],
#         )
#
#         self._test_multi_lookup(['suffix_140608_DUP'], 'SV_WES', [NO_GENOTYPE_GCNV_VARIANT])
#
#     def _test_multi_lookup(self, variant_ids, data_type, results, genome_version='GRCh38'):
#         body = {'genome_version': genome_version, 'data_type': data_type, 'variant_ids': variant_ids}
#         async with self.client.request('POST', '/multi_lookup', json=body) as resp:
#             self.assertEqual(resp.status, 200)
#             resp_json = resp.json()
#         self.assertDictEqual(resp_json, {'results': [
#             {k: v for k, v in variant.items() if k not in {'familyGuids', 'genotypes'}}
#             for variant in results
#         ]})
#
    def test_frequency_filter(self):
        sv_callset_filter = {'sv_callset': {'af': 0.05}}
        # seqr af filter is ignored for SNV_INDEL
        self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            freqs={'callset': {'af': 0.2},  **sv_callset_filter},
        )

        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            freqs={'callset': {'ac': 6}, **sv_callset_filter},
        )

        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], freqs={'callset': {'hh': 1}},
        )

        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, GCNV_VARIANT3, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], freqs={'callset': {'ac': 6, 'hh': 0}, 'sv_callset': {'ac': 50}},
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT1], freqs={'sv_callset': {'ac': 1}},
        )

        self._reset_search_families()
        self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2], freqs={'gnomad_genomes': {'af': 0.05}, 'gnomad_mito': {'af': 0.05}},
        )

        self._assert_expected_search(
            [VARIANT2, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2], freqs={'gnomad_genomes': {'af': 0.05, 'hh': 1}, 'gnomad_mito': {'af': 0.05}},
        )

        self._set_sv_family_search()
        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT3, SV_VARIANT4], freqs={'gnomad_svs': {'af': 0.001}},
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
            [VARIANT1, VARIANT2, VARIANT4, MITO_VARIANT1],
            freqs={'gnomad_genomes': {'af': 0.01, 'hh': 10}, 'gnomad_mito': {'af': 0.01}},
            annotations=annotations, pathogenicity={'clinvar': ['pathogenic', 'likely_pathogenic', 'vus_or_conflicting']},
        )

        self._assert_expected_search(
            [VARIANT2, VARIANT4, MITO_VARIANT1], freqs={'gnomad_genomes': {'af': 0.01}, 'gnomad_mito': {'af': 0.01}},
            annotations=annotations, pathogenicity={'clinvar': ['pathogenic', 'vus_or_conflicting']},
        )

    def test_annotations_filter(self):
        self._assert_expected_search([VARIANT2], pathogenicity={'hgmd': ['hgmd_other']})

        pathogenicity = {'clinvar': ['likely_pathogenic', 'vus_or_conflicting', 'benign']}
        self._assert_expected_search(
            [VARIANT1, VARIANT2, MITO_VARIANT1, MITO_VARIANT3], pathogenicity=pathogenicity,
        )

        exclude = {'clinvar': pathogenicity['clinvar'][1:]}
        pathogenicity['clinvar'] = pathogenicity['clinvar'][:1]
        snv_38_only_annotations = {'SCREEN': ['CTCF-only', 'DNase-only'], 'UTRAnnotator': ['5_prime_UTR_stop_codon_loss_variant']}
        selected_transcript_variant_2 = {**VARIANT2, 'selectedMainTranscriptId': 'ENST00000408919'}
        self._assert_expected_search(
            [VARIANT1, selected_transcript_variant_2, VARIANT4, MITO_VARIANT3], pathogenicity=pathogenicity, annotations=snv_38_only_annotations,
            cached_variant_fields=[
                {'selectedTranscript': None},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][1]},
                {'selectedTranscript': None},
                {},
            ]
        )

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

        pathogenicity = {'clinvar': ['likely_pathogenic', 'vus_or_conflicting']}
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
        self.results_model.families.set(Family.objects.filter(guid__in=['F000002_2', 'F000014_14']))
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
            **GCNV_VARIANT4, 'genotypes': {k: v for k, v in GCNV_VARIANT4['genotypes'].items() if k != 'I000005_hg00732'}
        }
        Sample.objects.filter(guid='S000146_hg00732').update(is_active=False)
        self._assert_expected_search(
            [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, missing_gt_gcnv_variant]],
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

#     def test_search_errors(self):
#         search_body = get_hail_search_body(sample_data=FAMILY_2_MISSING_SAMPLE_DATA)
#         async with self.client.request('POST', '/search', json=search_body) as resp:
#             self.assertEqual(resp.status, 400)
#             reason = resp.reason
#         self.assertEqual(reason, 'The following samples are available in seqr but missing the loaded data: NA19675_1, NA19678')
#
#         search_body = get_hail_search_body(sample_data=MULTI_PROJECT_MISSING_SAMPLE_DATA)
#         async with self.client.request('POST', '/search', json=search_body) as resp:
#             self.assertEqual(resp.status, 400)
#             reason = resp.reason
#         self.assertEqual(reason, 'The following samples are available in seqr but missing the loaded data: NA19675_1, NA19678')
#
#         search_body = get_hail_search_body(
#             intervals=LOCATION_SEARCH['intervals'] + [['1', 1, 999999999]], omit_data_type='SV_WES',
#         )
#         async with self.client.request('POST', '/search', json=search_body) as resp:
#             self.assertEqual(resp.status, 400)
#             reason = resp.reason
#         self.assertEqual(reason, 'Invalid intervals: 1:1-999999999')

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
            [VARIANT2, MITO_VARIANT1, MITO_VARIANT2, VARIANT4, VARIANT1, MITO_VARIANT3, VARIANT3, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            sort='gnomad',
        )

        self._reset_search_families()
        self._assert_expected_search(
            [VARIANT1, MULTI_FAMILY_VARIANT, VARIANT4, VARIANT2, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            sort='gnomad_exomes',
        )

        self._assert_expected_search(
            [MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3, VARIANT4, MULTI_FAMILY_VARIANT, VARIANT2, VARIANT1, GCNV_VARIANT3, GCNV_VARIANT4, GCNV_VARIANT2, GCNV_VARIANT1],
            sort='callset_af',
        )

        self._assert_expected_search(
            [VARIANT4, VARIANT2, VARIANT1, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            sort='cadd',
        )

        self._assert_expected_search(
            [VARIANT4, VARIANT2, VARIANT1, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='revel',
        )

        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT2, VARIANT4, VARIANT1, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='splice_ai',
        )

        self._assert_expected_search(
            [VARIANT2, VARIANT1, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='alphamissense',
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
            sort='family_guid',
        )

        # size sort only applies to SVs, so has no impact on other variant
        self._reset_search_families()
        self._assert_expected_search(
            [GCNV_VARIANT1, GCNV_VARIANT4, GCNV_VARIANT2, GCNV_VARIANT3, VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='size',
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
