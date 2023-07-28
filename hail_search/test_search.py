from aiohttp.test_utils import AioHTTPTestCase
from copy import deepcopy

from hail_search.test_utils import get_hail_search_body, FAMILY_2_VARIANT_SAMPLE_DATA, FAMILY_2_MISSING_SAMPLE_DATA, \
    VARIANT1, VARIANT2, VARIANT3, VARIANT4, MULTI_PROJECT_SAMPLE_DATA, MULTI_PROJECT_MISSING_SAMPLE_DATA
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
    '_sort': [1000010146],
}

MULTI_FAMILY_VARIANT = deepcopy(VARIANT3)
MULTI_FAMILY_VARIANT['familyGuids'].append('F000003_3')
MULTI_FAMILY_VARIANT['genotypes']['I000007_na20870'] = {
    'sampleId': 'NA20870', 'individualGuid': 'I000007_na20870', 'familyGuid': 'F000003_3',
    'numAlt': 1, 'dp': 28, 'gq': 99, 'ab': 0.6785714285714286,
}

MULTI_PROJECT_VARIANT1 = deepcopy(VARIANT1)
MULTI_PROJECT_VARIANT1['familyGuids'].append('F000011_11')
MULTI_PROJECT_VARIANT1['genotypes']['I000015_na20885'] = {
    'sampleId': 'NA20885', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
    'numAlt': 2, 'dp': 6, 'gq': 16, 'ab': 1.0,
}
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

    async def test_search_missing_data(self):
        search_body = get_hail_search_body(sample_data=FAMILY_2_MISSING_SAMPLE_DATA)
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 400)
            text = await resp.text()
        self.assertEqual(text, 'The following samples are available in seqr but missing the loaded data: NA19675, NA19678')

        search_body = get_hail_search_body(sample_data=MULTI_PROJECT_MISSING_SAMPLE_DATA)
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 400)
            text = await resp.text()
        self.assertEqual(text, 'The following samples are available in seqr but missing the loaded data: NA19675, NA19678')
