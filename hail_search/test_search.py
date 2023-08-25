from aiohttp.test_utils import AioHTTPTestCase
from copy import deepcopy

from hail_search.test_utils import get_hail_search_body, FAMILY_2_VARIANT_SAMPLE_DATA, FAMILY_2_MISSING_SAMPLE_DATA, \
    VARIANT1, VARIANT2, VARIANT3, VARIANT4, MULTI_PROJECT_SAMPLE_DATA, MULTI_PROJECT_MISSING_SAMPLE_DATA, \
    LOCATION_SEARCH, EXCLUDE_LOCATION_SEARCH, VARIANT_ID_SEARCH, RSID_SEARCH, GENE_COUNTS, SV_WGS_SAMPLE_DATA, \
    SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, \
    GCNV_MULTI_FAMILY_VARIANT1, GCNV_MULTI_FAMILY_VARIANT2, SV_WES_SAMPLE_DATA
from hail_search.web_app import init_web_app

PROJECT_2_VARIANT = {
    'variantId': '1-10146-ACC-A',
    'chrom': '1',
    'pos': 10146,
    'ref': 'ACC',
    'alt': 'A',
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '1',
    'liftedOverPos': 10146,
    'xpos': 1000010146,
    'rsid': 'rs375931351',
    'familyGuids': ['F000011_11'],
    'genotypes': {
        'I000015_na20885': {
            'sampleId': 'NA20885', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
            'numAlt': 1, 'dp': 8, 'gq': 14, 'ab': 0.875,
        }
    },
    'genotypeFilters': '',
    'clinvar': None,
    'hgmd': None,
    'screenRegionType': None,
    'populations': {
        'seqr': {'af': 0.0, 'ac': 0, 'an': 90, 'hom': 0},
        'topmed': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'het': 0},
        'exac': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'het': 0, 'filter_af': 0.0},
        'gnomad_exomes': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'filter_af': 0.0},
        'gnomad_genomes': {'af': 0.00012430080096237361, 'ac': 2, 'an': 16090, 'hom': 0, 'hemi': 0, 'filter_af': 0.002336448524147272},
    },
    'predictions': {
        'cadd': 4.6529998779296875,
        'eigen': None,
        'fathmm': None,
        'gnomad_noncoding': None,
        'mpc': None,
        'mut_pred': None,
        'primate_ai': None,
        'splice_ai': None,
        'splice_ai_consequence': None,
        'vest': None,
        'mut_taster': None,
        'polyphen': None,
        'revel': None,
        'sift': None,
    },
    'transcripts': {},
    'mainTranscriptId': None,
    'selectedMainTranscriptId': None,
    '_sort': [1000010146],
}

FAMILY_3_VARIANT = deepcopy(VARIANT3)
FAMILY_3_VARIANT['familyGuids'] = ['F000003_3']
FAMILY_3_VARIANT['genotypes'] = {
    'I000007_na20870': {
        'sampleId': 'NA20870', 'individualGuid': 'I000007_na20870', 'familyGuid': 'F000003_3',
        'numAlt': 1, 'dp': 28, 'gq': 99, 'ab': 0.6785714285714286,
    },
}

MULTI_FAMILY_VARIANT = deepcopy(VARIANT3)
MULTI_FAMILY_VARIANT['familyGuids'] += FAMILY_3_VARIANT['familyGuids']
MULTI_FAMILY_VARIANT['genotypes'].update(FAMILY_3_VARIANT['genotypes'])

SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT = {**MULTI_FAMILY_VARIANT, 'selectedMainTranscriptId': 'ENST00000497611'}
SELECTED_ANNOTATION_TRANSCRIPT_MULTI_FAMILY_VARIANT = {**MULTI_FAMILY_VARIANT, 'selectedMainTranscriptId': 'ENST00000426137'}
SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_3 = {**VARIANT3, 'selectedMainTranscriptId': 'ENST00000426137'}
SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2 = {**VARIANT2, 'selectedMainTranscriptId': 'ENST00000641759'}

PROJECT_2_VARIANT1 = deepcopy(VARIANT1)
PROJECT_2_VARIANT1['familyGuids'] = ['F000011_11']
PROJECT_2_VARIANT1['genotypes'] = {
    'I000015_na20885': {
        'sampleId': 'NA20885', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
        'numAlt': 2, 'dp': 6, 'gq': 16, 'ab': 1.0,
    },
}
MULTI_PROJECT_VARIANT1 = deepcopy(VARIANT1)
MULTI_PROJECT_VARIANT1['familyGuids'] += PROJECT_2_VARIANT1['familyGuids']
MULTI_PROJECT_VARIANT1['genotypes'].update(PROJECT_2_VARIANT1['genotypes'])
MULTI_PROJECT_VARIANT2 = deepcopy(VARIANT2)
MULTI_PROJECT_VARIANT2['familyGuids'].append('F000011_11')
MULTI_PROJECT_VARIANT2['genotypes']['I000015_na20885'] = {
    'sampleId': 'NA20885', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
    'numAlt': 1, 'dp': 28, 'gq': 99, 'ab': 0.5,
}

# Ensures no variants are filtered out by annotation/path filters for compound hets
COMP_HET_ALL_PASS_FILTERS = {
    'annotations': {'splice_ai': '0.0'}, 'pathogenicity': {'clinvar': ['likely_pathogenic']},
    'structural': ['DEL', 'CPX', 'INS'],
}

NEW_SV_FILTER = {'new_structural_variants': ['NEW']}


def _sorted(variant, sorts):
    return {**variant, '_sort': sorts + variant['_sort']}


class HailSearchTestCase(AioHTTPTestCase):

    async def get_application(self):
        return init_web_app()

    # async def test_status(self):
    #     async with self.client.request('GET', '/status') as resp:
    #         self.assertEqual(resp.status, 200)
    #         resp_json = await resp.json()
    #     self.assertDictEqual(resp_json, {'success': True})

    async def _assert_expected_search(self, results, gene_counts=None, **search_kwargs):
        search_body = get_hail_search_body(**search_kwargs)
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertSetEqual(set(resp_json.keys()), {'results', 'total'})
        self.assertEqual(resp_json['total'], len(results))
        for i, result in enumerate(resp_json['results']):
            if result != results[i]:
                diff_k = {ky for ky, val in results[i].items() if val != result[ky]}
                import pdb; pdb.set_trace()  # TODO
            self.assertEqual(result, results[i])

        if gene_counts:
            async with self.client.request('POST', '/gene_counts', json=search_body) as resp:
                self.assertEqual(resp.status, 200)
                gene_counts_json = await resp.json()
            if gene_counts_json != gene_counts:
                import pdb; pdb.set_trace()  # TODO
            self.assertDictEqual(gene_counts_json, gene_counts)

    async def test_single_family_search(self):
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT3, VARIANT4], sample_data=FAMILY_2_VARIANT_SAMPLE_DATA, gene_counts={
                'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2}},
            }
        )

        await self._assert_expected_search(
            [GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], omit_sample_type='VARIANTS', gene_counts={
                # TODO should be filtered to returned transcripts - just use entries?
                'ENSG00000129562': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000013364': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000079616': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000103495': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000167371': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000280789': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000280893': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000281348': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000275023': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000277972': {'total': 1, 'families': {'F000002_2': 1}},
            }
        )

        await self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, gene_counts={
                'ENSG00000171621': {'total': 2, 'families': {'F000011_11': 2}},
                'ENSG00000083544': {'total': 1, 'families': {'F000011_11': 1}},
                'ENSG00000184986': {'total': 1, 'families': {'F000011_11': 1}},
                'null': {'total': 1, 'families': {'F000011_11': 1}},
            }
        )

    async def test_single_project_search(self):
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], omit_sample_type='SV_WES', gene_counts={
                'ENSG00000097046': {'total': 3, 'families': {'F000002_2': 2, 'F000003_3': 1}},
                'ENSG00000177000': {'total': 3, 'families': {'F000002_2': 2, 'F000003_3': 1}},
            }
        )

        await self._assert_expected_search(
            [GCNV_MULTI_FAMILY_VARIANT1, GCNV_MULTI_FAMILY_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], sample_data=SV_WES_SAMPLE_DATA, gene_counts={
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
            }
        )

    # async def test_multi_project_search(self):
    #     await self._assert_expected_search(
    #         [PROJECT_2_VARIANT, MULTI_PROJECT_VARIANT1, MULTI_PROJECT_VARIANT2, VARIANT3, VARIANT4],
    #         gene_counts=GENE_COUNTS, sample_data=MULTI_PROJECT_SAMPLE_DATA,
    #     )
    #
    # async def test_inheritance_filter(self):
    #     inheritance_mode = 'any_affected'
    #     await self._assert_expected_search(
    #         [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], inheritance_mode=inheritance_mode, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA,
    #     )
    #
    #     await self._assert_expected_search(
    #         [SV_VARIANT2], inheritance_mode=inheritance_mode, annotations=NEW_SV_FILTER, sample_data=SV_WGS_SAMPLE_DATA,
    #     )
    #
    #     inheritance_mode = 'de_novo'
    #     await self._assert_expected_search(
    #         [VARIANT1, FAMILY_3_VARIANT, VARIANT4], inheritance_mode=inheritance_mode, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [SV_VARIANT1], inheritance_mode=inheritance_mode,  sample_data=SV_WGS_SAMPLE_DATA,
    #     )
    #
    #     inheritance_mode = 'x_linked_recessive'
    #     await self._assert_expected_search([], inheritance_mode=inheritance_mode, omit_sample_type='SV_WES')
    #     await self._assert_expected_search([], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA)
    #
    #     inheritance_mode = 'homozygous_recessive'
    #     await self._assert_expected_search(
    #         [VARIANT2], inheritance_mode=inheritance_mode, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [PROJECT_2_VARIANT1, VARIANT2], inheritance_mode=inheritance_mode, sample_data=MULTI_PROJECT_SAMPLE_DATA,
    #     )
    #
    #     await self._assert_expected_search(
    #         [SV_VARIANT4], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA,
    #     )
    #
    #     gt_inheritance_filter = {'genotype': {'I000006_hg00733': 'has_alt', 'I000005_hg00732': 'ref_ref'}}
    #     await self._assert_expected_search(
    #         [VARIANT2, VARIANT3], inheritance_filter=gt_inheritance_filter, sample_data=FAMILY_2_VARIANT_SAMPLE_DATA)
    #
    #     inheritance_mode = 'compound_het'
    #     await self._assert_expected_search(
    #         [[VARIANT3, VARIANT4]], inheritance_mode=inheritance_mode, sample_data=MULTI_PROJECT_SAMPLE_DATA, gene_counts={
    #             'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
    #             'ENSG00000177000': {'total': 1, 'families': {'F000002_2': 1}},
    #         }, **COMP_HET_ALL_PASS_FILTERS,
    #     )
    #
    #     await self._assert_expected_search(
    #         [[SV_VARIANT1, SV_VARIANT2]], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA,
    #         **COMP_HET_ALL_PASS_FILTERS,
    #     )
    #
    #     inheritance_mode = 'recessive'
    #     await self._assert_expected_search(
    #         [PROJECT_2_VARIANT1, VARIANT2, [VARIANT3, VARIANT4]], inheritance_mode=inheritance_mode, gene_counts={
    #             'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
    #             'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2}},
    #         }, sample_data=MULTI_PROJECT_SAMPLE_DATA, **COMP_HET_ALL_PASS_FILTERS,
    #     )
    #
    #     await self._assert_expected_search(
    #         [[SV_VARIANT1, SV_VARIANT2], SV_VARIANT4], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA,
    #         **COMP_HET_ALL_PASS_FILTERS,
    #     )
    #
    # async def test_quality_filter(self):
    #     quality_filter = {'vcf_filter': 'pass'}
    #     await self._assert_expected_search(
    #         [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT], quality_filter=quality_filter, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search([SV_VARIANT4], quality_filter=quality_filter, sample_data=SV_WGS_SAMPLE_DATA)
    #
    #     await self._assert_expected_search(
    #         [VARIANT2, MULTI_FAMILY_VARIANT], quality_filter={'min_gq': 40}, omit_sample_type='SV_WES',
    #     )
    #
    #     sv_quality_filter = {'min_gq_sv': 40}
    #     await self._assert_expected_search(
    #         [SV_VARIANT3, SV_VARIANT4], quality_filter=sv_quality_filter, sample_data=SV_WGS_SAMPLE_DATA,
    #     )
    #
    #     await self._assert_expected_search(
    #         [], annotations=NEW_SV_FILTER, quality_filter=sv_quality_filter, sample_data=SV_WGS_SAMPLE_DATA,
    #     )
    #
    #     await self._assert_expected_search(
    #         [VARIANT2, MULTI_FAMILY_VARIANT], quality_filter={'min_gq': 40, 'vcf_filter': 'pass'}, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT], quality_filter={'min_gq': 60, 'affected_only': True},
    #         omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [SV_VARIANT3, SV_VARIANT4], quality_filter={'min_gq_sv': 60, 'affected_only': True}, sample_data=SV_WGS_SAMPLE_DATA,
    #     )
    #
    #     await self._assert_expected_search(
    #         [VARIANT1, VARIANT2, FAMILY_3_VARIANT], quality_filter={'min_ab': 50}, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [VARIANT2, VARIANT3], quality_filter={'min_ab': 70, 'affected_only': True},
    #         omit_sample_type='SV_WES',
    #     )
    #
    #     quality_filter = {'min_gq': 40, 'min_ab': 50}
    #     await self._assert_expected_search(
    #         [VARIANT2, FAMILY_3_VARIANT], quality_filter=quality_filter, omit_sample_type='SV_WES',
    #     )
    #
    #     annotations = {'splice_ai': '0.0'}  # Ensures no variants are filtered out by annotation/path filters
    #     await self._assert_expected_search(
    #         [VARIANT1, VARIANT2, FAMILY_3_VARIANT], quality_filter=quality_filter, omit_sample_type='SV_WES',
    #         annotations=annotations, pathogenicity={'clinvar': ['likely_pathogenic', 'vus_or_conflicting']},
    #     )
    #
    #     await self._assert_expected_search(
    #         [VARIANT2, FAMILY_3_VARIANT], quality_filter=quality_filter, omit_sample_type='SV_WES',
    #         annotations=annotations, pathogenicity={'clinvar': ['pathogenic']},
    #     )
    #
    # async def test_location_search(self):
    #     await self._assert_expected_search(
    #         [VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], omit_sample_type='SV_WES', **LOCATION_SEARCH,
    #     )
    #
    #     sv_intervals = ['1:9310023-9380264']
    #     await self._assert_expected_search(
    #         [SV_VARIANT1, SV_VARIANT2], sample_data=SV_WGS_SAMPLE_DATA, intervals=sv_intervals, gene_ids=['ENSG00000171621'],
    #     )
    #
    #     await self._assert_expected_search(
    #         [VARIANT1], omit_sample_type='SV_WES', **EXCLUDE_LOCATION_SEARCH,
    #     )
    #
    #     await self._assert_expected_search(
    #         [SV_VARIANT3, SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, intervals=sv_intervals, exclude_intervals=True,
    #     )
    #
    #     await self._assert_expected_search(
    #         [SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT],  omit_sample_type='SV_WES',
    #         intervals=LOCATION_SEARCH['intervals'][-1:], gene_ids=LOCATION_SEARCH['gene_ids'][:1]
    #     )
    #
    # async def test_variant_id_search(self):
    #     await self._assert_expected_search([VARIANT2], omit_sample_type='SV_WES', **RSID_SEARCH)
    #
    #     await self._assert_expected_search([VARIANT1], omit_sample_type='SV_WES', **VARIANT_ID_SEARCH)
    #
    #     await self._assert_expected_search(
    #         [VARIANT1], omit_sample_type='SV_WES', variant_ids=VARIANT_ID_SEARCH['variant_ids'][:1],
    #     )
    #
    #     await self._assert_expected_search(
    #         [], omit_sample_type='SV_WES', variant_ids=VARIANT_ID_SEARCH['variant_ids'][1:],
    #     )
    #
    #     await self._assert_expected_search([SV_VARIANT2, SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, variant_keys=[
    #         'cohort_2911.chr1.final_cleanup_INS_chr1_160', 'phase2_DEL_chr14_4640',
    #     ])
    #
    # async def test_frequency_filter(self):
    #     await self._assert_expected_search(
    #         [VARIANT1, VARIANT4], frequencies={'seqr': {'af': 0.2}}, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [MULTI_FAMILY_VARIANT, VARIANT4], frequencies={'seqr': {'ac': 4}}, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [MULTI_FAMILY_VARIANT, VARIANT4], frequencies={'seqr': {'hh': 1}}, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [VARIANT4], frequencies={'seqr': {'ac': 4, 'hh': 0}}, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [SV_VARIANT1], frequencies={'sv_callset': {'af': 0.05}}, sample_data=SV_WGS_SAMPLE_DATA,
    #     )
    #
    #     await self._assert_expected_search(
    #         [VARIANT1, VARIANT2, VARIANT4], frequencies={'gnomad_genomes': {'af': 0.05}}, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [VARIANT2, VARIANT4], frequencies={'gnomad_genomes': {'af': 0.05, 'hh': 1}}, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [VARIANT2, VARIANT4], frequencies={'gnomad_genomes': {'af': 0.005}}, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [SV_VARIANT1, SV_VARIANT3, SV_VARIANT4], frequencies={'gnomad_svs': {'af': 0.001}}, sample_data=SV_WGS_SAMPLE_DATA,
    #     )
    #
    #     await self._assert_expected_search(
    #         [VARIANT4], frequencies={'seqr': {'af': 0.2}, 'gnomad_genomes': {'ac': 50}},
    #         omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], frequencies={'seqr': {}, 'gnomad_genomes': {'af': None}},
    #         omit_sample_type='SV_WES',
    #     )
    #
    #     annotations = {'splice_ai': '0.0'}  # Ensures no variants are filtered out by annotation/path filters
    #     await self._assert_expected_search(
    #         [VARIANT1, VARIANT2, VARIANT4], frequencies={'gnomad_genomes': {'af': 0.01}}, omit_sample_type='SV_WES',
    #         annotations=annotations, pathogenicity={'clinvar': ['pathogenic', 'likely_pathogenic', 'vus_or_conflicting']},
    #     )
    #
    #     await self._assert_expected_search(
    #         [VARIANT2, VARIANT4], frequencies={'gnomad_genomes': {'af': 0.01}}, omit_sample_type='SV_WES',
    #         annotations=annotations, pathogenicity={'clinvar': ['pathogenic', 'vus_or_conflicting']},
    #     )
    #
    # async def test_annotations_filter(self):
    #     await self._assert_expected_search([VARIANT2], pathogenicity={'hgmd': ['hgmd_other']}, omit_sample_type='SV_WES')
    #
    #     pathogenicity = {'clinvar': ['likely_pathogenic', 'vus_or_conflicting', 'benign']}
    #     await self._assert_expected_search([VARIANT1, VARIANT2], pathogenicity=pathogenicity, omit_sample_type='SV_WES')
    #
    #     pathogenicity['clinvar'] = pathogenicity['clinvar'][:1]
    #     await self._assert_expected_search(
    #         [VARIANT1, VARIANT4], pathogenicity=pathogenicity, annotations={'SCREEN': ['CTCF-only', 'DNase-only']},
    #         omit_sample_type='SV_WES',
    #     )
    #
    #     annotations = {
    #         'missense': ['missense_variant'], 'in_frame': ['inframe_insertion', 'inframe_deletion'], 'frameshift': None,
    #         'structural_consequence': ['INTRONIC'],
    #     }
    #     await self._assert_expected_search(
    #         [VARIANT1, VARIANT2, VARIANT4], pathogenicity=pathogenicity, annotations=annotations, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search([VARIANT2, VARIANT4], annotations=annotations, omit_sample_type='SV_WES')
    #
    #     await self._assert_expected_search([SV_VARIANT1], annotations=annotations, sample_data=SV_WGS_SAMPLE_DATA)
    #
    #     annotations['splice_ai'] = '0.005'
    #     await self._assert_expected_search(
    #         [VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], annotations=annotations, omit_sample_type='SV_WES',
    #     )
    #
    #     annotations['structural'] = ['DEL']
    #     await self._assert_expected_search([SV_VARIANT1, SV_VARIANT4], annotations=annotations, sample_data=SV_WGS_SAMPLE_DATA)
    #
    #     annotations = {'other': ['non_coding_transcript_exon_variant']}
    #     await self._assert_expected_search(
    #         [VARIANT1, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, SELECTED_ANNOTATION_TRANSCRIPT_MULTI_FAMILY_VARIANT],
    #         pathogenicity=pathogenicity, annotations=annotations, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT],
    #         gene_ids=LOCATION_SEARCH['gene_ids'][:1], annotations=annotations, omit_sample_type='SV_WES',
    #     )
    #
    # async def test_secondary_annotations_filter(self):
    #     annotations_1 = {'missense': ['missense_variant']}
    #     annotations_2 = {'other': ['intron_variant']}
    #
    #     await self._assert_expected_search(
    #         [[VARIANT3, VARIANT4]], inheritance_mode='compound_het', omit_sample_type='SV_WES',
    #         annotations=annotations_1, annotations_secondary=annotations_2,
    #     )
    #
    #     await self._assert_expected_search(
    #         [VARIANT2, [VARIANT3, VARIANT4]], inheritance_mode='recessive', omit_sample_type='SV_WES',
    #         annotations=annotations_1, annotations_secondary=annotations_2,
    #     )
    #
    #     await self._assert_expected_search(
    #         [[VARIANT3, VARIANT4]], inheritance_mode='recessive', omit_sample_type='SV_WES',
    #         annotations=annotations_2, annotations_secondary=annotations_1,
    #     )
    #
    #     sv_annotations_1 = {'structural': ['INS']}
    #     sv_annotations_2 = {'structural': ['DEL'], 'structural_consequence': ['INTRONIC']}
    #
    #     await self._assert_expected_search(
    #         [[SV_VARIANT1, SV_VARIANT2]], sample_data=SV_WGS_SAMPLE_DATA, inheritance_mode='compound_het',
    #         annotations=sv_annotations_1, annotations_secondary=sv_annotations_2,
    #     )
    #
    #     await self._assert_expected_search(
    #         [[SV_VARIANT1, SV_VARIANT2], SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, inheritance_mode='recessive',
    #         annotations=sv_annotations_2, annotations_secondary=sv_annotations_1,
    #     )
    #
    #     pathogenicity = {'clinvar': ['likely_pathogenic', 'vus_or_conflicting']}
    #     await self._assert_expected_search(
    #         [VARIANT2, [VARIANT3, VARIANT4]], inheritance_mode='recessive', omit_sample_type='SV_WES',
    #         annotations=annotations_2, annotations_secondary=annotations_1, pathogenicity=pathogenicity,
    #     )
    #
    #     screen_annotations = {'SCREEN': ['CTCF-only']}
    #     await self._assert_expected_search(
    #         [], inheritance_mode='recessive', omit_sample_type='SV_WES',
    #         annotations=screen_annotations, annotations_secondary=annotations_1,
    #     )
    #
    #     await self._assert_expected_search(
    #         [[VARIANT3, VARIANT4]], inheritance_mode='recessive', omit_sample_type='SV_WES',
    #         annotations=screen_annotations, annotations_secondary=annotations_2,
    #     )
    #
    #     selected_transcript_annotations = {'other': ['non_coding_transcript_exon_variant']}
    #     await self._assert_expected_search(
    #         [VARIANT2, [SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_3, VARIANT4]], inheritance_mode='recessive',
    #         annotations=screen_annotations, annotations_secondary=selected_transcript_annotations,
    #         pathogenicity=pathogenicity, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, [SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_3, VARIANT4]],
    #         annotations={**selected_transcript_annotations, **screen_annotations}, annotations_secondary=annotations_2,
    #         inheritance_mode='recessive', omit_sample_type='SV_WES',
    #     )
    #
    # async def test_in_silico_filter(self):
    #     in_silico = {'eigen': '5.5', 'mut_taster': 'P'}
    #     await self._assert_expected_search(
    #         [VARIANT1, VARIANT2, VARIANT4], in_silico=in_silico, omit_sample_type='SV_WES',
    #     )
    #
    #     in_silico['requireScore'] = True
    #     await self._assert_expected_search(
    #         [VARIANT2, VARIANT4], in_silico=in_silico, omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, in_silico={'strvctvre': 0.1, 'requireScore': True},
    #     )
    #
    # async def test_search_errors(self):
    #     search_body = get_hail_search_body(sample_data=FAMILY_2_MISSING_SAMPLE_DATA)
    #     async with self.client.request('POST', '/search', json=search_body) as resp:
    #         self.assertEqual(resp.status, 400)
    #         reason = resp.reason
    #     self.assertEqual(reason, 'The following samples are available in seqr but missing the loaded data: NA19675, NA19678')
    #
    #     search_body = get_hail_search_body(sample_data=MULTI_PROJECT_MISSING_SAMPLE_DATA)
    #     async with self.client.request('POST', '/search', json=search_body) as resp:
    #         self.assertEqual(resp.status, 400)
    #         reason = resp.reason
    #     self.assertEqual(reason, 'The following samples are available in seqr but missing the loaded data: NA19675, NA19678')
    #
    #     search_body = get_hail_search_body(
    #         intervals=LOCATION_SEARCH['intervals'] + ['1:1-99999999999'], omit_sample_type='SV_WES',
    #     )
    #     async with self.client.request('POST', '/search', json=search_body) as resp:
    #         self.assertEqual(resp.status, 400)
    #         reason = resp.reason
    #     self.assertEqual(reason, 'Invalid intervals: 1:1-99999999999')
    #
    # async def test_sort(self):
    #     await self._assert_expected_search(
    #         [_sorted(VARIANT2, [11, 11]),  _sorted(VARIANT4, [11, 11]), _sorted(MULTI_FAMILY_VARIANT, [22, 24]),
    #          _sorted(VARIANT1, [None, None])], omit_sample_type='SV_WES', sort='protein_consequence',
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(SV_VARIANT1, [11]), _sorted(SV_VARIANT2, [12]), _sorted(SV_VARIANT3, [12]), _sorted(SV_VARIANT4, [12])],
    #          sample_data=SV_WGS_SAMPLE_DATA, sort='protein_consequence',
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(VARIANT4, [11, 11]), _sorted(SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, [11, 22]),
    #          _sorted(SELECTED_ANNOTATION_TRANSCRIPT_MULTI_FAMILY_VARIANT, [22, 22])],
    #         omit_sample_type='SV_WES', sort='protein_consequence',
    #         annotations={'other': ['non_coding_transcript_exon_variant'], 'splice_ai': '0'},
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(VARIANT1, [4]), _sorted(VARIANT2, [8]), _sorted(MULTI_FAMILY_VARIANT, [12.5]),
    #          _sorted(VARIANT4, [12.5])], omit_sample_type='SV_WES', sort='pathogenicity',
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(VARIANT1, [4, None]), _sorted(VARIANT2, [8, 3]), _sorted(MULTI_FAMILY_VARIANT, [12.5, None]),
    #          _sorted(VARIANT4, [12.5, None])], omit_sample_type='SV_WES', sort='pathogenicity_hgmd',
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(VARIANT2, [0]), _sorted(VARIANT4, [0.00026519427774474025]),
    #          _sorted(VARIANT1, [0.034449315071105957]), _sorted(MULTI_FAMILY_VARIANT, [0.38041073083877563])],
    #         omit_sample_type='SV_WES', sort='gnomad',
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(VARIANT1, [0]), _sorted(MULTI_FAMILY_VARIANT, [0]), _sorted(VARIANT4, [0]),
    #          _sorted(VARIANT2, [0.28899794816970825])], omit_sample_type='SV_WES', sort='gnomad_exomes',
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(VARIANT4, [0.02222222276031971]), _sorted(VARIANT1, [0.10000000149011612]),
    #          _sorted(VARIANT2, [0.31111112236976624]), _sorted(MULTI_FAMILY_VARIANT, [0.6666666865348816])],
    #         omit_sample_type='SV_WES', sort='callset_af',
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(VARIANT4, [-29.899999618530273]), _sorted(VARIANT2, [-20.899999618530273]),
    #          _sorted(VARIANT1, [-4.668000221252441]), _sorted(MULTI_FAMILY_VARIANT, [-2.753999948501587]), ],
    #         omit_sample_type='SV_WES', sort='cadd',
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(VARIANT4, [-0.5260000228881836]), _sorted(VARIANT2, [-0.19699999690055847]),
    #          _sorted(VARIANT1, [None]), _sorted(MULTI_FAMILY_VARIANT, [None])], omit_sample_type='SV_WES', sort='revel',
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(MULTI_FAMILY_VARIANT, [-0.009999999776482582]), _sorted(VARIANT2, [0]), _sorted(VARIANT4, [0]),
    #          _sorted(VARIANT1, [None])], omit_sample_type='SV_WES', sort='splice_ai',
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(MULTI_FAMILY_VARIANT, [0, -2]), _sorted(VARIANT2, [0, -1]), _sorted(VARIANT4, [0, -1]), _sorted(VARIANT1, [1, 0])],
    #         omit_sample_type='SV_WES', sort='in_omim', sort_metadata=['ENSG00000177000', 'ENSG00000097046'],
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(VARIANT2, [0, -1]), _sorted(MULTI_FAMILY_VARIANT, [1, -1]), _sorted(VARIANT1, [1, 0]), _sorted(VARIANT4, [1, 0])],
    #         omit_sample_type='SV_WES', sort='in_omim', sort_metadata=['ENSG00000177000'],
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(VARIANT2, [2, 2]), _sorted(MULTI_FAMILY_VARIANT, [4, 2]), _sorted(VARIANT4, [4, 4]),
    #          _sorted(VARIANT1, [None, None])], omit_sample_type='SV_WES', sort='constraint',
    #         sort_metadata={'ENSG00000177000': 2, 'ENSG00000097046': 4},
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(VARIANT2, [3, 3]), _sorted(MULTI_FAMILY_VARIANT, [None, 3]), _sorted(VARIANT1, [None, None]),
    #          _sorted(VARIANT4, [None, None])], omit_sample_type='SV_WES', sort='prioritized_gene',
    #         sort_metadata={'ENSG00000177000': 3},
    #     )
    #
    #     # size sort only applies to SVs, so has no impact on other variants
    #     await self._assert_expected_search(
    #         [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], sort='size', omit_sample_type='SV_WES',
    #     )
    #
    #     await self._assert_expected_search(
    #         [_sorted(SV_VARIANT4, [-46343]), _sorted(SV_VARIANT1, [-104]), _sorted(SV_VARIANT2, [-50]),
    #          _sorted(SV_VARIANT3, [-50])], sample_data=SV_WGS_SAMPLE_DATA, sort='size',
    #     )
    #
    #     # sort applies to compound hets
    #     await self._assert_expected_search(
    #         [_sorted(VARIANT2, [11, 11]), [_sorted(VARIANT4, [11, 11]),  _sorted(VARIANT3, [22, 24])]],
    #         sort='protein_consequence', inheritance_mode='recessive', omit_sample_type='SV_WES', **COMP_HET_ALL_PASS_FILTERS,
    #     )
    #
    #     await self._assert_expected_search(
    #         [[_sorted(VARIANT4, [-0.5260000228881836]), _sorted(VARIANT3, [None])],
    #          _sorted(VARIANT2, [-0.19699999690055847])],
    #         sort='revel', inheritance_mode='recessive', omit_sample_type='SV_WES', **COMP_HET_ALL_PASS_FILTERS,
    #     )
    #
    #     await self._assert_expected_search(
    #         [[_sorted(VARIANT3, [-0.009999999776482582]),  _sorted(VARIANT4, [0])], _sorted(VARIANT2, [0])],
    #         sort='splice_ai', inheritance_mode='recessive', omit_sample_type='SV_WES', **COMP_HET_ALL_PASS_FILTERS,
    #     )
