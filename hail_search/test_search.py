from aiohttp.test_utils import AioHTTPTestCase
from copy import deepcopy

from hail_search.test_utils import get_hail_search_body, FAMILY_2_VARIANT_SAMPLE_DATA, FAMILY_2_MISSING_SAMPLE_DATA, \
    VARIANT1, VARIANT2, VARIANT3, VARIANT4, MULTI_PROJECT_SAMPLE_DATA, MULTI_PROJECT_MISSING_SAMPLE_DATA, \
    LOCATION_SEARCH, EXCLUDE_LOCATION_SEARCH, VARIANT_ID_SEARCH, RSID_SEARCH
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


class HailSearchTestCase(AioHTTPTestCase):

    async def get_application(self):
        return init_web_app()

    async def test_status(self):
        async with self.client.request('GET', '/status') as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, {'success': True})

    async def _assert_expected_search(self, results, **search_kwargs):
        search_body = get_hail_search_body(**search_kwargs)
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertSetEqual(set(resp_json.keys()), {'results', 'total'})
        self.assertEqual(resp_json['total'], len(results))
        self.assertListEqual(
            [v['variantId'] for v in resp_json['results']], [v['variantId'] for v in results],
        )
        for i, result in enumerate(resp_json['results']):
            self.assertDictEqual(result, results[i])

    async def test_single_family_search(self):
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT3, VARIANT4], sample_data=FAMILY_2_VARIANT_SAMPLE_DATA,
        )

    async def test_single_project_search(self):
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], omit_sample_type='SV_WES',
        )

    async def test_multi_project_search(self):
        await self._assert_expected_search(
            [PROJECT_2_VARIANT, MULTI_PROJECT_VARIANT1, MULTI_PROJECT_VARIANT2, VARIANT3, VARIANT4],
            sample_data=MULTI_PROJECT_SAMPLE_DATA,
        )

    async def test_inheritance_filter(self):
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], inheritance_mode='any_affected', omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT1, FAMILY_3_VARIANT, VARIANT4], inheritance_mode='de_novo', omit_sample_type='SV_WES',
        )

        await self._assert_expected_search([], inheritance_mode='x_linked_recessive', omit_sample_type='SV_WES')

        await self._assert_expected_search(
            [VARIANT2], inheritance_mode='homozygous_recessive', omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [PROJECT_2_VARIANT1, VARIANT2], inheritance_mode='homozygous_recessive', sample_data=MULTI_PROJECT_SAMPLE_DATA,
        )

        gt_inheritance_filter = {'genotype': {'I000006_hg00733': 'has_alt', 'I000005_hg00732': 'ref_ref'}}
        await self._assert_expected_search(
            [VARIANT2, VARIANT3], inheritance_filter=gt_inheritance_filter, sample_data=FAMILY_2_VARIANT_SAMPLE_DATA)

    async def test_quality_filter(self):
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT], quality_filter={'vcf_filter': 'pass'}, omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT], quality_filter={'min_gq': 40}, omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT], quality_filter={'min_gq': 40, 'vcf_filter': 'pass'}, omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT], quality_filter={'min_gq': 60, 'affected_only': True},
            omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT1, VARIANT2, FAMILY_3_VARIANT], quality_filter={'min_ab': 50}, omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT2, VARIANT3], quality_filter={'min_ab': 70, 'affected_only': True},
            omit_sample_type='SV_WES',
        )

        quality_filter = {'min_gq': 40, 'min_ab': 50}
        await self._assert_expected_search(
            [VARIANT2, FAMILY_3_VARIANT], quality_filter=quality_filter, omit_sample_type='SV_WES',
        )

        annotations = {'splice_ai': '0.0'}  # Ensures no variants are filtered out by annotation/path filters
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, FAMILY_3_VARIANT], quality_filter=quality_filter, omit_sample_type='SV_WES',
            annotations=annotations, pathogenicity={'clinvar': ['likely_pathogenic', 'vus_or_conflicting']},
        )

        await self._assert_expected_search(
            [VARIANT2, FAMILY_3_VARIANT], quality_filter=quality_filter, omit_sample_type='SV_WES',
            annotations=annotations, pathogenicity={'clinvar': ['pathogenic']},
        )

    async def test_location_search(self):
        await self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], omit_sample_type='SV_WES', **LOCATION_SEARCH,
        )

        await self._assert_expected_search(
            [VARIANT1], omit_sample_type='SV_WES', **EXCLUDE_LOCATION_SEARCH,
        )

        await self._assert_expected_search(
            [SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT],  omit_sample_type='SV_WES',
            intervals=LOCATION_SEARCH['intervals'][-1:], gene_ids=LOCATION_SEARCH['gene_ids'][:1]
        )

    async def test_variant_id_search(self):
        await self._assert_expected_search([VARIANT2], omit_sample_type='SV_WES', **RSID_SEARCH)

        await self._assert_expected_search([VARIANT1], omit_sample_type='SV_WES', **VARIANT_ID_SEARCH)

        await self._assert_expected_search(
            [VARIANT1], omit_sample_type='SV_WES', variant_ids=VARIANT_ID_SEARCH['variant_ids'][:1],
        )

        await self._assert_expected_search(
            [], omit_sample_type='SV_WES', variant_ids=VARIANT_ID_SEARCH['variant_ids'][1:],
        )

    async def test_frequency_filter(self):
        await self._assert_expected_search(
            [VARIANT1, VARIANT4], frequencies={'seqr': {'af': 0.2}}, omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4], frequencies={'seqr': {'ac': 4}}, omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4], frequencies={'seqr': {'hh': 1}}, omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT4], frequencies={'seqr': {'ac': 4, 'hh': 0}}, omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT4], frequencies={'gnomad_genomes': {'af': 0.41}}, omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT2, VARIANT4], frequencies={'gnomad_genomes': {'af': 0.41, 'hh': 1}}, omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT1, VARIANT4], frequencies={'seqr': {'af': 0.2}, 'gnomad_genomes': {'af': 0.41}},
            omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], frequencies={'seqr': {}, 'gnomad_genomes': {'af': None}},
            omit_sample_type='SV_WES',
        )

        annotations = {'splice_ai': '0.0'}  # Ensures no variants are filtered out by annotation/path filters
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT4], frequencies={'gnomad_genomes': {'af': 0.01}}, omit_sample_type='SV_WES',
            annotations=annotations, pathogenicity={'clinvar': ['likely_pathogenic', 'vus_or_conflicting']},
        )

        await self._assert_expected_search(
            [VARIANT2, VARIANT4], frequencies={'gnomad_genomes': {'af': 0.01}}, omit_sample_type='SV_WES',
            annotations=annotations, pathogenicity={'clinvar': ['pathogenic', 'vus_or_conflicting']},
        )

    async def test_annotations_filter(self):
        await self._assert_expected_search([VARIANT2], pathogenicity={'hgmd': ['hgmd_other']}, omit_sample_type='SV_WES')

        pathogenicity = {'clinvar': ['likely_pathogenic', 'vus_or_conflicting', 'benign']}
        await self._assert_expected_search([VARIANT1, VARIANT2], pathogenicity=pathogenicity, omit_sample_type='SV_WES')

        pathogenicity['clinvar'] = pathogenicity['clinvar'][:1]
        await self._assert_expected_search(
            [VARIANT1, VARIANT4], pathogenicity=pathogenicity, annotations={'SCREEN': ['CTCF-only', 'DNase-only']},
            omit_sample_type='SV_WES',
        )

        annotations = {'missense': ['missense_variant'], 'in_frame': ['inframe_insertion', 'inframe_deletion'], 'frameshift': None}
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT4], pathogenicity=pathogenicity, annotations=annotations, omit_sample_type='SV_WES',
        )

        await self._assert_expected_search([VARIANT2, VARIANT4], annotations=annotations, omit_sample_type='SV_WES')

        annotations['splice_ai'] = '0.005'
        await self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], annotations=annotations, omit_sample_type='SV_WES',
        )

        selected_transcript_variant_2 = {**VARIANT2, 'selectedMainTranscriptId': 'ENST00000641759'}
        selected_transcript_variant_3 = {**MULTI_FAMILY_VARIANT, 'selectedMainTranscriptId': 'ENST00000426137'}
        annotations = {'other': ['non_coding_transcript_exon_variant']}
        await self._assert_expected_search(
            [VARIANT1, selected_transcript_variant_2, selected_transcript_variant_3],
            pathogenicity=pathogenicity, annotations=annotations, omit_sample_type='SV_WES',
        )

        await self._assert_expected_search(
            [selected_transcript_variant_2, SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT],
            gene_ids=LOCATION_SEARCH['gene_ids'][:1], annotations=annotations, omit_sample_type='SV_WES',
        )

    async def test_in_silico_filter(self):
        in_silico = {'eigen': '5.5', 'mut_taster': 'P'}
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT4], in_silico=in_silico, omit_sample_type='SV_WES',
        )

        in_silico['requireScore'] = True
        await self._assert_expected_search(
            [VARIANT2, VARIANT4], in_silico=in_silico, omit_sample_type='SV_WES',
        )

    async def test_search_errors(self):
        search_body = get_hail_search_body(sample_data=FAMILY_2_MISSING_SAMPLE_DATA)
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 400)
            reason = resp.reason
        self.assertEqual(reason, 'The following samples are available in seqr but missing the loaded data: NA19675, NA19678')

        search_body = get_hail_search_body(sample_data=MULTI_PROJECT_MISSING_SAMPLE_DATA)
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 400)
            reason = resp.reason
        self.assertEqual(reason, 'The following samples are available in seqr but missing the loaded data: NA19675, NA19678')

        search_body = get_hail_search_body(
            intervals=LOCATION_SEARCH['intervals'] + ['1:1-99999999999'], omit_sample_type='SV_WES',
        )
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 400)
            reason = resp.reason
        self.assertEqual(reason, 'Invalid intervals: 1:1-99999999999')
