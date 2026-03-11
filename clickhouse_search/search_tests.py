from datetime import timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.db import connections
from django.urls.base import reverse
import json
import mock
import random
import responses

from clickhouse_search.models.gt_stats_models import ProjectGtStatsSnvIndel, \
    ProjectsToGtStatsGRCh37SnvIndel, ProjectsToGtStatsSnvIndel, ProjectsToGtStatsMito, ProjectsToGtStatsSv, \
    GtStatsDictGRCh37SnvIndel, GtStatsDictSnvIndel, GtStatsDictMito, GtStatsDictSv
from clickhouse_search.models.postgres_dicts import AffectedDict, SexDict
from clickhouse_search.models.reference_data_models import ClinvarMvSnvIndel, ClinvarSearchMvSnvIndel, ClinvarMvMito, \
    ClinvarSearchMvMito, ClinvarMvGRCh37SnvIndel, ClinvarSearchMvGRCh37SnvIndel, HgmdMv, HgmdSearchMv,  \
    DbnsfpSnvIndelMv, DbnsfpSnvIndelDict, EigenMv, EigenDict, SpliceAiMv, SpliceAiDict, GnomadNonCodingConstraintDict, \
    DbnsfpGRCh37SnvIndelMv, DbnsfpGRCh37SnvIndelDict, EigenGRCh37Mv, EigenGRCh37Dict, SpliceAiGRCh37Mv, SpliceAiGRCh37Dict, \
    DbnsfpMitoMv, DbnsfpMitoDict, MitimpactMv, MitimpactDict, HmtvarMv, HmtvarDict, LocalconstraintmitoMv, \
    LocalconstraintmitoDict, GnomadGenomesMv, GnomadGenomesDict, GnomadExomesMv, GnomadExomesDict, TopmedMv, TopmedDict, \
    GnomadGenomesGRCh37Mv, GnomadGenomesGRCh37Dict, GnomadExomesGRCh37Mv, GnomadExomesGRCh37Dict, TopmedGRCh37Mv, \
    TopmedGRCh37Dict, GnomadmitoMv, GnomadmitoDict, GnomadmitoheteroplasmyMv, GnomadmitoheteroplasmyDict, HelixmitoMv, \
    HelixmitoDict, HelixmitoheteroplasmyMv, HelixmitoheteroplasmyDict, ScreenDict, MitomapMv, MitomapDict, Absplice2Mv, \
    Absplice2Dict, PromoterAIMv, PromoterAIDict, PextSnvIndelMv, PextSnvIndelDict, PextMitoMv, PextMitoDict
from clickhouse_search.models.search_models import EntriesSnvIndel, VariantsSnvIndel
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
    DEFAULT_PROJECT_FAMILIES, SINGLE_FAMILY_PROJECT_FAMILIES, SV_PROJECT_FAMILIES, MULTI_PROJECT_PROJECT_FAMILIES, \
    format_cached_variant
from reference_data.models import Omim
from seqr.models import Project, Family, Sample, VariantSearch, VariantSearchResults
from seqr.utils.search.utils import query_variants, variant_lookup, get_variant_query_gene_counts, get_single_variant, InvalidSearchException
from seqr.views.apis.data_manager_api import trigger_delete_project
from seqr.views.utils.json_utils import DjangoJSONEncoderWithSets
from seqr.views.utils.test_utils import AnvilAuthenticationTestCase, GENE_VARIANT_FIELDS
from seqr.views.apis.variant_search_api import query_variants_handler, get_variant_gene_breakdown


class ClickhouseSearchTestCase(AnvilAuthenticationTestCase):

    @classmethod
    def setUpClass(cls):
        # Atomic transactions prevent the clickhouse/ postgres connection from working properly,
        # so disable them for the initial fixture loading
        original_enter_atomics = cls._enter_atomics
        cls._enter_atomics = lambda: {}
        super().setUpClass()
        cls._enter_atomics = original_enter_atomics

    @classmethod
    def tearDownClass(cls):
        for conn in connections.all(initialized_only=True):
            conn.close()
        for db_name in cls._databases_names():
            call_command(
                "flush",
                verbosity=0,
                interactive=False,
                database=db_name,
                reset_sequences=False,
                allow_cascade=False,
                inhibit_post_migrate=False,
            )

    @classmethod
    def setUpTestData(cls):
        AffectedDict.reload()
        SexDict.reload()
        for view in [
            ProjectsToGtStatsGRCh37SnvIndel, ProjectsToGtStatsSnvIndel, ProjectsToGtStatsMito, ProjectsToGtStatsSv,
            ClinvarMvSnvIndel, ClinvarSearchMvSnvIndel, ClinvarMvMito, ClinvarSearchMvMito, ClinvarMvGRCh37SnvIndel,
            ClinvarSearchMvGRCh37SnvIndel, HgmdMv, HgmdSearchMv, DbnsfpSnvIndelMv, EigenMv, SpliceAiMv,
            DbnsfpGRCh37SnvIndelMv, EigenGRCh37Mv, SpliceAiGRCh37Mv, DbnsfpMitoMv, MitimpactMv, HmtvarMv, LocalconstraintmitoMv,
            GnomadGenomesMv, GnomadExomesMv, TopmedMv, GnomadGenomesGRCh37Mv, GnomadExomesGRCh37Mv,TopmedGRCh37Mv,
            GnomadmitoMv, GnomadmitoheteroplasmyMv, HelixmitoMv, HelixmitoheteroplasmyMv, MitomapMv, Absplice2Mv,
            PromoterAIMv, PextSnvIndelMv, PextMitoMv
        ]:
            view.refresh()
        for dictionary in [
            GtStatsDictGRCh37SnvIndel, GtStatsDictSnvIndel, GtStatsDictMito, GtStatsDictSv, DbnsfpSnvIndelDict,
            EigenDict, SpliceAiDict, GnomadNonCodingConstraintDict, DbnsfpGRCh37SnvIndelDict, EigenGRCh37Dict,
            SpliceAiGRCh37Dict, DbnsfpMitoDict, MitimpactDict, HmtvarDict, LocalconstraintmitoDict, GnomadGenomesDict,
            GnomadExomesDict, TopmedDict, GnomadGenomesGRCh37Dict, GnomadExomesGRCh37Dict, TopmedGRCh37Dict,
            GnomadmitoDict, GnomadmitoheteroplasmyDict, HelixmitoDict, HelixmitoheteroplasmyDict, ScreenDict,
            MitomapDict, Absplice2Dict, PromoterAIDict, PextSnvIndelDict, PextMitoDict
        ]:
            dictionary.reload()
        Project.objects.update(genome_version='38')
        super().setUpTestData()


class ClickhouseSearchTests(ClickhouseSearchTestCase):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'variant_searches', 'reference_data', 'clickhouse_search', 'clickhouse_transcripts']

    def setUp(self):
        patcher = mock.patch('seqr.utils.redis_utils.redis.StrictRedis')
        self.mock_redis = patcher.start().return_value
        self.mock_redis.get.return_value = None
        self.addCleanup(patcher.stop)

        patcher = mock.patch('seqr.models.VariantSearchResults._compute_guid')
        self.mock_results_guid = patcher.start()
        self.mock_results_guid.return_value = random.randint(1000, 10000)  # nosec
        self.addCleanup(patcher.stop)

        # TODO remove
        self.families = Family.objects.filter(guid__in=['F000003_3', 'F000002_2', 'F000005_5'])
        self.user = User.objects.get(username='test_user')

        self.search_model = VariantSearch.objects.create(search={'inheritance': {'mode': 'de_novo'}, 'freqs': {'callset': {'ac': 1000}}})
        self.results_model = VariantSearchResults.objects.create(variant_search=self.search_model)
        self.results_model.families.set(self.families)

        super().setUp()

    def set_cache(self, cached):
        self.mock_redis.get.return_value = json.dumps(cached)

    def assert_cached_results(self, expected_results, sort='xpos', cache_key=None):
        cache_key = cache_key or f'search_results__{self.results_model.guid}__{sort}'
        self.mock_redis.set.assert_called_with(cache_key, mock.ANY)
        self.assertEqual(json.loads(self.mock_redis.set.call_args.args[1]), expected_results)
        self.mock_redis.expire.assert_called_with(cache_key, timedelta(weeks=2))

    def _execute_search(self, sort='xpos', inheritance_mode=None, inheritance_filter=None, quality_filter=None, project_families=None, request_body=None, check_login=None, query_params=None, **search_kwargs):
        search_hash = random.randint(1000, 10000)  # nosec
        self.mock_results_guid.return_value = f'VRS{search_hash:07d}'
        url = reverse(query_variants_handler, args=[search_hash])

        search_body = {
            'inheritance': {'mode': inheritance_mode},
            'freqs': {'callset': {'ac': 1000}},
            'qualityFilter': quality_filter,
            **(search_kwargs or {}),
        }
        if inheritance_filter is not None:
            search_body['inheritance']['filter'] = inheritance_filter

        request_data = {
            **(request_body or {'projectFamilies': DEFAULT_PROJECT_FAMILIES if project_families is None else project_families }), 'search': search_body,
        }

        if check_login:
            check_login(url, request_data=request_data)

        query_string = '&'.join([f'{key}={value}' for key, value in {'sort': sort, **(query_params or {})}.items()])
        response = self.client.post(f'{url}?{query_string}', content_type='application/json', data=json.dumps(request_data))

        return response, search_hash, search_body

    def _assert_expected_search(self, expected_results, results_page=None, gene_counts=None, cached_variant_fields=None, sort='xpos', response_search=None, format_cache_key=None, project_families=None, is_37=False, **kwargs):
        response, search_hash, search_body = self._execute_search(project_families=project_families, sort=sort, **kwargs)
        self.assertEqual(response.status_code, 200)
        expected_response = {
            'searchedVariants': results_page or expected_results,
            'search': {
                'search': {**search_body, **(response_search or {})},
                'projectFamilies': DEFAULT_PROJECT_FAMILIES if project_families is None else project_families,
                'totalResults': len(expected_results),
            },

        }
        if expected_results:
            expected_response.update({
                'genesById': mock.ANY,
                'locusListsByGuid': mock.ANY,
                'mmeSubmissionsByGuid': mock.ANY,
                'phenotypeGeneScores': mock.ANY,
                'rnaSeqData': mock.ANY,
                'savedVariantsByGuid': mock.ANY,
                'variantFunctionalDataByGuid': mock.ANY,
                'variantNotesByGuid': mock.ANY,
                'variantTagsByGuid': mock.ANY,
                'totalSampleCounts': mock.ANY,
            })
            if not is_37:
                expected_response['omimIntervals'] = mock.ANY
        self.assertDictEqual(response.json(), expected_response)

        cache_key = format_cache_key() if format_cache_key else f'search_results__VRS{search_hash:07d}__{sort}'
        if cache_key:
            cached_variants = self._format_cached_variants(expected_results, cached_variant_fields=cached_variant_fields)
            self.assert_cached_results(cached_variants, sort=sort, cache_key=cache_key)
        else:
            self.mock_redis.get.assert_not_called()
            self.mock_redis.set.assert_not_called()

        if gene_counts:
            gene_breakdown_url = reverse(get_variant_gene_breakdown, args=[search_hash])
            gene_breakdown_response = self.client.get(gene_breakdown_url)
            self.assertEqual(gene_breakdown_response.status_code, 200)
            self.assertDictEqual(gene_breakdown_response.json(), {
                'searchGeneBreakdown': {str(search_hash): gene_counts},
                'genesById': mock.ANY,
            })
            # TODO test genesById context

        return response.json()

    def _assert_expected_search_error(self, error, **kwargs):
        response, _, _ = self._execute_search(**kwargs)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': error})

    def _assert_expected_variants(self, variants, expected_results, cache_key=None, results_page=None, format_cached_variants=None, sort='xpos', **kwargs):
        encoded_variants = self._encode_variants(variants)
        self.assertListEqual(encoded_variants, results_page or expected_results)
        if cache_key:
            cached_variants = format_cached_variants(expected_results, **kwargs) if format_cached_variants else expected_results
            self.assert_cached_results(cached_variants, sort=sort, cache_key=cache_key)
        else:
            self.mock_redis.get.assert_not_called()
            self.mock_redis.set.assert_not_called()

    @staticmethod
    def _encode_variants(variants):
        return json.loads(json.dumps(variants, cls=DjangoJSONEncoderWithSets))

    def _format_cached_variants(self, variants, cached_variant_fields=None):
        cached_variants = [
            self._get_cached_variant(variant, (cached_variant_fields[i] if cached_variant_fields else None))
            for i, variant in enumerate(variants)
        ]
        return {'all_results': cached_variants, 'total_results': len(variants)}

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

    def _set_grch37_search(self):
        Project.objects.filter(id=1).update(genome_version='37')
        Sample.objects.filter(sample_id='HG00732').update(is_active=False)
        Sample.objects.exclude(dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS).update(is_active=False)

    def test_single_family_search(self):
        variant_gene_counts = {
            'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
            'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2}},
            'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}}
        }
        self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT3, VARIANT4], gene_counts=variant_gene_counts, locus={'rawItems': '1:1-100000000'},
            exclude_svs=True, project_families=SINGLE_FAMILY_PROJECT_FAMILIES, check_login=self.check_collaborator_login,
        )

        self._assert_expected_search(
            [MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], gene_counts=MITO_GENE_COUNTS, locus={'rawItems': 'M:1-100000000'},
            exclude_svs=False, project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], gene_counts=GCNV_GENE_COUNTS,
            locus=None, annotations={'structural': COMP_HET_ALL_PASS_FILTERS['annotations']['structural']},
            project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self.login_manager()
        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4], gene_counts=SV_GENE_COUNTS,
            project_families=SV_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [VARIANT1, SV_VARIANT1, SV_VARIANT2, VARIANT2, VARIANT3, VARIANT4, SV_VARIANT3, GCNV_VARIANT1,
                         GCNV_VARIANT2, GCNV_VARIANT3, SV_VARIANT4, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            gene_counts={**variant_gene_counts, **MITO_GENE_COUNTS, **GCNV_GENE_COUNTS, **SV_GENE_COUNTS, 'ENSG00000277258': {'total': 2, 'families': {'F000002_2': 2}}},
            project_families=[*SINGLE_FAMILY_PROJECT_FAMILIES, *SV_PROJECT_FAMILIES],
        )

        self._set_grch37_search()
        self._assert_expected_search([GRCH37_VARIANT], project_families=SINGLE_FAMILY_PROJECT_FAMILIES, is_37=True)

    def test_standard_searches(self):
        self._assert_expected_search(
            [VARIANT1, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], cached_variant_fields=[
                {'selectedTranscript': None}, {}, {}, {},
            ], project_families=SINGLE_FAMILY_PROJECT_FAMILIES, **VariantSearch.objects.get(name='De Novo/Dominant Restrictive').search,
            check_login=self.check_collaborator_login,
        )

        self._assert_expected_search(
            [VARIANT1, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], cached_variant_fields=[
                {'selectedTranscript': None}, {}, {}, {},
            ], project_families=SINGLE_FAMILY_PROJECT_FAMILIES, **VariantSearch.objects.get(name='De Novo/Dominant Permissive').search,
        )

        self._assert_expected_search([VARIANT2, MITO_VARIANT3], cached_variant_fields=[
            {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][0]}, {},
        ], project_families=SINGLE_FAMILY_PROJECT_FAMILIES, **VariantSearch.objects.get(name='Recessive Restrictive').search)

        self._assert_expected_search([VARIANT2, MITO_VARIANT3], cached_variant_fields=[
            {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][0]}, {},
        ], project_families=SINGLE_FAMILY_PROJECT_FAMILIES, **VariantSearch.objects.get(name='Recessive Permissive').search)

    def test_single_project_search(self):
        variant_gene_counts = {
            'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2, 'F000003_3': 1}},
            'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2, 'F000003_3': 1}},
            'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
            **MITO_GENE_COUNTS,
        }
        self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2,
             GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], check_login=self.check_collaborator_login,
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
        gene_counts = {
            **GENE_COUNTS,
            **MITO_GENE_COUNTS,
            **GCNV_GENE_COUNTS,
            'ENSG00000277258': {'total': 2, 'families': {'F000002_2': 2, 'F000011_11': 1}},
        }
        locus = {'rawItems': 'chr1:1-100000000, chr13:1-100000000, chr14:1-100000000, chr16:1-100000000, chr17:1-100000000, M:1-100000000'}
        self._assert_expected_search(
            [PROJECT_2_VARIANT, MULTI_PROJECT_VARIANT1, MULTI_PROJECT_VARIANT2, VARIANT3, VARIANT4,
             GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            gene_counts=gene_counts, locus=locus, check_login=self.check_collaborator_login, project_families=MULTI_PROJECT_PROJECT_FAMILIES,
        )

        self.login_manager()
        self._assert_expected_search(
            [PROJECT_2_VARIANT, MULTI_PROJECT_VARIANT1, SV_VARIANT1, SV_VARIANT2, MULTI_PROJECT_VARIANT2, VARIANT3,
             VARIANT4, SV_VARIANT3, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, SV_VARIANT4, GCNV_VARIANT4, MITO_VARIANT1,
             MITO_VARIANT2, MITO_VARIANT3], gene_counts={**gene_counts, **SV_GENE_COUNTS}, locus=locus, project_families=[
                *MULTI_PROJECT_PROJECT_FAMILIES, *SV_PROJECT_FAMILIES,
            ]
        )

    def test_both_sample_types_search(self):
        Sample.objects.filter(dataset_type='MITO').update(is_active=False)

        # One family (F000011_11) in a multi-project search has identical exome and genome data.
        self._add_sample_type_samples('WES', individual__family__guid='F000011_11')

        self._assert_expected_search(
            MULTI_PROJECT_BOTH_SAMPLE_TYPE_VARIANTS, gene_counts=GENE_COUNTS, locus={'rawItems': 'chr1:1-100000000'},
            project_families=MULTI_PROJECT_PROJECT_FAMILIES, check_login=self.check_collaborator_login,
        )

        self._add_sample_type_samples('WGS', guid__in=['S000132_hg00731'])

        # Variant 1 is de novo in exome but inherited and homozygous in genome.
        # Variant 2 is inherited and homozygous in exome and de novo and homozygous in genome, so it fails de-novo inheritance when parental data is missing in genome.
        # Variant 3 is inherited in both sample types.
        # Variant 4 is de novo in exome, but inherited in genome in the same parent that has variant 3.
        self._assert_expected_search(
            [VARIANT1_BOTH_SAMPLE_TYPES, VARIANT2_BOTH_SAMPLE_TYPES, VARIANT3_BOTH_SAMPLE_TYPES, VARIANT4_BOTH_SAMPLE_TYPES,
             GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            inheritance_mode='any_affected', project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [VARIANT2_BOTH_SAMPLE_TYPES, VARIANT3_BOTH_SAMPLE_TYPES, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT4],
            inheritance_mode='any_affected', quality_filter={'min_gq': 40, 'min_qs': 20}, project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [VARIANT1_BOTH_SAMPLE_TYPES, VARIANT4_BOTH_SAMPLE_TYPES, GCNV_VARIANT1],
            inheritance_mode='de_novo', quality_filter=None, project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self._add_sample_type_samples('WGS', guid__in=['S000133_hg00732', 'S000134_hg00733'])
        self._assert_expected_search(
            [VARIANT1_BOTH_SAMPLE_TYPES, VARIANT2_BOTH_SAMPLE_TYPES, VARIANT3_BOTH_SAMPLE_TYPES,
             VARIANT4_BOTH_SAMPLE_TYPES, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            inheritance_mode='any_affected', project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [VARIANT1_BOTH_SAMPLE_TYPES, VARIANT2_BOTH_SAMPLE_TYPES, VARIANT4_BOTH_SAMPLE_TYPES, GCNV_VARIANT1],
            inheritance_mode='de_novo', project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [VARIANT2_BOTH_SAMPLE_TYPES, GCNV_VARIANT1],
            inheritance_mode='de_novo', quality_filter={'min_gq': 40}, project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self.maxDiff = None
        self._assert_expected_search(
            [VARIANT1_BOTH_SAMPLE_TYPES, VARIANT2_BOTH_SAMPLE_TYPES,
             [{**VARIANT2_BOTH_SAMPLE_TYPES, 'selectedMainTranscriptId': 'ENST00000450625'}, GCNV_VARIANT4],
             [VARIANT3_BOTH_SAMPLE_TYPES, VARIANT4_BOTH_SAMPLE_TYPES],
             GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]], project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
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
            inheritance_mode=inheritance_mode, check_login=self.check_collaborator_login,
        )

        self.login_manager()
        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4], inheritance_mode=inheritance_mode,
            project_families=SV_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [SV_VARIANT2], inheritance_mode=inheritance_mode, annotations=NEW_SV_FILTER, project_families=SV_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [GCNV_VARIANT3], inheritance_mode=inheritance_mode, annotations=NEW_SV_FILTER,
        )

        inheritance_mode = 'de_novo'
        self._assert_expected_search(
            [VARIANT1, FAMILY_3_VARIANT, VARIANT4, GCNV_VARIANT1, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            inheritance_mode=inheritance_mode, annotations=None,
        )

        sv_affected = {'affected': {'I000019_na21987': 'N'}}
        self._assert_expected_search(
            [SV_VARIANT1], inheritance_mode=inheritance_mode, inheritance_filter=sv_affected, project_families=SV_PROJECT_FAMILIES,
        )

        inheritance_mode = 'x_linked_recessive'
        self._assert_expected_search([], inheritance_mode=inheritance_mode)
        # self._assert_expected_search([], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA_WITH_SEX)

        inheritance_mode = 'homozygous_recessive'
        self._assert_expected_search(
            [VARIANT2, GCNV_VARIANT3, MITO_VARIANT3],
            inheritance_mode=inheritance_mode,
        )

        self._assert_expected_search(
            [PROJECT_2_VARIANT1, VARIANT2, GCNV_VARIANT3, MITO_VARIANT3], project_families=MULTI_PROJECT_PROJECT_FAMILIES,
            inheritance_mode=inheritance_mode, locus={'rawItems': 'chr1:1-100000000, chr14:1-100000000, chr16:1-100000000, chr17:1-100000000, M:1-100000000'},
        )

        self._assert_expected_search(
            [SV_VARIANT4], inheritance_mode=inheritance_mode, inheritance_filter=sv_affected, project_families=SV_PROJECT_FAMILIES,
        )

        gt_inheritance_filter = {'genotype': {'I000006_hg00733': 'ref_ref', 'I000005_hg00732': 'has_alt'}}
        self._assert_expected_search([VARIANT2, GCNV_VARIANT3], inheritance_filter=gt_inheritance_filter, project_families=SINGLE_FAMILY_PROJECT_FAMILIES)

        self._assert_expected_search(
            [VARIANT2, GCNV_VARIANT2, GCNV_VARIANT3], inheritance_mode='any_affected', inheritance_filter={'affected': {
                'I000004_hg00731': 'N', 'I000005_hg00732': 'A', 'I000006_hg00733': 'U',
            }}, project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        inheritance_mode = 'compound_het'
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

        self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2]], inheritance_mode=inheritance_mode,
            **COMP_HET_ALL_PASS_FILTERS, gene_counts={'ENSG00000171621': {'total': 2, 'families': {'F000014_14': 2}}},
            inheritance_filter=sv_affected, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000171621'}, {'selectedGeneId': 'ENSG00000171621'}],
            ], project_families=SV_PROJECT_FAMILIES,
        )

        inheritance_mode = 'recessive'
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
            project_families=MULTI_PROJECT_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [VARIANT2, [VARIANT3, VARIANT4], MITO_VARIANT3], inheritance_mode=inheritance_mode, cached_variant_fields=[
                {},
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}], {},
            ], locus=None, project_families=SINGLE_FAMILY_PROJECT_FAMILIES, **ALL_SNV_INDEL_PASS_FILTERS,
        )

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

        self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2], SV_VARIANT4], inheritance_mode=inheritance_mode,
            **COMP_HET_ALL_PASS_FILTERS, gene_counts={
                'ENSG00000171621': {'total': 2, 'families': {'F000014_14': 2}},
                'ENSG00000184986': {'total': 1, 'families': {'F000014_14': 1}},
            }, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000171621'}, {'selectedGeneId': 'ENSG00000171621'}], {},
            ], project_families=SV_PROJECT_FAMILIES, inheritance_filter=sv_affected,
        )

        # Test deletion in trans with hom alt snp/indel
        for sample in Sample.objects.filter(individual__family_id=14):
            sample.pk = None
            sample.dataset_type = 'SNV_INDEL'
            sample.save()
        self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2], [SV_VARIANT1, PROJECT_4_COMP_HET_VARIANT], PROJECT_4_COMP_HET_VARIANT, SV_VARIANT4],
            inheritance_mode=inheritance_mode, inheritance_filter=sv_affected, **COMP_HET_ALL_PASS_FILTERS,
            cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000171621'}, {'selectedGeneId': 'ENSG00000171621'}],
                [{'selectedGeneId': 'ENSG00000171621'}, {'selectedGeneId': 'ENSG00000171621'}],
                {}, {},
            ], project_families=SV_PROJECT_FAMILIES,
        )

        self._set_grch37_search()
        self._assert_expected_search([], inheritance_mode=inheritance_mode, **COMP_HET_ALL_PASS_FILTERS, project_families=SINGLE_FAMILY_PROJECT_FAMILIES)
        self._assert_expected_search(
            [GRCH37_VARIANT], inheritance_mode=inheritance_mode, inheritance_filter={'allowNoCall': True},
            **COMP_HET_ALL_PASS_FILTERS, project_families=SINGLE_FAMILY_PROJECT_FAMILIES, is_37=True,
        )

    def test_exclude_previous_search_results(self):
        self.mock_results_guid.return_value = 'VRS00079516'
        VariantSearchResults.objects.create(variant_search_id=79516, search_hash='abc1234')
        self.mock_redis.get.side_effect = [None, None, None, json.dumps({'all_results': [
            VARIANT1, VARIANT2, [VARIANT3, VARIANT2], [GCNV_VARIANT4, GCNV_VARIANT3],
        ]})]
        self.mock_redis.keys.side_effect = [[], ['search_results__abc1234__gnomad']]

        exclude = {'previousSearch': True, 'previousSearchHash': 'abc1234'}
        self._assert_expected_search(
            [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, VARIANT4], GCNV_VARIANT3, MITO_VARIANT3],
            inheritance_mode='recessive', **COMP_HET_ALL_PASS_FILTERS,
            exclude=exclude, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000277258'}, {'selectedGeneId': 'ENSG00000277258'}],
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}],
                {}, {},
            ], check_login=self.check_collaborator_login,
        )

        self.mock_redis.get.side_effect = [None, None, json.dumps({'all_results': [
            [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, VARIANT4], GCNV_VARIANT3, MITO_VARIANT3,
        ]})]
        self.mock_redis.keys.side_effect = [[], ['search_results__abc1234__gnomad']]
        self._assert_expected_search(
            [VARIANT2, [GCNV_VARIANT3, GCNV_VARIANT4]], exclude=exclude, **COMP_HET_ALL_PASS_FILTERS,
            inheritance_mode='recessive', cached_variant_fields=[
                {}, [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
            ],
        )

    def test_quality_filter(self):
        quality_filter = {'vcf_filter': 'pass'}
        self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2],
            quality_filter=quality_filter, check_login=self.check_collaborator_login,
        )

        self.login_manager()
        self._assert_expected_search(
            [SV_VARIANT4], quality_filter=quality_filter, project_families=SV_PROJECT_FAMILIES,
        )

        gcnv_quality_filter = {'min_gq': 40, 'min_qs': 20, 'min_hl': 5}
        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT3], quality_filter=gcnv_quality_filter,
        )

        self._assert_expected_search(
            [], annotations=NEW_SV_FILTER, quality_filter=gcnv_quality_filter, omit_data_type='SNV_INDEL',
        )

        sv_quality_filter = {'min_gq_sv': 40}
        self._assert_expected_search(
            [SV_VARIANT3, SV_VARIANT4], quality_filter=sv_quality_filter, annotations=None, project_families=SV_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [], annotations=NEW_SV_FILTER, quality_filter=sv_quality_filter, project_families=SV_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, MITO_VARIANT1, MITO_VARIANT2], quality_filter={'min_gq': 40, 'min_qs': 30, 'vcf_filter': 'pass'},
            annotations=None,
        )

        self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            quality_filter={'min_gq': 60, 'min_qs': 10, 'affected_only': True},
        )

        self._assert_expected_search(
            [SV_VARIANT4], quality_filter={'min_gq_sv': 60, 'affected_only': True}, project_families=SV_PROJECT_FAMILIES,
        )

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
            [GRCH37_VARIANT], quality_filter=quality_filter, inheritance_filter={'allowNoCall': True}, is_37=True,
        )

    def test_location_search(self):
        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4], **LOCATION_SEARCH, cached_variant_fields=[
                {'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}
            ], check_login=self.check_collaborator_login,
        )

        sv_locus = {'rawItems': 'ENSG00000275023, ENSG00000171621'}
        self._assert_expected_search(
            [GCNV_VARIANT3, GCNV_VARIANT4], locus=sv_locus,
        )

        self.login_manager()
        # For gene search, return SVs annotated in gene even if they fall outside the gene interval
        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2], locus=sv_locus, project_families=SV_PROJECT_FAMILIES,
        )
        self._assert_expected_search(
            [SV_VARIANT1], locus={'rawItems': 'chr1:9297894-9369732%10'}, project_families=SV_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [VARIANT1, VARIANT2, GCNV_VARIANT1, GCNV_VARIANT2, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], exclude={
                'rawItems': ','.join([LOCATION_SEARCH['locus']['rawItems'], sv_locus['rawItems']])
            }, locus=None,
        )

        self._assert_expected_search(
            [SV_VARIANT2, SV_VARIANT3], exclude=sv_locus, project_families=SV_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT, VARIANT4],
            locus={'rawItems': f'{GENE_IDS[1]}\n1:91500851-91525764'}, exclude=None, cached_variant_fields=[
                {'selectedGeneId': 'ENSG00000177000'}, {'selectedGeneId': None},
            ],
        )

        self._add_sample_type_samples('WES', individual__family__guid='F000014_14')
        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2, MULTI_PROJECT_GCNV_VARIANT3, GCNV_VARIANT4], locus=sv_locus,
            project_families=[*SINGLE_FAMILY_PROJECT_FAMILIES, *SV_PROJECT_FAMILIES],
        )

        self._set_grch37_search()
        self._assert_expected_search([GRCH37_VARIANT], locus={'rawItems': '7:143268894-143271480'}, is_37=True)

    def test_variant_id_search(self):
        self._assert_expected_search([VARIANT1], **VARIANT_ID_SEARCH, check_login=self.check_collaborator_login)

        self._assert_expected_search(
            [VARIANT1], locus={'rawVariantItems': VARIANT_IDS[0]},
        )

        self._assert_expected_search(
            [],locus={'rawVariantItems': VARIANT_IDS[1]},
        )

    @mock.patch('seqr.utils.search.utils.MAX_GENES_FOR_FILTER', 2)
    @mock.patch('seqr.utils.search.utils.MAX_NO_LOCATION_COMP_HET_FAMILIES', 1)
    @mock.patch('clickhouse_search.search.MAX_VARIANTS', 3)
    def test_invalid_search(self):
        url = reverse(query_variants_handler, args=['not_a_hash'])
        self.check_require_login(url)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {'error': 'Invalid search hash: not_a_hash'})
        self.login_collaborator()

        self._assert_expected_search_error('Invalid search: no projects/ families specified', project_families=[])

        self._assert_expected_search_error(
            'Invalid variants: chr2-A-C', locus={'rawVariantItems': 'chr2-A-C'},
        )

        self._assert_expected_search_error('Invalid variants: rs9876', locus={'rawVariantItems': 'rs9876'})

        self._assert_expected_search_error(
            'Invalid genes/intervals: chr27:1234-5678, chr2:40-400000000, ENSG00012345',
            locus={'rawItems': 'chr27:1234-5678,2:40-400000000, ENSG00012345'},
        )

        self._assert_expected_search_error('Too many genes/intervals', locus={'rawItems': '1:1-1000, 2:2000-3000, 3:4000-5000'})

        build_specific_genes = 'DDX11L1, OR4F29, ENSG00000223972, ENSG00000256186'
        self._assert_expected_search_error('Invalid genes/intervals: OR4F29, ENSG00000256186', locus={'rawItems': build_specific_genes})

        self._assert_expected_search_error(
            'Cannot specify both Location and Excluded Genes/Intervals',
            locus={'rawItems': build_specific_genes}, exclude={'rawItems': build_specific_genes},
        )

        self._assert_expected_search_error('Invalid genes/intervals: OR4F29, ENSG00000256186', exclude={'rawItems': build_specific_genes})

        self._assert_expected_search_error('This search returned too many results')

        self._assert_expected_search_error(
            'ClinVar pathogenicity vus is both included and excluded',
            pathogenicity={'clinvar': ['pathogenic', 'vus']}, exclude={'clinvar': ['benign', 'vus']},
        )

        self._assert_expected_search_error('Annotations must be specified to search for compound heterozygous variants', inheritance_mode='recessive')

        self._assert_expected_search_error(
            'Location must be specified to search for compound heterozygous variants across many families',
            annotations={'frameshift': ['frameshift_variant']}, inheritance_mode='recessive',
        )

        self._assert_expected_search_error(
            'Phenotype sort is only supported for single-family search.',
            sort='prioritized_gene', annotations={'frameshift': ['frameshift_variant']},
        )

        self._assert_expected_search_error('seqr AC frequency of at least 5000 must be specified to search across multiple families', freqs={})

        self._assert_expected_search_error(
            'Inheritance based search is disabled in families with no data loaded for affected individuals',
            inheritance_mode='recessive', project_families=[{'projectGuid': 'R0001_1kg', 'familyGuids': ['F000005_5']}],
        )

        no_sv_project_families = [{'projectGuid': 'R0001_1kg', 'familyGuids': ['F000003_3']}]
        self._assert_expected_search_error(
            'Unable to search against dataset type "SV"', pathogenicity={}, annotations={'structural': ['DEL']},
            project_families=no_sv_project_families,
        )

        self._assert_expected_search_error(
            'Unable to search for comp-het pairs with dataset type "SV". This may be because inheritance based search is disabled in families with no loaded affected individuals',
            inheritance_mode='recessive', annotations={'structural': ['DEL']}, annotations_secondary={'frameshift': ['frameshift_variant']}, project_families=no_sv_project_families,
        )

        self._assert_expected_search_error(
            'Inheritance based search is disabled in families with no data loaded for affected individuals',
            inheritance_mode='recessive', inheritance_filter={'affected': {'I000007_na20870': 'N'}}, project_families=no_sv_project_families,
        )

        self._assert_expected_search_error('Inheritance must be specified if custom affected status is set', inheritance_filter={'affected': {'I000007_na20870': 'N'}})

        self._assert_expected_search_error(
            'Invalid custom inheritance', project_families=no_sv_project_families, inheritance_filter={'genotype': {'I000004_hg00731': 'ref_ref'}},
        )

        self._assert_expected_search_error(
            'No search data found for families no_individuals', project_families=[{'projectGuid': 'R0001_1kg', 'familyGuids': ['F000013_13']}],
        )

        self._assert_expected_search_error('Location must be specified to search across multiple projects', project_families=MULTI_PROJECT_PROJECT_FAMILIES)

        Sample.objects.filter(guid='S000143_na20885').update(sample_id='HG00732')
        self._assert_expected_search_error(
            'The following samples are incorrectly configured and have different affected statuses in different projects: '
            'HG00732 (1kg project nåme with uniçøde/ Test Reprocessed Project)',
            locus={'rawItems': GENE_IDS[0]}, freqs={'callset': {'ac': 1000}}, project_families=MULTI_PROJECT_PROJECT_FAMILIES,
        )

        self._set_grch37_search()
        self._assert_expected_search_error('Invalid genes/intervals: DDX11L1, ENSG00000223972', locus={'rawItems': build_specific_genes})

        self._assert_expected_search_error(
            'Searching across multiple genome builds is not supported. Remove projects with differing genome builds from search: 37 - 1kg project nåme with uniçøde; 38 - Test Reprocessed Project',
            project_families=MULTI_PROJECT_PROJECT_FAMILIES,
        )

        #  TODO test once have export tests in this file
        self.set_cache({'total_results': 20000})
        with self.assertRaises(InvalidSearchException) as cm:
            self._assert_expected_search([], page=1, num_results=2, load_all=True, project_families=SINGLE_FAMILY_PROJECT_FAMILIES)
        self._assert_expected_search_error('Unable to export more than 1000 variants (20000 requested)')

    @mock.patch('seqr.utils.search.utils.LiftOver')
    def test_variant_lookup(self, mock_liftover):
        # TODO
        mock_convert_coordinate = mock_liftover.return_value.convert_coordinate
        mock_convert_coordinate.side_effect = lambda chrom, pos: [(chrom, pos + 10000)]

        variants = variant_lookup(self.user, '1-10439-AC-A', '38')
        self._assert_expected_variants(variants, [VARIANT_LOOKUP_VARIANT], 'variant_lookup_results__1-10439-AC-A__38')

        with self.assertRaises(ObjectDoesNotExist) as cm:
            variant_lookup(self.user, '1-91511686-TCA-G', '38')
        self.assertEqual(str(cm.exception), 'Variant not present in seqr')

        self.set_cache([VARIANT_LOOKUP_VARIANT])
        cached_variants = variant_lookup(self.user, '1-91511686-TCA-G', '38')
        self.assertListEqual([VARIANT_LOOKUP_VARIANT], cached_variants)
        self.mock_redis.get.assert_called_with('variant_lookup_results__1-91511686-TCA-G__38')

        self.set_cache(None)
        variants = variant_lookup(self.user, '7-143270172-A-G', '37')
        grch37_lookup_variant = {
            **{k: v for k, v in GRCH37_VARIANT.items() if k not in {'familyGuids', 'genotypes'}},
            'familyGenotypes': {GRCH37_VARIANT['familyGuids'][0]: sorted([
                {k: v for k, v in g.items() if k != 'individualGuid'} for g in GRCH37_VARIANT['genotypes'].values()
            ], key=lambda x: x['sampleId'], reverse=True)},
        }
        cache_key = 'variant_lookup_results__7-143270172-A-G__37'
        self._assert_expected_variants(variants, [grch37_lookup_variant], cache_key)

        variants = variant_lookup(self.user, '7-143270172-A-G', '37', hom_only=True, affected_only=True)
        self._assert_expected_variants(variants, [grch37_lookup_variant], f'{cache_key}__affected__hom')

        # Lookup works if variant is only present on a different build
        variants = variant_lookup(self.user, '7-143260172-A-G', '38')
        self._assert_expected_variants(variants, [grch37_lookup_variant], 'variant_lookup_results__7-143260172-A-G__38')
        mock_liftover.assert_called_with('hg38', 'hg19')
        mock_convert_coordinate.assert_called_with('chr7', 143260172)

        liftover_variant = {
            **VARIANT_LOOKUP_VARIANT,
            'familyGenotypes': {
                family_guid: gts
                for family_guid, gts in VARIANT_LOOKUP_VARIANT['familyGenotypes'].items() if family_guid != 'F000014_14'
            },
        }
        del liftover_variant['liftedFamilyGuids']
        variants = variant_lookup(self.user, '1-439-AC-A', '37')
        cache_key = 'variant_lookup_results__1-439-AC-A__37'
        self._assert_expected_variants(variants, [liftover_variant], cache_key)
        mock_liftover.assert_called_with('hg19', 'hg38')
        mock_convert_coordinate.assert_called_with('chr1', 439)

        hom_only_lookup_variant = {
            **liftover_variant,
            'familyGenotypes': {
                **liftover_variant['familyGenotypes'],
                'F000002_2': [gt for gt in liftover_variant['familyGenotypes']['F000002_2'] if gt['sampleType'] == 'WGS'],
            },
        }
        variants = variant_lookup(self.user, '1-10439-AC-A', '38', hom_only=True)
        self._assert_expected_variants(variants, [hom_only_lookup_variant], 'variant_lookup_results__1-10439-AC-A__38__hom')
        variants = variant_lookup(self.user, '1-439-AC-A', '37', hom_only=True)
        self._assert_expected_variants(variants, [hom_only_lookup_variant], f'{cache_key}__hom')

        variants = variant_lookup(self.user, 'M-4429-G-A', '38')
        self._assert_expected_variants(variants, [{
            **{k: v for k, v in MITO_VARIANT1.items() if k not in {'familyGuids', 'genotypes'}},
            'familyGenotypes': {MITO_VARIANT1['familyGuids'][0]: [
                {k: v for k, v in g.items() if k != 'individualGuid'} for g in MITO_VARIANT1['genotypes'].values()
            ]},
        }], 'variant_lookup_results__M-4429-G-A__38')

        with self.assertRaises(ObjectDoesNotExist) as cm:
            variant_lookup(self.user, 'M-4429-G-A', '38', hom_only=True)
        self.assertEqual(str(cm.exception), 'Variant not present in seqr')

        with self.assertRaises(InvalidSearchException) as cm:
            variant_lookup(self.user, 'phase2_DEL_chr14_4640', '37')
        self.assertEqual(str(cm.exception), 'SV variants are not available for GRCh37')

        with self.assertRaises(InvalidSearchException) as cm:
            variant_lookup(self.user, 'phase2_DEL_chr14_4640', '38')
        self.assertEqual(str(cm.exception), 'Sample type must be specified to look up a structural variant')

        variants = variant_lookup(self.user, 'phase2_DEL_chr14_4640', '38', sample_type='WGS')
        cache_key = 'variant_lookup_results__phase2_DEL_chr14_4640__38'
        self._assert_expected_variants(variants, [SV_LOOKUP_VARIANT, GCNV_LOOKUP_VARIANT], cache_key)

        affected_only_lookup_variant = {
            **GCNV_LOOKUP_VARIANT,
            'familyGenotypes': {
                family_guid: gts for family_guid, gts in GCNV_LOOKUP_VARIANT['familyGenotypes'].items() if family_guid != 'F000002_2_x'
            },
        }
        variants = variant_lookup(self.user, 'phase2_DEL_chr14_4640', '38', sample_type='WGS', affected_only=True)
        self._assert_expected_variants(variants, [SV_LOOKUP_VARIANT, affected_only_lookup_variant], f'{cache_key}__affected')

        # reciprocal overlap does not meet the threshold for smaller events
        variants = variant_lookup(self.user, 'suffix_140608_DUP', '38', sample_type='WES')
        cache_key = 'variant_lookup_results__suffix_140608_DUP__38'
        self._assert_expected_variants(variants, [GCNV_LOOKUP_VARIANT], cache_key)

        variants = variant_lookup(self.user, 'suffix_140608_DUP', '38', sample_type='WES', affected_only=True)
        self._assert_expected_variants(variants, [affected_only_lookup_variant], f'{cache_key}__affected')

        variants = variant_lookup(self.user, 'suffix_140593_DUP', '38', sample_type='WES')
        self._assert_expected_variants(variants, [GCNV_LOOKUP_VARIANT_3], 'variant_lookup_results__suffix_140593_DUP__38')

    def test_get_single_variant(self):
        #  TODO
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
        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            freqs={'callset': {'ac': 7}, **sv_callset_filter}, check_login=self.check_collaborator_login,
        )

        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], freqs={'callset': {'ac': 1000, 'hh': 1}},
        )

        self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, GCNV_VARIANT3, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], freqs={'callset': {'ac': 7, 'hh': 0}, 'sv_callset': {'ac': 50}},
        )

        self.login_manager()
        self._assert_expected_search(
            [SV_VARIANT1], freqs={'sv_callset': {'ac': 1}}, project_families=SV_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2], freqs={'callset': {'ac': 1000}, 'gnomad_genomes': {'af': 0.03}, 'gnomad_mito': {'af': 0.005}},
        )

        self._assert_expected_search(
            [VARIANT2, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2], freqs={'callset': {'ac': 1000}, 'gnomad_genomes': {'af': 0.05, 'hh': 0}, 'gnomad_mito': {'af': 0.005}},
        )

        self._assert_expected_search(
            [VARIANT4, GCNV_VARIANT3, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            freqs={'callset': {'ac': 1000}, 'topmed': {'af': 0.05, 'hh': 1}, 'sv_callset': {'ac': 50}},
        )

        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT3, SV_VARIANT4], freqs={'gnomad_svs': {'af': 0.001}}, project_families=SV_PROJECT_FAMILIES,
        )
        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT3, SV_VARIANT4], freqs={'gnomad_svs': {'ac': 4000}}, project_families=SV_PROJECT_FAMILIES,
        )

        # seqr af filter is ignored for SNV_INDEL
        self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT3, VARIANT4, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            freqs={'callset': {'af': 0.2},  **sv_callset_filter}, project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2],
            freqs={'callset': {'ac': 6}, 'gnomad_genomes': {'ac': 50}, 'gnomad_mito': {'ac': 10}}, project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT3, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            freqs={'callset': {}, 'gnomad_genomes': {'af': None}}, project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        annotations = {'splice_ai': '0.0'}  # Ensures no variants are filtered out by annotation/path filters
        self._assert_expected_search(
            [VARIANT1, VARIANT4, MITO_VARIANT1],
            freqs={'gnomad_genomes': {'af': 0.002, 'hh': 10}, 'gnomad_mito': {'ac': 1000}},
            annotations=annotations, pathogenicity={'clinvar': ['pathogenic', 'likely_pathogenic', 'vus']},
            project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [VARIANT2, VARIANT4, MITO_VARIANT1], freqs={'gnomad_genomes': {'af': 0.002}, 'gnomad_mito': {'ac': 1000}},
            annotations=annotations, pathogenicity={'clinvar': ['pathogenic', 'conflicting_p_lp', 'vus']}, project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

    def test_annotations_filter(self):
        self._assert_expected_search([VARIANT2], pathogenicity={'hgmd': ['hgmd_other']}, check_login=self.check_collaborator_login)
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

        self.login_manager()
        self._assert_expected_search([SV_VARIANT1], annotations=annotations, project_families=SV_PROJECT_FAMILIES)

        annotations['splice_ai'] = '0.005'
        annotations['structural'] = ['gCNV_DUP', 'DEL']
        self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT2],
            annotations=annotations, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][0]},
                {'selectedTranscript': None},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][1]},
                {}, {}, {}, {}, {},
            ]
        )

        annotations['missense'] = []
        annotations['in_frame'] = []
        del annotations['splice_ai']
        self._assert_expected_search(
            [GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], annotations=annotations,
        )

        self._assert_expected_search([SV_VARIANT1, SV_VARIANT4], annotations=annotations, project_families=SV_PROJECT_FAMILIES)

        annotations = {'other': ['non_coding_transcript_exon_variant__canonical', 'non_coding_transcript_exon_variant']}
        self._assert_expected_search(
            [VARIANT1, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_3, MITO_VARIANT1, MITO_VARIANT3],
            pathogenicity=pathogenicity, annotations=annotations, cached_variant_fields=[
                {'selectedTranscript': None},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][5]},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][3]},
                {}, {},
            ], project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        locus = {'rawItems': f'{GENE_IDS[1]}\n1:11785723-91525764'}
        self._assert_expected_search(
            [SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2],
            locus=locus, pathogenicity=None, annotations=annotations,
            cached_variant_fields=[{
                'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][5],
            }],
        )

        annotations['other'].append('intron_variant')
        self._assert_expected_search(
            [SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT],
            annotations=annotations, locus=locus, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][5]},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][1]},
            ],
        )

        annotations['other'] = annotations['other'][:1]
        annotations['splice_ai'] = '0.005'
        self._assert_expected_search(
            [VARIANT1, VARIANT3, MITO_VARIANT1, MITO_VARIANT3],
            pathogenicity=pathogenicity, annotations=annotations, locus=None, cached_variant_fields=[
                {'selectedTranscript': None}, {'selectedTranscript': None}, {}, {},
            ], project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        annotations['extended_splice_site'] = ['extended_intronic_splice_region_variant']
        self._assert_expected_search(
            [VARIANT1, VARIANT3, VARIANT4, MITO_VARIANT1, MITO_VARIANT3],
            pathogenicity=pathogenicity, annotations=annotations, cached_variant_fields=[
                {'selectedTranscript': None},
                {'selectedTranscript': None},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][0]},
                {}, {},
            ], project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        annotations = {'extended_splice_site': ['5_prime_UTR_variant']}
        self._assert_expected_search(
            [selected_transcript_variant_2], pathogenicity=None, annotations=annotations, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][1]},
            ], project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        annotations['extended_splice_site'].append('extended_intronic_splice_region_variant')
        self._assert_expected_search(
            [selected_transcript_variant_2, VARIANT4], annotations=annotations, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][1]},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][0]},
            ], project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        annotations = {'motif_feature': ['TF_binding_site_variant'], 'regulatory_feature': ['regulatory_region_variant']}
        self._assert_expected_search(
            [VARIANT3, VARIANT4], annotations=annotations, pathogenicity=None, project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self._set_grch37_search()
        self._assert_expected_search([], pathogenicity=pathogenicity, annotations=snv_38_only_annotations)
        annotations['missense'] = ['missense_variant']
        self._assert_expected_search(
            [GRCH37_VARIANT], pathogenicity=None, annotations=annotations,
            cached_variant_fields=[{'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[11][0]}], is_37=True,
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
            check_login=self.check_collaborator_login,
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
                {'selectedGeneId': 'ENSG00000277258'},
            ]],
        )

        self._assert_expected_search(
            [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4], GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode='recessive',
            annotations={**annotations_1, **gcnv_annotations_1}, annotations_secondary={**annotations_2, **gcnv_annotations_2}, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][0]}, [
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]},
                {'selectedGeneId': 'ENSG00000277258'},
            ], [
                {'selectedGeneId':  'ENSG00000097046', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][0]},
                {'selectedGeneId':  'ENSG00000097046', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][1]},
            ], {}, [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}]],
        )

        locus = {'rawItems': 'ENSG00000277258,ENSG00000275023'}
        self._assert_expected_search(
            [MULTI_DATA_TYPE_COMP_HET_VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode='recessive',
            annotations={**annotations_1, 'structural': ['gCNV_DEL'], 'structural_consequence': ['INTRONIC']},
            annotations_secondary={**annotations_2, **gcnv_annotations_1},
            locus=locus, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]}, [
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]},
                {'selectedGeneId': 'ENSG00000277258'},
            ], [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}]],
        )

        self._assert_expected_search(
            [MULTI_DATA_TYPE_COMP_HET_VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4]],
            inheritance_mode='recessive', annotations={**annotations_1, 'structural': [], 'structural_consequence': []},
            annotations_secondary=gcnv_annotations_2, locus=locus, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]}, [
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]},
                {'selectedGeneId': 'ENSG00000277258'},
            ]],
        )

        sv_annotations_1 = {'structural': ['INS', 'LOF']}
        sv_annotations_2 = {'structural': ['DEL', 'gCNV_DUP'], 'structural_consequence': ['INTRONIC']}

        self.login_manager()
        inheritance_filter = {'affected': {'I000019_na21987': 'N'}}
        self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2]], inheritance_mode='compound_het', locus=None,
            annotations=sv_annotations_1, annotations_secondary=sv_annotations_2, inheritance_filter=inheritance_filter,
            project_families=SV_PROJECT_FAMILIES, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000171621'}, {'selectedGeneId': 'ENSG00000171621'}],
            ],
        )

        self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2], SV_VARIANT4], inheritance_mode='recessive',
            annotations=sv_annotations_2, annotations_secondary=sv_annotations_1, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000171621'}, {'selectedGeneId': 'ENSG00000171621'}], {},
            ], inheritance_filter=inheritance_filter, project_families=SV_PROJECT_FAMILIES,
        )

        pathogenicity = {'clinvar': ['likely_pathogenic', 'conflicting_p_lp', 'conflicting_no_p', 'vus']}
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
                {'selectedGeneId': 'ENSG00000277258'},
            ], [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}]],
        )

        self._assert_expected_search(
            [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4], MITO_VARIANT3],
            inheritance_mode='recessive', pathogenicity=pathogenicity,
            annotations=gcnv_annotations_2, annotations_secondary=gcnv_annotations_1, cached_variant_fields=[{}, [
                {'selectedGeneId': 'ENSG00000277258'},
                {'selectedGeneId': 'ENSG00000277258'},
            ], {}, [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}], {}],
        )

        selected_transcript_annotations = {'other': ['non_coding_transcript_exon_variant']}
        self._assert_expected_search(
            [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], GCNV_VARIANT3, MITO_VARIANT3],
            inheritance_mode='recessive', pathogenicity=pathogenicity,
            annotations=gcnv_annotations_2, annotations_secondary=selected_transcript_annotations, cached_variant_fields=[{}, [
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': None},
                {'selectedGeneId': 'ENSG00000277258'},
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
            inheritance_mode='recessive', pathogenicity=pathogenicity, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][5]}, [
                    {'selectedGeneId': 'ENSG00000097046', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][0]},
                    {'selectedGeneId': 'ENSG00000097046', 'selectedTranscript': None},
                ], {},
            ],
        )

        self._add_sample_type_samples('WES', individual__family__guid='F000014_14')
        self._assert_expected_search(
            [MULTI_DATA_TYPE_COMP_HET_VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], MULTI_PROJECT_GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode='recessive',
            annotations={**annotations_1, **gcnv_annotations_1}, annotations_secondary={**annotations_2, **gcnv_annotations_2},
            locus={'rawItems': 'ENSG00000277258,ENSG00000275023'}, pathogenicity=pathogenicity, cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]}, [
                {'selectedGeneId': 'ENSG00000277258', 'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[2][3]},
                {'selectedGeneId': 'ENSG00000277258'},
            ], {}, [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}]],
            project_families=[*MULTI_PROJECT_PROJECT_FAMILIES, *SV_PROJECT_FAMILIES],
        )

        # Search works with a different number of samples within the family
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
                {'selectedGeneId': 'ENSG00000277258'},
            ]], project_families=[{**DEFAULT_PROJECT_FAMILIES[0], 'familyGuids': ['F000002_2_x', *DEFAULT_PROJECT_FAMILIES[0]['familyGuids'][1:]]}],
        )

    def test_in_silico_filter(self):
        main_in_silico = {'eigen': '3.5', 'mut_taster': 'N', 'vest': 0.5}
        self._assert_expected_search(
           [VARIANT1, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], in_silico=main_in_silico,
            check_login=self.check_collaborator_login,
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

        self.login_manager()
        self._assert_expected_search(
            [SV_VARIANT4], in_silico=sv_in_silico, project_families=SV_PROJECT_FAMILIES,
        )

        self._set_grch37_search()
        self._assert_expected_search([GRCH37_VARIANT], in_silico=main_in_silico, is_37=True)

    def test_sort(self):
        self._assert_expected_search(
            [VARIANT4, GCNV_VARIANT3, GCNV_VARIANT4, GCNV_VARIANT2, GCNV_VARIANT1, VARIANT2, MITO_VARIANT2, MITO_VARIANT3, MITO_VARIANT1, VARIANT3, VARIANT1],
            sort='protein_consequence', check_login=self.check_collaborator_login, project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self.login_manager()
        self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4],
             sort='protein_consequence', project_families=SV_PROJECT_FAMILIES,
        )

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

        self._assert_expected_search(
            [VARIANT1, MITO_VARIANT3, VARIANT2, MITO_VARIANT1, VARIANT3, VARIANT4,  GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT2],
            sort='pathogenicity_hgmd', project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        sorted_variants = [MITO_VARIANT1, MITO_VARIANT2, VARIANT4, VARIANT2, VARIANT3, MITO_VARIANT3, VARIANT1, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4]
        self._assert_expected_search(sorted_variants, sort='gnomad', project_families=SINGLE_FAMILY_PROJECT_FAMILIES)

        self._assert_expected_search(
            sorted_variants, results_page=[VARIANT3, MITO_VARIANT3, VARIANT1, GCNV_VARIANT1], sort='gnomad', query_params={'page': 2, 'per_page': 4}, project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )
        self._assert_expected_search(
            sorted_variants, results_page=[GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], sort='gnomad', query_params={'page': 3, 'per_page': 4}, project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

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

        self._assert_expected_search([VARIANT2, VARIANT3, VARIANT1, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='prioritized_gene', project_families=SINGLE_FAMILY_PROJECT_FAMILIES)

        self._assert_expected_search(
            [MULTI_PROJECT_VARIANT1, MULTI_PROJECT_VARIANT2, VARIANT3, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3, PROJECT_2_VARIANT],
            sort='family_guid', locus={'rawItems': 'chr1:1-100000000, chr14:1-100000000, chr16:1-100000000, chr17:1-100000000, M:1-100000000'},
            project_families=MULTI_PROJECT_PROJECT_FAMILIES,
        )

        # size sort only applies to SVs, so has no impact on other variant
        self._assert_expected_search(
            [GCNV_VARIANT1, GCNV_VARIANT4, GCNV_VARIANT2, GCNV_VARIANT3, VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sort='size', locus=None,
        )

        self._assert_expected_search(
            [SV_VARIANT4, SV_VARIANT1, SV_VARIANT3, SV_VARIANT2], sort='size', project_families=SV_PROJECT_FAMILIES,
        )

        # sort applies to compound hets
        self._assert_expected_search(
            [[VARIANT4, VARIANT3], VARIANT2, MITO_VARIANT3],
            sort='revel', inheritance_mode='recessive', **ALL_SNV_INDEL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId':  'ENSG00000097046'}, {'selectedGeneId':  'ENSG00000097046'}], {}, {},
            ], project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [[VARIANT3, VARIANT4], VARIANT2, MITO_VARIANT3],
            sort='splice_ai', inheritance_mode='recessive', **ALL_SNV_INDEL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId':  'ENSG00000097046'}, {'selectedGeneId':  'ENSG00000097046'}], {}, {},
            ], project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

        self._assert_expected_search(
            [MITO_VARIANT3, [VARIANT4, VARIANT3], VARIANT2],
            sort='callset_af', inheritance_mode='recessive', **ALL_SNV_INDEL_PASS_FILTERS, cached_variant_fields=[
                {}, [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}], {},
            ], project_families=SINGLE_FAMILY_PROJECT_FAMILIES,
        )

    def test_multi_data_type_comp_het_sort(self):
        self._assert_expected_search(
            [[VARIANT4, VARIANT3], GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4],
             [GCNV_VARIANT4, MULTI_DATA_TYPE_COMP_HET_VARIANT2], VARIANT2, MITO_VARIANT3],
            sort='protein_consequence', inheritance_mode='recessive', **COMP_HET_ALL_PASS_FILTERS, cached_variant_fields=[
                [{'selectedGeneId': 'ENSG00000097046'}, {'selectedGeneId': 'ENSG00000097046'}], {},
                [{'selectedGeneId': 'ENSG00000275023'}, {'selectedGeneId': 'ENSG00000275023'}],
                [{'selectedGeneId': 'ENSG00000277258'}, {'selectedGeneId': 'ENSG00000277258'}], {}, {}],
            check_login=self.check_collaborator_login,
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
        request_body = {
            'allGenomeProjectFamilies': '38',
            'includeNoAccessProjects': True,
        }
        self._assert_expected_search_error(
            'Including external projects is only available when searching for a single gene', request_body=request_body,
            check_login=self.check_require_login,
        )

        annotations = {
            'missense': ['missense_variant'],
            'other': ['non_coding_transcript_exon_variant'],
        }
        freqs = {
            'callset': {'ac': 3000},
            'gnomad_genomes': {'af': 0.003},
            'gnomad_exomes': {'af': 0.003},
        }
        locus = {'rawItems': 'ENSG00000097046'}
        response_search = {'no_access_project_genome_version': '38'}
        variant4 = {**VARIANT4, 'selectedMainTranscriptId': 'ENST00000350997', 'numFamilies': 3}
        del variant4['familyGuids']
        del variant4['genotypes']
        self._assert_expected_search(
            [variant4], request_body=request_body, response_search=response_search,
            cached_variant_fields=[{'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][1]}],
            annotations=annotations, freqs=freqs, locus=locus, project_families=[],
        )

        freqs = {'callset': freqs['callset']}
        variant3 = {**VARIANT3, 'selectedMainTranscriptId': 'ENST00000497611', 'numFamilies': 4}
        del variant3['familyGuids']
        del variant3['genotypes']
        self._assert_expected_search(
            [variant3, variant4], request_body=request_body, response_search=response_search,
            cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][3]},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][1]},
            ],
            annotations=annotations, freqs=freqs, locus=locus, project_families=[],
        )

        self._assert_expected_search_error(
            'Compound heterozygous search is not supported when including external projects',
            request_body=request_body, locus=locus, annotations=annotations, inheritance_mode='recessive',
        )

        self._assert_expected_search(
            [], request_body=request_body, response_search=response_search, project_families=[],
            annotations=annotations, freqs=freqs, locus=locus, inheritance_mode='homozygous_recessive',
        )

        variant3['numFamilies'] = 1
        variant4['numFamilies'] = 1
        self._assert_expected_search(
            [variant3, variant4], request_body=request_body, response_search=response_search,
            cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][3]},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][1]},
            ],
            annotations=annotations, freqs=freqs, locus=locus, inheritance_mode='de_novo', project_families=[],
        )

        self.login_collaborator()
        project_families = [{'projectGuid': 'R0001_1kg', 'familyGuids': mock.ANY}]
        self._assert_expected_search([
                {**FAMILY_3_VARIANT, 'selectedMainTranscriptId': 'ENST00000497611'},
                {**VARIANT4, 'selectedMainTranscriptId': 'ENST00000350997'},
            ], request_body=request_body, response_search=response_search, project_families=project_families,
            cached_variant_fields=[
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[3][3]},
                {'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[4][1]},
            ],
            annotations=annotations, freqs=freqs, locus=locus, inheritance_mode='de_novo',
        )

        locus['rawItems'] = 'ENSG00000171621'
        other_project_variant = {**PROJECT_4_COMP_HET_VARIANT, 'numFamilies': 1}
        del other_project_variant['familyGuids']
        del other_project_variant['genotypes']
        self._assert_expected_search(
            [other_project_variant], request_body=request_body, response_search=response_search,
            project_families=project_families, cached_variant_fields=[{'selectedTranscript': CACHED_CONSEQUENCES_BY_KEY[22][0]}],
            annotations=annotations, freqs=freqs, locus=locus, inheritance_mode='de_novo',
        )

        locus['rawItems'] = 'ENSG00000229905'
        self._assert_expected_search(
            [], request_body=request_body, response_search=response_search,
            project_families=project_families, annotations=annotations, freqs=freqs, locus=locus, inheritance_mode='de_novo',
        )

    def test_search_context(self):
        response_json = self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2,
             GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3],
            check_login=self.check_collaborator_login,
        )
        #  TODO test pa gene in saved variant test
        #         expected_pa_gene = {**expected_gene, 'locusListGuids': ['LL00049_pid_genes_autosomal_do'], 'panelAppDetail': mock.ANY}
        #             self.assertDictEqual(
        #                 response_json['genesById']['ENSG00000227232']['panelAppDetail'], {LOCUS_LIST_GUID: {'confidence': '3', 'moi': 'BIALLELIC, autosomal or pseudoautosomal'}}
        #             )
        expected_gene = {k: mock.ANY for k in GENE_VARIANT_FIELDS}
        expected_gene['locusListGuids'] = []
        self.assertDictEqual(response_json['genesById'], {
            'ENSG00000097046': expected_gene,
            'ENSG00000277258': expected_gene,
            'ENSG00000177000': expected_gene,
            'ENSG00000275023': expected_gene,
        })
        self.assertDictEqual(response_json['locusListsByGuid'], {'LL00049_pid_genes_autosomal_do': {'intervals': [mock.ANY, mock.ANY]}})
        self.assertSetEqual(
            set(response_json['locusListsByGuid']['LL00049_pid_genes_autosomal_do']['intervals'][0].keys()),
            {'locusListGuid', 'locusListIntervalGuid', 'genomeVersion', 'chrom', 'start', 'end'}
        )
        self.assertDictEqual(response_json['mmeSubmissionsByGuid'], {})
        self.assertDictEqual(response_json['phenotypeGeneScores'],{'I000004_hg00731': mock.ANY, 'I000005_hg00732': mock.ANY})
        self.assertDictEqual(response_json['rnaSeqData'], {})
        self.assertDictEqual(response_json['savedVariantsByGuid'], {})
        self.assertDictEqual(response_json['totalSampleCounts'], {
            'MITO': {'WES': 1},
            'SNV_INDEL': {'WES': 7},
            'SV': {'WES': 3, 'WGS': 3},
        })
        self.assertDictEqual(response_json['variantFunctionalDataByGuid'], {})
        self.assertDictEqual(response_json['variantNotesByGuid'], {})
        self.assertDictEqual(response_json['variantTagsByGuid'], {})

    def test_cached_query_variants(self):
        # TODO
        cache_key_prefix = f'search_results__{self.results_model.guid}'
        cached_variants = [VARIANT1, SV_VARIANT1, GCNV_VARIANT1, MITO_VARIANT1, VARIANT2]
        cache_result = self._format_cached_variants(cached_variants)
        self.set_cache(cache_result)

        variants, total = query_variants(self.results_model, user=self.user)
        self.assertEqual(total, 5)
        self.assertListEqual(self._encode_variants(variants), cached_variants)
        self.mock_redis.get.assert_called_with(f'{cache_key_prefix}__xpos')
        self.mock_redis.set.assert_not_called()

        variants, _ = query_variants(self.results_model, user=self.user, num_results=2, page=2)
        self.assertListEqual(variants, [GCNV_VARIANT1, MITO_VARIANT1])

        gene_counts = get_variant_query_gene_counts(self.results_model, self.user)
        self.assertDictEqual(gene_counts, {
            'ENSG00000177000': {'total': 1, 'families': {'F000002_2': 1}},
            'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
            'ENSG00000210112': {'total': 1, 'families': {'F000002_2': 1}},
            'ENSG00000171621': {'total': 1, 'families': {'F000014_14': 1}},
        })

        self.mock_redis.get.side_effect = [None, json.dumps(cache_result)]
        self.mock_redis.keys.return_value = [f'{cache_key_prefix}__xpos', f'{cache_key_prefix}__gnomad']

        variants, total = query_variants(self.results_model, user=self.user, sort='cadd')
        self.assertEqual(total, 5)
        sorted_variants = [VARIANT2, VARIANT1, SV_VARIANT1, GCNV_VARIANT1, MITO_VARIANT1]
        self.assertListEqual(self._encode_variants(variants), sorted_variants)
        self.mock_redis.get.assert_has_calls([
            mock.call(f'{cache_key_prefix}__cadd'),
            mock.call(f'{cache_key_prefix}__xpos'),
        ])
        self.mock_redis.keys.assert_called_with(pattern=f'{cache_key_prefix}__*')
        self.assert_cached_results(
            {'all_results': [format_cached_variant(v) for v in sorted_variants], 'total_results': 5},
            sort='cadd',
        )

class ClickhouseDeleteDataTests(ClickhouseSearchTestCase):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data', 'clickhouse_search']

    @responses.activate
    def test_trigger_delete_project(self):
        url = reverse(trigger_delete_project)
        self.check_data_manager_login(url)

        Project.objects.filter(guid='R0001_1kg').update(genome_version='38')
        response = self.client.post(
            url, content_type='application/json', data=json.dumps({'project': 'R0001_1kg', 'datasetType': 'SNV_INDEL'})
        )
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'info': [
                'Deactivated search for 7 individuals',
                'Deleted all SNV_INDEL search data for project 1kg project n\xe5me with uni\xe7\xf8de',
            ],
        })
        self.assertEqual(EntriesSnvIndel.objects.filter(project_guid='R0001_1kg').count(), 0)
        self.assertEqual(ProjectGtStatsSnvIndel.objects.filter(project_guid='R0001_1kg').count(), 0)

        annotations_qs = VariantsSnvIndel.objects.all().join_populations()
        updated_seqr_pops_by_key = dict(annotations_qs.values_list('key', 'seqrPop'))
        self.assertDictEqual(updated_seqr_pops_by_key, {
            1: {'ac_wes': 2, 'ac_wgs': 2, 'hom_wes': 1, 'hom_wgs': 1, 'ac_affected': 4, 'hom_affected': 2},
            2: {'ac_wes': 1, 'ac_wgs': 1, 'hom_wes': 0, 'hom_wgs': 0, 'ac_affected': 2, 'hom_affected': 0},
            3: {'ac_wes': 0, 'ac_wgs': 0, 'hom_wes': 0, 'hom_wgs': 0, 'ac_affected': 0, 'hom_affected': 0},
            4: {'ac_wes': 0, 'ac_wgs': 0, 'hom_wes': 0, 'hom_wgs': 0, 'ac_affected': 0, 'hom_affected': 0},
            5: {'ac_wes': 1, 'ac_wgs': 1, 'hom_wes': 0, 'hom_wgs': 0, 'ac_affected': 2, 'hom_affected': 0},
            6: {'ac_wes': 0, 'ac_wgs': 0, 'hom_wes': 0, 'hom_wgs': 0, 'ac_affected': 0, 'hom_affected': 0},
            22: {'ac_wes': 0, 'ac_wgs': 3, 'hom_wes': 0, 'hom_wgs': 1, 'ac_affected': 3, 'hom_affected': 1},
        })

        project_samples = Sample.objects.filter(individual__family__project__guid='R0001_1kg', is_active=True)
        self.assertEqual(project_samples.filter(dataset_type='SNV_INDEL').count(), 0)
        self.assertEqual(project_samples.count(), 4)


