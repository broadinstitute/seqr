from django.db import connections
from django.test import TestCase
import json
import mock
import os

from clickhouse_search.test_utils import VARIANT1, VARIANT2, VARIANT3, VARIANT4, CACHED_CONSEQUENCES_BY_KEY, \
    VARIANT_ID_SEARCH, VARIANT_IDS, LOCATION_SEARCH, GENE_IDS, SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT, \
    SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_3, COMP_HET_ALL_PASS_FILTERS, \
    SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, SELECTED_ANNOTATION_TRANSCRIPT_MULTI_FAMILY_VARIANT, MULTI_FAMILY_VARIANT, \
    FAMILY_3_VARIANT, PROJECT_2_VARIANT, PROJECT_2_VARIANT1, MULTI_PROJECT_VARIANT1, MULTI_PROJECT_VARIANT2, GENE_COUNTS, \
    MULTI_PROJECT_BOTH_SAMPLE_TYPE_VARIANTS, VARIANT1_BOTH_SAMPLE_TYPES, VARIANT2_BOTH_SAMPLE_TYPES, \
    VARIANT3_BOTH_SAMPLE_TYPES, VARIANT4_BOTH_SAMPLE_TYPES, GRCH37_VARIANT, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3, \
    format_cached_variant
from reference_data.models import Omim
from seqr.models import Project, Family, Sample
from seqr.utils.search.search_utils_tests import SearchTestHelper
from seqr.utils.search.utils import query_variants
from seqr.views.utils.json_utils import DjangoJSONEncoderWithSets


@mock.patch('clickhouse_search.search.CLICKHOUSE_SERVICE_HOSTNAME', 'localhost')
class ClickhouseSearchTests(SearchTestHelper, TestCase):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data', 'clickhouse_search', 'clickhouse_transcripts']

    @classmethod
    def setUpTestData(cls):
        with connections['clickhouse'].cursor() as cursor:
            cursor.execute("""
            CREATE OR REPLACE DICTIONARY "GRCh38/SNV_INDEL/gt_stats_dict"
            (
                key UInt32,
                ac_wes UInt32,
                ac_wgs UInt32,
                hom_wes UInt32,
                hom_wgs UInt32,
            )
            PRIMARY KEY key
            SOURCE(CLICKHOUSE(
                USER %s
                PASSWORD %s
                QUERY "SELECT * FROM VALUES ((1, 4, 5, 2, 0), (2, 12, 16, 3, 1), (3, 4, 0, 1, 0), (4, 0, 2, 0, 0))"
            ))
            LIFETIME(0)
            LAYOUT(FLAT(MAX_ARRAY_SIZE 500000000))
            """, [os.environ.get('CLICKHOUSE_USER', 'clickhouse'), os.environ.get('CLICKHOUSE_PASSWORD', 'clickhouse_test')])
            cursor.execute("""
            CREATE OR REPLACE DICTIONARY "GRCh37/SNV_INDEL/gt_stats_dict"
            (
                key UInt32,
                ac_wes UInt32,
                ac_wgs UInt32,
                hom_wes UInt32,
                hom_wgs UInt32,
            )
            PRIMARY KEY key
            SOURCE(CLICKHOUSE(
                USER %s
                PASSWORD %s
                QUERY "SELECT * FROM VALUES ((11, 4711, 0, 1508, 0))"
            ))
            LIFETIME(0)
            LAYOUT(FLAT(MAX_ARRAY_SIZE 500000000))
            """, [os.environ.get('CLICKHOUSE_USER', 'clickhouse'), os.environ.get('CLICKHOUSE_PASSWORD', 'clickhouse_test')])
            cursor.execute("""
            CREATE OR REPLACE DICTIONARY "GRCh38/MITO/gt_stats_dict"
            (
                key UInt32,
                ac_het_wes UInt32,
                ac_het_wgs UInt32,
                ac_hom_wes UInt32,
                ac_hom_wgs UInt32,
            )
            PRIMARY KEY key
            SOURCE(CLICKHOUSE(
                USER %s
                PASSWORD %s
                QUERY "SELECT * FROM VALUES ((6, 0, 1, 0, 0), (7, 1, 0, 0, 0), (8, 0, 1, 2, 1))"
            ))
            LIFETIME(0)
            LAYOUT(FLAT(MAX_ARRAY_SIZE 500000000))
            """, [os.environ.get('CLICKHOUSE_USER', 'clickhouse'), os.environ.get('CLICKHOUSE_PASSWORD', 'clickhouse_test')])

    def setUp(self):
        super().set_up()
        Project.objects.update(genome_version='38')
        Sample.objects.filter(dataset_type=Sample.DATASET_TYPE_SV_CALLS).update(is_active=False)

    def _assert_expected_search(self, expected_results, gene_counts=None, inheritance_mode=None, inheritance_filter=None, quality_filter=None, cached_variant_fields=None, sort='xpos', **search_kwargs):
        self.search_model.search.update(search_kwargs or {})
        self.search_model.search['qualityFilter'] = quality_filter
        self.search_model.search['inheritance']['mode'] = inheritance_mode
        if inheritance_filter is not None:
            self.search_model.search['inheritance']['filter'] = inheritance_filter

        variants, total = query_variants(self.results_model, user=self.user, sort=sort)
        encoded_variants = json.loads(json.dumps(variants, cls=DjangoJSONEncoderWithSets))

        self.assertListEqual(encoded_variants, expected_results)
        self.assertEqual(total, len(expected_results))
        self._assert_expected_search_cache(encoded_variants, total, cached_variant_fields, sort)

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

    def _reset_search_families(self):
        self.results_model.families.set(self.families)

    def _set_grch37_search(self):
        Project.objects.filter(id=1).update(genome_version='37')
        Sample.objects.filter(sample_id='HG00732').update(is_active=False)
        Sample.objects.filter(dataset_type=Sample.DATASET_TYPE_MITO_CALLS).update(is_active=False)
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
        )

        mito_gene_counts = {
            'ENSG00000210112': {'total': 1, 'families': {'F000002_2': 1}},
            'ENSG00000198886': {'total': 1, 'families': {'F000002_2': 1}},
            'ENSG00000198727': {'total': 1, 'families': {'F000002_2': 1}},
        }
        self._assert_expected_search(
            [MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], gene_counts=mito_gene_counts, locus={'rawItems': 'M:1-100000000'},
        )

#         self._assert_expected_search(
#             [GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], omit_data_type='SNV_INDEL', gene_counts=GCNV_GENE_COUNTS,
#         )
#
#         self._assert_expected_search(
#             [SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, gene_counts=SV_GENE_COUNTS,
#         )
#
        self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT3, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], locus=None,
            # [VARIANT1, SV_VARIANT1, SV_VARIANT2, VARIANT2, VARIANT3, VARIANT4, SV_VARIANT3, GCNV_VARIANT1, SV_VARIANT4,
            #              GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            # gene_counts={**variant_gene_counts, **mito_gene_counts, **GCNV_GENE_COUNTS, **SV_GENE_COUNTS, 'ENSG00000277258': {'total': 2, 'families': {'F000002_2': 2}}},
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
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], gene_counts=variant_gene_counts,
        )

#         self._assert_expected_search(
#             [GCNV_MULTI_FAMILY_VARIANT1, GCNV_MULTI_FAMILY_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], sample_data=SV_WES_SAMPLE_DATA, gene_counts={
#                 'ENSG00000129562': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
#                 'ENSG00000013364': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
#                 'ENSG00000079616': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
#                 'ENSG00000103495': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
#                 'ENSG00000167371': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
#                 'ENSG00000280789': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
#                 'ENSG00000280893': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
#                 'ENSG00000281348': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
#                 'ENSG00000275023': {'total': 2, 'families': {'F000002_2': 2}},
#                 'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
#                 'ENSG00000277972': {'total': 1, 'families': {'F000002_2': 1}},
#             }
#         )
#
#         self._assert_expected_search(
#             [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
#             gene_counts={**variant_gene_counts, **GCNV_GENE_COUNTS, 'ENSG00000277258': {'total': 2, 'families': {'F000002_2': 2}}}
#         )

    def test_multi_project_search(self):
        self._set_multi_project_search()
        self._assert_expected_search(
            [PROJECT_2_VARIANT, MULTI_PROJECT_VARIANT1, MULTI_PROJECT_VARIANT2, VARIANT3, VARIANT4,
             MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            gene_counts=GENE_COUNTS,
        )

#         self._assert_expected_search(
#             [PROJECT_2_VARIANT, MULTI_PROJECT_VARIANT1, SV_VARIANT1, SV_VARIANT2, MULTI_PROJECT_VARIANT2, VARIANT3,
#              VARIANT4, SV_VARIANT3, SV_VARIANT4], gene_counts={**GENE_COUNTS, **SV_GENE_COUNTS},
#             sample_data={**MULTI_PROJECT_SAMPLE_DATA, **SV_WGS_SAMPLE_DATA},
#         )
#
    def test_both_sample_types_search(self):
        Sample.objects.filter(dataset_type='MITO').update(is_active=False)

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
    def _add_sample_type_samples(sample_type, **sample_filter):
        for sample in Sample.objects.filter(**sample_filter):
            sample.pk = None
            sample.sample_type = sample_type
            sample.save()

    def test_inheritance_filter(self):
        inheritance_mode = 'any_affected'
        self._assert_expected_search(
            # [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            inheritance_mode=inheritance_mode,
        )

        # self._assert_expected_search(
        #     [SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA,
        # )
        #
        # self._assert_expected_search(
        #     [GCNV_VARIANT3], inheritance_mode=inheritance_mode, annotations=NEW_SV_FILTER, omit_data_type='SNV_INDEL',
        # )
        #
        # self._assert_expected_search(
        #     [SV_VARIANT2], inheritance_mode=inheritance_mode, annotations=NEW_SV_FILTER, sample_data=SV_WGS_SAMPLE_DATA,
        # )

        inheritance_mode = 'de_novo'
        self._assert_expected_search(
            # [VARIANT1, FAMILY_3_VARIANT, VARIANT4, GCNV_VARIANT1],
            [VARIANT1, FAMILY_3_VARIANT, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            inheritance_mode=inheritance_mode,
        )

        # self._assert_expected_search(
        #     [SV_VARIANT1], inheritance_mode=inheritance_mode,  sample_data=SV_WGS_SAMPLE_DATA,
        # )

        inheritance_mode = 'x_linked_recessive'
        self._assert_expected_search([], inheritance_mode=inheritance_mode)
        # self._assert_expected_search([], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA_WITH_SEX)

        inheritance_mode = 'homozygous_recessive'
        self._assert_expected_search(
            # [VARIANT2, GCNV_VARIANT3],
            [VARIANT2, MITO_VARIANT3],
            inheritance_mode=inheritance_mode,
        )

        self._set_multi_project_search()
        self._assert_expected_search(
            [PROJECT_2_VARIANT1, VARIANT2, MITO_VARIANT3],
            inheritance_mode=inheritance_mode,
        )

        # self._assert_expected_search(
        #     [SV_VARIANT4], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA,
        # )

        gt_inheritance_filter = {'genotype': {'I000006_hg00733': 'ref_ref', 'I000005_hg00732': 'has_alt'}}
        self._set_single_family_search()
        self._assert_expected_search([VARIANT2], inheritance_filter=gt_inheritance_filter)

        self._assert_expected_search(
            [VARIANT2], inheritance_mode='any_affected', inheritance_filter={'affected': {
                'I000004_hg00731': 'N', 'I000005_hg00732': 'A', 'I000006_hg00733': 'U',
            }},
        )

        inheritance_mode = 'compound_het'
        self._reset_search_families()
        self._assert_expected_search(
            [[VARIANT3, VARIANT4]], inheritance_mode=inheritance_mode, inheritance_filter={}, gene_counts={
                'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000177000': {'total': 1, 'families': {'F000002_2': 1}},
            }, **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId':  'ENSG00000097046'}, {'selectedGeneId':  'ENSG00000097046'}],
            ],
        )

#         self._assert_expected_search(
#             [[GCNV_VARIANT3, GCNV_VARIANT4]], inheritance_mode=inheritance_mode, omit_data_type='SNV_INDEL', gene_counts={
#                 'ENSG00000275023': {'total': 2, 'families': {'F000002_2': 2}},
#                 'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
#                 'ENSG00000277972': {'total': 1, 'families': {'F000002_2': 1}},
#             }, **COMP_HET_ALL_PASS_FILTERS,
#         )
#
#         self._assert_expected_search(
#             [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, VARIANT4], [GCNV_VARIANT3, GCNV_VARIANT4]],
#             inheritance_mode=inheritance_mode, gene_counts={
#                 'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
#                 'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2}},
#                 'ENSG00000275023': {'total': 3, 'families': {'F000002_2': 3}},
#                 'ENSG00000277258': {'total': 3, 'families': {'F000002_2': 3}},
#                 'ENSG00000277972': {'total': 2, 'families': {'F000002_2': 2}},
#             }, **COMP_HET_ALL_PASS_FILTERS,
#         )
#
#         self._assert_expected_search(
#             [[SV_VARIANT1, SV_VARIANT2]], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA,
#             **COMP_HET_ALL_PASS_FILTERS, gene_counts={'ENSG00000171621': {'total': 2, 'families': {'F000011_11': 2}}},
#         )
#
#         self._assert_expected_search(
#             [[SV_VARIANT1, SV_VARIANT2], [VARIANT3, VARIANT4]], inheritance_mode=inheritance_mode,
#             sample_data={**SV_WGS_SAMPLE_DATA, **FAMILY_2_VARIANT_SAMPLE_DATA}, **COMP_HET_ALL_PASS_FILTERS, gene_counts={
#                 'ENSG00000171621': {'total': 2, 'families': {'F000011_11': 2}},
#                 'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
#                 'ENSG00000177000': {'total': 1, 'families': {'F000002_2': 1}},
#             },
#         )

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
            ],
        )

        self._set_single_family_search()
        self._assert_expected_search(
            [VARIANT2, [VARIANT3, VARIANT4], MITO_VARIANT3], inheritance_mode=inheritance_mode, cached_variant_fields=[
                {},
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}], {},
            ],
        )
        self._reset_search_families()

#         self._assert_expected_search(
#             [GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]], inheritance_mode=inheritance_mode, omit_data_type='SNV_INDEL', gene_counts={
#                 'ENSG00000275023': {'total': 3, 'families': {'F000002_2': 3}},
#                 'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
#                 'ENSG00000277972': {'total': 1, 'families': {'F000002_2': 1}},
#             }, **COMP_HET_ALL_PASS_FILTERS,
#         )
#
#         self._assert_expected_search(
#             [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, VARIANT4], GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]],
#             inheritance_mode=inheritance_mode, gene_counts={
#                 'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
#                 'ENSG00000177000': {'total': 3, 'families': {'F000002_2': 3}},
#                 'ENSG00000275023': {'total': 4, 'families': {'F000002_2': 4}},
#                 'ENSG00000277258': {'total': 4, 'families': {'F000002_2': 4}},
#                 'ENSG00000277972': {'total': 2, 'families': {'F000002_2': 2}},
#             }, **COMP_HET_ALL_PASS_FILTERS,
#         )
#
#         self._assert_expected_search(
#             [[SV_VARIANT1, SV_VARIANT2], SV_VARIANT4], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA,
#             **COMP_HET_ALL_PASS_FILTERS, gene_counts={
#                 'ENSG00000171621': {'total': 2, 'families': {'F000011_11': 2}},
#                 'ENSG00000184986': {'total': 1, 'families': {'F000011_11': 1}},
#             }
#         )

    def test_quality_filter(self):
        quality_filter = {'vcf_filter': 'pass'}
        self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, MITO_VARIANT1, MITO_VARIANT2],
            # [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            quality_filter=quality_filter
        )

        # self._assert_expected_search(
        #     [SV_VARIANT4], quality_filter=quality_filter,
        #     sample_data={**SV_WGS_SAMPLE_DATA, **FAMILY_2_MITO_SAMPLE_DATA}
        # )

        gcnv_quality_filter = {'min_gq': 40, 'min_qs': 20, 'min_hl': 5}
        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, MITO_VARIANT1, MITO_VARIANT3], quality_filter=gcnv_quality_filter,
            # [VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT4], quality_filter=gcnv_quality_filter,
        )

        # self._assert_expected_search(
        #     [], annotations=NEW_SV_FILTER, quality_filter=gcnv_quality_filter, omit_data_type='SNV_INDEL',
        # )
        #
        # sv_quality_filter = {'min_gq_sv': 40}
        # self._assert_expected_search(
        #     [SV_VARIANT3, SV_VARIANT4], quality_filter=sv_quality_filter, sample_data=SV_WGS_SAMPLE_DATA,
        # )
        #
        # self._assert_expected_search(
        #     [], annotations=NEW_SV_FILTER, quality_filter=sv_quality_filter, sample_data=SV_WGS_SAMPLE_DATA,
        # )

        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, MITO_VARIANT1, MITO_VARIANT2], quality_filter={'min_gq': 40, 'vcf_filter': 'pass'},
        )

        self._assert_expected_search(
            # [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            quality_filter={'min_gq': 60, 'min_qs': 10, 'affected_only': True},
        )

        # self._assert_expected_search(
        #     [SV_VARIANT3, SV_VARIANT4], quality_filter={'min_gq_sv': 60, 'affected_only': True}, sample_data=SV_WGS_SAMPLE_DATA,
        # )

        self._assert_expected_search(
            [VARIANT1, VARIANT2, FAMILY_3_VARIANT, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], quality_filter={'min_ab': 50},
        )

        self._assert_expected_search(
            [VARIANT2, VARIANT3, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], quality_filter={'min_ab': 70, 'affected_only': True},
            # omit_data_type='SV_WES',
        )

        quality_filter.update({'min_gq': 40, 'min_ab': 50, 'min_hl': 5})
        self._assert_expected_search(
            [VARIANT2, FAMILY_3_VARIANT, MITO_VARIANT1], quality_filter=quality_filter,
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
#
#         sv_intervals = [['1', 9310023, 9380264], ['17', 38717636, 38724781]]
#         self._assert_expected_search(
#             [GCNV_VARIANT3, GCNV_VARIANT4], intervals=sv_intervals, gene_ids=['ENSG00000275023'], omit_data_type='SNV_INDEL',
#         )
#
#         self._assert_expected_search(
#             [SV_VARIANT1, SV_VARIANT2], sample_data=SV_WGS_SAMPLE_DATA, intervals=sv_intervals, gene_ids=['ENSG00000171621'],
#         )
#
#         self._assert_expected_search(
#             [SV_VARIANT1, SV_VARIANT2, MULTI_PROJECT_GCNV_VARIANT3, GCNV_VARIANT4], intervals=sv_intervals,
#             sample_data={'SV_WES': EXPECTED_SAMPLE_DATA['SV_WES'] + SECOND_PROJECT_SV_WES_SAMPLE_DATA, **SV_WGS_SAMPLE_DATA},
#         )
#
        self._assert_expected_search(
            [VARIANT1, VARIANT2, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], exclude=LOCATION_SEARCH['locus'], locus=None,
        )
#
#         self._assert_expected_search(
#             [GCNV_VARIANT1, GCNV_VARIANT2], intervals=sv_intervals, exclude_intervals=True, omit_data_type='SNV_INDEL',
#         )
#
#         self._assert_expected_search(
#             [SV_VARIANT3, SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, intervals=sv_intervals, exclude_intervals=True,
#         )
#
        self._assert_expected_search(
            [SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT],
            locus={'rawItems': f'{GENE_IDS[1]}\n1:91500851-91525764'}, exclude=None, cached_variant_fields=[
                {'selectedGeneId': 'ENSG00000177000'},
            ],
        )

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
#
#         # For gene search, return SVs annotated in gene even if they fall outside the gene interval
#         nearest_tss_gene_intervals = [['1', 9292894, 9369532]]
#         self._assert_expected_search(
#             [SV_VARIANT1], sample_data=SV_WGS_SAMPLE_DATA, intervals=nearest_tss_gene_intervals,
#         )
#         self._assert_expected_search(
#             [SV_VARIANT1, SV_VARIANT2], sample_data=SV_WGS_SAMPLE_DATA, intervals=nearest_tss_gene_intervals,
#             gene_ids=['ENSG00000171621'],
#         )

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

#         variant_keys = ['suffix_95340_DUP', 'suffix_140608_DUP']
#         self._assert_expected_search([GCNV_VARIANT1, GCNV_VARIANT4], omit_data_type='SNV_INDEL', variant_keys=variant_keys)
#
#         self._assert_expected_search([VARIANT1, GCNV_VARIANT1, GCNV_VARIANT4], variant_keys=variant_keys, **VARIANT_ID_SEARCH)
#
#         self._assert_expected_search([SV_VARIANT2, SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, variant_keys=[
#             'cohort_2911.chr1.final_cleanup_INS_chr1_160', 'phase2_DEL_chr14_4640',
#         ])
#
#     def test_variant_lookup(self):
#         body = {'genome_version': 'GRCh38', 'variant_id': VARIANT_ID_SEARCH['variant_ids'][0]}
#         async with self.client.request('POST', '/lookup', json=body) as resp:
#             self.assertEqual(resp.status, 200)
#             resp_json = resp.json()
#         self.assertDictEqual(resp_json, VARIANT_LOOKUP_VARIANT)
#
#         body['variant_id'] = VARIANT_ID_SEARCH['variant_ids'][1]
#         async with self.client.request('POST', '/lookup', json=body) as resp:
#             self.assertEqual(resp.status, 404)
#
#         body.update({'genome_version': 'GRCh37', 'variant_id': ['7', 143270172, 'A', 'G']})
#         async with self.client.request('POST', '/lookup', json=body) as resp:
#             self.assertEqual(resp.status, 200)
#             resp_json = resp.json()
#         self.assertDictEqual(resp_json, {
#             **{k: v for k, v in GRCH37_VARIANT.items() if k not in {'familyGuids', 'genotypes'}},
#             'familyGenotypes': {GRCH37_VARIANT['familyGuids'][0]: [
#                 {k: v for k, v in g.items() if k != 'individualGuid'} for g in GRCH37_VARIANT['genotypes'].values()
#             ]},
#         })
#
#         body.update({'variant_id': ['M', 4429, 'G', 'A'], 'data_type': 'MITO', 'genome_version': 'GRCh38'})
#         async with self.client.request('POST', '/lookup', json=body) as resp:
#             self.assertEqual(resp.status, 200)
#             resp_json = resp.json()
#         self.assertDictEqual(resp_json, {
#             **{k: v for k, v in MITO_VARIANT1.items() if k not in {'familyGuids', 'genotypes'}},
#             'familyGenotypes': {MITO_VARIANT1['familyGuids'][0]: [
#                 {k: v for k, v in g.items() if k != 'individualGuid'} for g in MITO_VARIANT1['genotypes'].values()
#             ]},
#         })
#
#         body.update({'variant_id': 'phase2_DEL_chr14_4640', 'data_type': 'SV_WGS', 'sample_data': SV_WGS_SAMPLE_DATA['SV_WGS']})
#         async with self.client.request('POST', '/lookup', json=body) as resp:
#             self.assertEqual(resp.status, 200)
#             resp_json = resp.json()
#         self.assertDictEqual(resp_json, SV_VARIANT4)
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
#
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
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            # [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            freqs={'callset': {'af': 0.2},  **sv_callset_filter},
        )

        self._assert_expected_search(
            [VARIANT4, MITO_VARIANT1, MITO_VARIANT2],
            # [MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            freqs={'callset': {'ac': 2}, **sv_callset_filter},
        )

        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], freqs={'callset': {'ac': 4}},
        )

        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], freqs={'callset': {'hh': 1}},
        )

        self._assert_expected_search(
            [VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], freqs={'callset': {'ac': 4, 'hh': 0}},
        )

#         self._assert_expected_search(
#             [SV_VARIANT1], frequencies=sv_callset_filter, sample_data=SV_WGS_SAMPLE_DATA,
#         )
#
        self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT4, MITO_VARIANT1, MITO_VARIANT2], freqs={'gnomad_genomes': {'af': 0.05}, 'gnomad_mito': {'af': 0.05}},
        )

        self._assert_expected_search(
            [VARIANT2, VARIANT4, MITO_VARIANT1, MITO_VARIANT2], freqs={'gnomad_genomes': {'af': 0.05, 'hh': 1}, 'gnomad_mito': {'af': 0.05}},
        )

#
#         self._assert_expected_search(
#             [SV_VARIANT1, SV_VARIANT3, SV_VARIANT4], frequencies={'gnomad_svs': {'af': 0.001}}, sample_data=SV_WGS_SAMPLE_DATA,
#         )

        self._assert_expected_search(
            [VARIANT4, MITO_VARIANT1, MITO_VARIANT2],
            freqs={'callset': {'ac': 10}, 'gnomad_genomes': {'ac': 50}, 'gnomad_mito': {'ac': 10}},
        )

        self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
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
            'structural_consequence': ['INTRONIC', 'LOF'],
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

        self._assert_expected_search(
            [VARIANT2, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4, MITO_VARIANT2], annotations=annotations, pathogenicity=None,
            cached_variant_fields = [
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][0]},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][1]},
                {},
            ],
            # [VARIANT2, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4, GCNV_VARIANT3, GCNV_VARIANT4], annotations=annotations,
        )

#         self._assert_expected_search([SV_VARIANT1], annotations=annotations, sample_data=SV_WGS_SAMPLE_DATA)

        annotations['splice_ai'] = '0.005'
        annotations['structural'] = ['gCNV_DUP', 'DEL']
        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4, MITO_VARIANT2],
            # [VARIANT2, MULTI_FAMILY_VARIANT, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            annotations=annotations, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][0]},
                {'selectedTranscript': None},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][1]},
                {},
            ]
        )

#         self._assert_expected_search([SV_VARIANT1, SV_VARIANT4], annotations=annotations, sample_data=SV_WGS_SAMPLE_DATA)

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

#         gcnv_annotations_1 = {'structural': ['gCNV_DUP']}
#         gcnv_annotations_2 = {'structural_consequence': ['LOF'], 'structural': []}
#
#         self._assert_expected_search(
#             [[GCNV_VARIANT3, GCNV_VARIANT4]], omit_data_type='SNV_INDEL', inheritance_mode='compound_het',
#             annotations=gcnv_annotations_1, annotations_secondary=gcnv_annotations_2,
#         )
#
#         self._assert_expected_search(
#             [GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]], omit_data_type='SNV_INDEL', inheritance_mode='recessive',
#             annotations=gcnv_annotations_2, annotations_secondary=gcnv_annotations_1,
#         )
#
#         # Do not return pairs where annotations match in a non-paired gene
#         gcnv_annotations_no_pair = {'structural_consequence': ['COPY_GAIN']}
#         self._assert_expected_search(
#             [], omit_data_type='SNV_INDEL', inheritance_mode='compound_het',
#             annotations=gcnv_annotations_1, annotations_secondary=gcnv_annotations_no_pair,
#         )
#
#         self._assert_expected_search(
#             [], omit_data_type='SNV_INDEL', inheritance_mode='compound_het',
#             annotations={**gcnv_annotations_1, **gcnv_annotations_no_pair},
#         )
#
#         self._assert_expected_search(
#             [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4]], inheritance_mode='compound_het',
#             annotations=annotations_1, annotations_secondary=gcnv_annotations_2,
#         )
#
#         self._assert_expected_search(
#             [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4], GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]],
#             inheritance_mode='recessive',
#             annotations={**annotations_1, **gcnv_annotations_1}, annotations_secondary={**annotations_2, **gcnv_annotations_2},
#         )
#
#         self._assert_expected_search(
#             [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], MULTI_PROJECT_GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]],
#             inheritance_mode='recessive',
#             annotations={**annotations_1, **gcnv_annotations_1}, annotations_secondary={**annotations_2, **gcnv_annotations_2},
#             intervals=[['1', 38717636, 38724781], ['17', 38717636, 38724781]],
#             sample_data={**EXPECTED_SAMPLE_DATA, 'SV_WES': EXPECTED_SAMPLE_DATA['SV_WES'] + SECOND_PROJECT_SV_WES_SAMPLE_DATA},
#         )
#
#         self._assert_expected_search(
#             [MULTI_DATA_TYPE_COMP_HET_VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [GCNV_VARIANT3, GCNV_VARIANT4]],
#             inheritance_mode='recessive',
#             annotations={**annotations_1, 'structural': ['gCNV_DEL'], 'structural_consequence': ['INTRONIC']},
#             annotations_secondary={**annotations_2, **gcnv_annotations_1},
#             gene_ids=['ENSG00000277258', 'ENSG00000275023'], intervals=[['1', 38717636, 38724781], ['17', 38717636, 38724781]],
#         )
#
#         self._assert_expected_search(
#             [MULTI_DATA_TYPE_COMP_HET_VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4]],
#             inheritance_mode='recessive', annotations={**annotations_1, 'structural': [], 'structural_consequence': []},
#             annotations_secondary=gcnv_annotations_2,
#             gene_ids=['ENSG00000277258', 'ENSG00000275023'], intervals=[['1', 38717636, 38724781], ['17', 38717636, 38724781]],
#         )
#
#         sv_annotations_1 = {'structural': ['INS', 'LOF']}
#         sv_annotations_2 = {'structural': ['DEL', 'gCNV_DUP'], 'structural_consequence': ['INTRONIC']}
#
#         self._assert_expected_search(
#             [[SV_VARIANT1, SV_VARIANT2]], sample_data=SV_WGS_SAMPLE_DATA, inheritance_mode='compound_het',
#             annotations=sv_annotations_1, annotations_secondary=sv_annotations_2,
#         )
#
#         self._assert_expected_search(
#             [[SV_VARIANT1, SV_VARIANT2], SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, inheritance_mode='recessive',
#             annotations=sv_annotations_2, annotations_secondary=sv_annotations_1,
#         )

        pathogenicity = {'clinvar': ['likely_pathogenic', 'vus_or_conflicting']}
        self._assert_expected_search(
            [VARIANT2, [VARIANT3, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4], MITO_VARIANT3], inheritance_mode='recessive',
            annotations=annotations_2, annotations_secondary=annotations_1, pathogenicity=pathogenicity, cached_variant_fields=[
                {'selectedTranscript': None},
                comp_het_cached_fields,
                {},
            ],
        )

#         self._assert_expected_search(
#             [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [GCNV_VARIANT3, GCNV_VARIANT4]],
#             inheritance_mode='compound_het', pathogenicity=pathogenicity,
#             annotations=gcnv_annotations_2, annotations_secondary=gcnv_annotations_1,
#         )
#
#         self._assert_expected_search(
#             [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]],
#             inheritance_mode='recessive', pathogenicity=pathogenicity,
#             annotations=gcnv_annotations_2, annotations_secondary=gcnv_annotations_1,
#         )
#
        selected_transcript_annotations = {'other': ['non_coding_transcript_exon_variant']}
#         self._assert_expected_search(
#             [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], GCNV_VARIANT3],
#             inheritance_mode='recessive', pathogenicity=pathogenicity,
#             annotations=gcnv_annotations_2, annotations_secondary=selected_transcript_annotations,
#         )
#
#         # Search works with a different number of samples within the family
#         missing_gt_gcnv_variant = {
#             **GCNV_VARIANT4, 'genotypes': {k: v for k, v in GCNV_VARIANT4['genotypes'].items() if k != 'I000005_hg00732'}
#         }
#         self._assert_expected_search(
#             [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, missing_gt_gcnv_variant]],
#             inheritance_mode='compound_het', pathogenicity=pathogenicity,
#             annotations=gcnv_annotations_2, annotations_secondary=selected_transcript_annotations,
#             sample_data={**EXPECTED_SAMPLE_DATA, 'SV_WES': SV_WES_SAMPLE_DATA['SV_WES'][:1] + SV_WES_SAMPLE_DATA['SV_WES'][2:]}
#
#         )
#
#         # Do not return pairs where annotations match in a non-paired gene
#         self._assert_expected_search(
#             [GCNV_VARIANT3], inheritance_mode='recessive',
#             annotations=gcnv_annotations_2, annotations_secondary=selected_transcript_annotations,
#         )

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

    def test_in_silico_filter(self):
        main_in_silico = {'eigen': '3.5', 'mut_taster': 'N', 'vest': 0.5}
        self._assert_expected_search(
           [VARIANT1, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], in_silico=main_in_silico,
        )

        in_silico = {**main_in_silico, 'requireScore': True}
        in_silico.pop('eigen')
        self._assert_expected_search(
           [VARIANT4, MITO_VARIANT2], in_silico=in_silico,
        )

        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT], in_silico={'gnomad_noncoding': 0.5, 'requireScore': True},
        )

#         sv_in_silico = {'strvctvre': 0.1, 'requireScore': True}
#         self._assert_expected_search(
#             [GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], omit_data_type='SNV_INDEL', in_silico=sv_in_silico,
#         )
#
#         self._assert_expected_search(
#             [SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, in_silico=sv_in_silico,
#         )

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
            [VARIANT4, VARIANT2, MITO_VARIANT2, MITO_VARIANT3, MITO_VARIANT1, VARIANT3, VARIANT1],
            sort='protein_consequence',
        )
        self._reset_search_families()

#         self._assert_expected_search(
#             [_sorted(GCNV_VARIANT2, [0]), _sorted(GCNV_VARIANT3, [0]), _sorted(GCNV_VARIANT4, [0]),
#              _sorted(GCNV_VARIANT1, [3])], omit_data_type='SNV_INDEL', sort='protein_consequence',
#         )

        # self._assert_expected_search(
        #     [_sorted(VARIANT4, [2, 2]), _sorted(GCNV_VARIANT2, [4.5, 0]), _sorted(GCNV_VARIANT3, [4.5, 0]), _sorted(GCNV_VARIANT4, [4.5, 0]),
        #      _sorted(GCNV_VARIANT1, [4.5, 3]), _sorted(VARIANT2, [12, 12]),
        #      _sorted(MULTI_FAMILY_VARIANT, [26, 27]), _sorted(VARIANT1, [None, None])], sort='protein_consequence',
        # )

#         self._assert_expected_search(
#             [_sorted(SV_VARIANT1, [11]), _sorted(SV_VARIANT2, [12]), _sorted(SV_VARIANT3, [12]), _sorted(SV_VARIANT4, [12])],
#              sample_data=SV_WGS_SAMPLE_DATA, sort='protein_consequence',
#         )

        self._assert_expected_search(
            [VARIANT4, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, MITO_VARIANT1, SELECTED_ANNOTATION_TRANSCRIPT_MULTI_FAMILY_VARIANT],
            # [_sorted(VARIANT4, [2, 2]), _sorted(SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, [12, 26]),
            #  _sorted(SELECTED_ANNOTATION_TRANSCRIPT_MULTI_FAMILY_VARIANT, [26, 26])],
            sort='protein_consequence',
            annotations={'other': ['non_coding_transcript_exon_variant'], 'splice_ai': '0'}, cached_variant_fields=[
                {'selectedTranscript': None},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][5]},
                {},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][3]},
            ],
        )

        self._assert_expected_search(
            [VARIANT1, MITO_VARIANT3, VARIANT2, MITO_VARIANT1, MULTI_FAMILY_VARIANT, VARIANT4, MITO_VARIANT2], sort='pathogenicity', annotations=None,
            # [_sorted(VARIANT1, [4]), _sorted(VARIANT2, [8]), _sorted(MULTI_FAMILY_VARIANT, [12.5]),
            #  _sorted(VARIANT4, [12.5]), GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], sort='pathogenicity',
        )

        self._set_single_family_search()
        self._assert_expected_search(
            [VARIANT1, MITO_VARIANT3, VARIANT2, MITO_VARIANT1, VARIANT3, VARIANT4, MITO_VARIANT2],
            sort='pathogenicity_hgmd',
        )

        self._assert_expected_search(
            [VARIANT2, MITO_VARIANT1, MITO_VARIANT2, VARIANT4, VARIANT1, MITO_VARIANT3, VARIANT3],
            sort='gnomad',
        )

        self._reset_search_families()
        self._assert_expected_search(
            [VARIANT1, MULTI_FAMILY_VARIANT, VARIANT4, VARIANT2, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            # [_sorted(VARIANT1, [0]), _sorted(MULTI_FAMILY_VARIANT, [0]), _sorted(VARIANT4, [0]),
            #  _sorted(VARIANT2, [0.28899794816970825]), GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            sort='gnomad_exomes',
        )

        # self._assert_expected_search(
        #     [_sorted(VARIANT4, [2]),_sorted(MULTI_FAMILY_VARIANT, [4]), _sorted(VARIANT1, [9]),
        #      _sorted(VARIANT2, [28]), _sorted(GCNV_VARIANT3, [35]), _sorted(GCNV_VARIANT4, [115]),
        #      _sorted(GCNV_VARIANT2, [284]), _sorted(GCNV_VARIANT1, [1763])],
        #     sort='callset_af',
        # )

        self._assert_expected_search(
            [MITO_VARIANT1, MITO_VARIANT2, VARIANT4, MITO_VARIANT3, MULTI_FAMILY_VARIANT, VARIANT1, VARIANT2],
            sort='callset_af',
        )

        self._assert_expected_search(
            [VARIANT4, VARIANT2, VARIANT1, MULTI_FAMILY_VARIANT, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            # [_sorted(VARIANT4, [-29.899999618530273]), _sorted(VARIANT2, [-20.899999618530273]),
            #  _sorted(VARIANT1, [-4.668000221252441]), _sorted(MULTI_FAMILY_VARIANT, [-2.753999948501587]),
            #  GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            sort='cadd',
        )

        self._assert_expected_search(
            [VARIANT4, VARIANT2, VARIANT1, MULTI_FAMILY_VARIANT, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='revel',
        )

        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT2, VARIANT4, VARIANT1, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='splice_ai',
        )

        self._assert_expected_search(
            [VARIANT2, VARIANT1, MULTI_FAMILY_VARIANT, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='alphamissense',
        )

        sort = 'in_omim'
        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT2, VARIANT4, VARIANT1, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort=sort
        )

#        self._assert_expected_search(
#             [_sorted(GCNV_VARIANT3, [-1]), _sorted(GCNV_VARIANT4, [-1]), _sorted(GCNV_VARIANT1, [0]), _sorted(GCNV_VARIANT2, [0])],
#             omit_data_type='SNV_INDEL', sort=sort, sort_metadata=OMIM_SORT_METADATA,
#         )
#
#         self._assert_expected_search(
#             [_sorted(MULTI_FAMILY_VARIANT, [0, -2]), _sorted(VARIANT2, [0, -1]), _sorted(VARIANT4, [0, -1]),
#              _sorted(GCNV_VARIANT3, [0, -1]), _sorted(GCNV_VARIANT4, [0, -1]), _sorted(GCNV_VARIANT1, [0, 0]),
#              _sorted(GCNV_VARIANT2, [0, 0]),  _sorted(VARIANT1, [1, 0])], sort=sort, sort_metadata=OMIM_SORT_METADATA,
#         )

        Omim.objects.filter(gene_id=61).delete()
        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, VARIANT1, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort=sort,
        )

        sort = 'constraint'
        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, VARIANT1, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort=sort,
        )

#         self._assert_expected_search(
#             [_sorted(GCNV_VARIANT3, [3]), _sorted(GCNV_VARIANT4, [3]), _sorted(GCNV_VARIANT1, [None]),
#              _sorted(GCNV_VARIANT2, [None])], omit_data_type='SNV_INDEL', sort=sort, sort_metadata=constraint_sort_metadata,
#         )
#
#         self._assert_expected_search(
#             [_sorted(VARIANT2, [2, 2]), _sorted(GCNV_VARIANT3, [3, 3]), _sorted(GCNV_VARIANT4, [3, 3]),
#              _sorted(MULTI_FAMILY_VARIANT, [4, 2]), _sorted(VARIANT4, [4, 4]), _sorted(VARIANT1, [None, None]),
#              _sorted(GCNV_VARIANT1, [None, None]), _sorted(GCNV_VARIANT2, [None, None])],
#             sort=sort, sort_metadata=constraint_sort_metadata,
#         )

        self._set_single_family_search()
        self._assert_expected_search([VARIANT2, VARIANT3, VARIANT1, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='prioritized_gene')

        self._set_multi_project_search()
        self._assert_expected_search(
            [MULTI_PROJECT_VARIANT1, MULTI_PROJECT_VARIANT2, VARIANT3, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3, PROJECT_2_VARIANT],
            sort='family_guid',
        )

#         # size sort only applies to SVs, so has no impact on other variant
#         self._assert_expected_search(
#             [_sorted(GCNV_VARIANT1, [-171766]), _sorted(GCNV_VARIANT2, [-17768]), _sorted(GCNV_VARIANT4, [-14487]),
#              _sorted(GCNV_VARIANT3, [-2666]), VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], sort='size',
#         )
#
#         self._assert_expected_search(
#             [_sorted(SV_VARIANT4, [-46343]), _sorted(SV_VARIANT1, [-104]), _sorted(SV_VARIANT2, [-50]),
#              _sorted(SV_VARIANT3, [-50])], sample_data=SV_WGS_SAMPLE_DATA, sort='size',
#         )
#
        # sort applies to compound hets
        self._set_single_family_search()
        self._assert_expected_search(
            [[VARIANT4, VARIANT3], VARIANT2, MITO_VARIANT3],
            sort='revel', inheritance_mode='recessive', **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId':  'ENSG00000097046'}, {'selectedGeneId':  'ENSG00000097046'}], {}, {},
            ],
        )

        self._assert_expected_search(
            [[VARIANT3, VARIANT4], VARIANT2, MITO_VARIANT3],
            sort='splice_ai', inheritance_mode='recessive', **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId':  'ENSG00000097046'}, {'selectedGeneId':  'ENSG00000097046'}], {}, {},
            ],
        )

        self._assert_expected_search(
            [[VARIANT4, VARIANT3], MITO_VARIANT3, VARIANT2],
            sort='callset_af', inheritance_mode='recessive', **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}], {}, {},
            ],
        )

#     def test_multi_data_type_comp_het_sort(self):
#         self._assert_expected_search(
#             [[_sorted(VARIANT4, [2, 2]), _sorted(VARIANT3, [26, 27])],
#              _sorted(GCNV_VARIANT3, [4.5, 0]), [_sorted(GCNV_VARIANT3, [0]), _sorted(GCNV_VARIANT4, [0])],
#              [_sorted(GCNV_VARIANT4, [4.5, 0]), _sorted(MULTI_DATA_TYPE_COMP_HET_VARIANT2, [12, 12])],
#              _sorted(VARIANT2, [12, 12])],
#             sort='protein_consequence', inheritance_mode='recessive', **COMP_HET_ALL_PASS_FILTERS,
#         )
#
#         self._assert_expected_search(
#             [[_sorted(GCNV_VARIANT4, [-14487]), _sorted(GCNV_VARIANT3, [-2666])],
#              [_sorted(GCNV_VARIANT4, [-14487]), MULTI_DATA_TYPE_COMP_HET_VARIANT2],
#              [VARIANT3, VARIANT4]],
#             sort='size', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS,
#         )
#
#         self._assert_expected_search(
#             [[_sorted(MULTI_DATA_TYPE_COMP_HET_VARIANT2, [8]), GCNV_VARIANT4],
#              [_sorted(VARIANT3, [12.5]), _sorted(VARIANT4, [12.5])],
#              [GCNV_VARIANT3, GCNV_VARIANT4]],
#             sort='pathogenicity', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS,
#         )
#
#         self._assert_expected_search(
#             [[_sorted(VARIANT4, [-0.6869999766349792]), _sorted(VARIANT3, [0])], _sorted(VARIANT2, [0]),
#              [_sorted(MULTI_DATA_TYPE_COMP_HET_VARIANT2, [0]), GCNV_VARIANT4],
#              GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]],
#             sort='mut_pred', inheritance_mode='recessive', **COMP_HET_ALL_PASS_FILTERS,
#         )
#
#         self._assert_expected_search(
#             [[_sorted(VARIANT3, [-0.009999999776482582]), _sorted(VARIANT4, [0])],
#              [_sorted(MULTI_DATA_TYPE_COMP_HET_VARIANT2, [0]), GCNV_VARIANT4],
#              [GCNV_VARIANT3, GCNV_VARIANT4]],
#             sort='splice_ai', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS,
#         )
#
#         self._assert_expected_search(
#             [[_sorted(GCNV_VARIANT3, [-0.7860000133514404]), _sorted(GCNV_VARIANT4, [-0.7099999785423279])],
#              [_sorted(GCNV_VARIANT4, [-0.7099999785423279]), MULTI_DATA_TYPE_COMP_HET_VARIANT2],
#              [VARIANT3, VARIANT4]],
#             sort='strvctvre', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS,
#         )
#
#         await self._assert_expected_search(
#             [[_sorted(VARIANT4, [2]), _sorted(VARIANT3, [4])],
#              [_sorted(MULTI_DATA_TYPE_COMP_HET_VARIANT2, [28]), _sorted(GCNV_VARIANT4, [115])],
#              [_sorted(GCNV_VARIANT3, [35]), _sorted(GCNV_VARIANT4, [115])]],
#             sort='callset_af', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS,
#         )
#
#         self._assert_expected_search(
#             [[_sorted(VARIANT3, [0]), _sorted(VARIANT4, [0])],
#              [_sorted(MULTI_DATA_TYPE_COMP_HET_VARIANT2, [0.28899794816970825]), GCNV_VARIANT4],
#              [GCNV_VARIANT3, GCNV_VARIANT4]],
#             sort='gnomad_exomes', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS,
#         )
#
#         self._assert_expected_search(
#             [[_sorted(VARIANT3, [0, -2]), _sorted(VARIANT4, [0, -1])],
#              [_sorted(GCNV_VARIANT3, [-1]), _sorted(GCNV_VARIANT4, [-1])],
#              [_sorted(GCNV_VARIANT4, [0, -1]), _sorted(MULTI_DATA_TYPE_COMP_HET_VARIANT2, [1, -1])]],
#             sort='in_omim', sort_metadata=OMIM_SORT_METADATA, inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS,
#         )
