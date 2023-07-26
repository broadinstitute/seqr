from aiohttp.test_utils import AioHTTPTestCase

from hail_search.test_utils import get_hail_search_body, FAMILY_2_VARIANT_SAMPLE_DATA, FAMILY_2_MISSING_SAMPLE_DATA
from hail_search.web_app import init_web_app


VARIANT1 = {
    'variantId': '1-10439-AC-A',
    'chrom': '1',
    'pos': 10439,
    'ref': 'AC',
    'alt': 'A',
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '1',
    'liftedOverPos': 10439,
    'xpos': 1000010439,
    'rsid': 'rs112766696',
    'familyGuids': ['F000002_2'],
    'genotypes': {
        'I000004_hg00731': {
            'sampleId': 'HG00731', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'dp': 10, 'gq': 99, 'ab': 0.5,
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'dp': 24, 'gq': 0, 'ab': 0.0,
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'dp': 60, 'gq': 20, 'ab': 0.0,
        },
    },
    'genotypeFilters': '',
    'clinvar': None,
    'hgmd': None,
    'screenRegionType': None,
    'populations': {
        'seqr': {'af': 0.10000000149011612, 'ac': 9, 'an': 90, 'hom': 2},
        'topmed': {'af': 0.0784199982881546, 'ac': 20757, 'an': 264690, 'hom': 0, 'het': 20757},
        'exac': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'het': 0, 'filter_af': 0.0},
        'gnomad_exomes': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'filter_af': 0.0},
        'gnomad_genomes': {'af': 0.34449315071105957, 'ac': 9271, 'an': 26912, 'hom': 480, 'hemi': 0, 'filter_af': 0.40276646614074707},
    },
    'predictions': {
        'cadd': 4.668000221252441,
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
    '_sort': [1000010439],
}
VARIANT2 = {
    'variantId': '1-11794419-T-G',
    'chrom': '1',
    'pos': 11794419,
    'ref': 'T',
    'alt': 'G',
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '1',
    'liftedOverPos': 11854476,
    'xpos': 1011794419,
    'rsid': 'rs1801131',
    'familyGuids': ['F000002_2'],
    'genotypes': {
       'I000004_hg00731': {
           'sampleId': 'HG00731', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
           'numAlt': 1, 'dp': 32, 'gq': 99, 'ab': 0.625,
       },
       'I000005_hg00732': {
           'sampleId': 'HG00732', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
           'numAlt': 0, 'dp': 33, 'gq': 40, 'ab': 0.0,
       },
       'I000006_hg00733': {
           'sampleId': 'HG00733', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
           'numAlt': 2, 'dp': 36, 'gq': 99, 'ab': 1.0,
       },
    },
    'genotypeFilters': '',
    'clinvar': {
       'alleleId': 18560,
       'conflictingPathogenicities': [
           {'count': 1, 'pathogenicity': 'Likely_pathogenic'},
           {'count': 1, 'pathogenicity': 'Uncertain_significance'},
           {'count': 1, 'pathogenicity': 'Likely_benign'},
           {'count': 5, 'pathogenicity': 'Benign'},
       ],
       'goldStars': 1,
       'pathogenicity': 'Conflicting_interpretations_of_pathogenicity',
       'assertions': ['other'],
       'version': '2023-07-10',
    },
    'hgmd': {'accession': 'CM981315', 'class': 'DFP'},
    'screenRegionType': None,
    'populations': {
       'seqr': {'af': 0.31111112236976624, 'ac': 28, 'an': 90, 'hom': 4},
       'topmed': {'af': 0.24615199863910675, 'ac': 65154, 'an': 264690, 'hom': 8775, 'het': 47604},
       'exac': {'af': 0.29499998688697815, 'ac': 35805, 'an': 121372, 'hom': 5872, 'hemi': 0, 'het': 24061, 'filter_af': 0.4153035283088684},
       'gnomad_exomes': {'af': 0.28899794816970825, 'ac': 72672, 'an': 251462, 'hom': 11567, 'hemi': 0, 'filter_af': 0.4116474986076355},
       'gnomad_genomes': {'af': 0.2633855640888214, 'ac': 40003, 'an': 151880, 'hom': 5754, 'hemi': 0, 'filter_af': 0.4067690968513489},
    },
    'predictions': {
       'cadd': 20.899999618530273,
       'eigen': 2.000999927520752,
       'fathmm': 'D',
       'gnomad_noncoding': 5.868505001068115,
       'mpc': 0.28205373883247375,
       'mut_pred': None,
       'primate_ai': 0.4655807614326477,
       'splice_ai': 0.0,
       'splice_ai_consequence': 'No consequence',
       'vest': 0.210999995470047,
       'mut_taster': 'P',
       'polyphen': 'B',
       'revel': 0.19699999690055847,
       'sift': 'T',
    },
    'transcripts': {
       'ENSG00000177000': [
           {'aminoAcids': 'E/A', 'canonical': 1, 'codons': 'gAa/gCa', 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000376585.6:c.1409A>C', 'hgvsp': 'ENSP00000365770.1:p.Glu470Ala', 'transcriptId': 'ENST00000376585', 'isLofNagnag': None, 'transcriptRank': 0, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
           {'aminoAcids': 'E/A', 'canonical': None, 'codons': 'gAa/gCa', 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000376583.7:c.1409A>C', 'hgvsp': 'ENSP00000365767.3:p.Glu470Ala', 'transcriptId': 'ENST00000376583', 'isLofNagnag': None, 'transcriptRank': 1, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
           {'aminoAcids': 'E/A', 'canonical': None, 'codons': 'gAa/gCa', 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000376590.8:c.1286A>C', 'hgvsp': 'ENSP00000365775.3:p.Glu429Ala', 'transcriptId': 'ENST00000376590', 'isLofNagnag': None, 'transcriptRank': 2, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
           {'aminoAcids': 'E/A', 'canonical': None, 'codons': 'gAa/gCa', 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000376592.6:c.1286A>C', 'hgvsp': 'ENSP00000365777.1:p.Glu429Ala', 'transcriptId': 'ENST00000376592', 'isLofNagnag': None, 'transcriptRank': 3, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
           {'aminoAcids': 'E/A', 'canonical': None, 'codons': 'gAa/gCa', 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000423400.7:c.1406A>C', 'hgvsp': 'ENSP00000398908.3:p.Glu469Ala', 'transcriptId': 'ENST00000423400', 'isLofNagnag': None, 'transcriptRank': 4, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
           {'aminoAcids': 'E/A', 'canonical': None, 'codons': 'gAa/gCa', 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000641407.1:c.1286A>C', 'hgvsp': 'ENSP00000493098.1:p.Glu429Ala', 'transcriptId': 'ENST00000641407', 'isLofNagnag': None, 'transcriptRank': 5, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
           {'aminoAcids': 'E/A', 'canonical': None, 'codons': 'gAa/gCa', 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000641820.1:c.551A>C', 'hgvsp': 'ENSP00000492937.1:p.Glu184Ala', 'transcriptId': 'ENST00000641820', 'isLofNagnag': None, 'transcriptRank': 6, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
           {'aminoAcids': 'E/A', 'canonical': None, 'codons': 'gAa/gCa', 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000641446.1:c.1286A>C', 'hgvsp': 'ENSP00000493262.1:p.Glu429Ala', 'transcriptId': 'ENST00000641446', 'isLofNagnag': None, 'transcriptRank': 7, 'biotype': 'nonsense_mediated_decay', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
           {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000641747.1:c.*798A>C', 'hgvsp': None, 'transcriptId': 'ENST00000641747', 'isLofNagnag': None, 'transcriptRank': 8, 'biotype': 'nonsense_mediated_decay', 'lofFilters': None, 'majorConsequence': '3_prime_UTR_variant'},
           {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000641759.1:n.1655A>C', 'hgvsp': None, 'transcriptId': 'ENST00000641759', 'isLofNagnag': None, 'transcriptRank': 9, 'biotype': 'retained_intron', 'lofFilters': None, 'majorConsequence': 'non_coding_transcript_exon_variant'},
           {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000641805.1:n.1803A>C', 'hgvsp': None, 'transcriptId': 'ENST00000641805', 'isLofNagnag': None, 'transcriptRank': 10, 'biotype': 'retained_intron', 'lofFilters': None, 'majorConsequence': 'non_coding_transcript_exon_variant'},
       ],
    },
    'mainTranscriptId': 'ENST00000376585',
    '_sort': [1011794419],
}
VARIANT3 = {
    'variantId': '1-91511686-T-G',
    'chrom': '1',
    'pos': 91511686,
    'ref': 'T',
    'alt': 'G',
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '1',
    'liftedOverPos': 91977243,
    'xpos': 1091511686,
    'rsid': None,
    'familyGuids': ['F000002_2'],
    'genotypes': {
        'I000004_hg00731': {
            'sampleId': 'HG00731', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'dp': 29, 'gq': 58, 'ab': 0.1724137931034483,
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'dp': 24, 'gq': 0, 'ab': 0.0,
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'dp': 45, 'gq': 0, 'ab': 0.0,
        },
    },
    'genotypeFilters': 'VQSRTrancheSNP99.95to100.00',
    'clinvar': None,
    'hgmd': None,
    'screenRegionType': 'CTCF-only',
    'populations': {
        'seqr': {'af': 0.02222222276031971, 'ac': 2, 'an': 90, 'hom': 0},
        'topmed': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'het': 0},
        'exac': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'het': 0, 'filter_af': 0.0},
        'gnomad_exomes': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'filter_af': 0.0},
        'gnomad_genomes': {'af': 0.00026519427774474025, 'ac': 39, 'an': 147062, 'hom': 0, 'hemi': 0, 'filter_af': 0.0015030059730634093},
    },
    'predictions': {
        'cadd': 29.899999618530273,
        'eigen': 9.491000175476074,
        'fathmm': 'D',
        'gnomad_noncoding': 0.2300506979227066,
        'mpc': 0.8326827883720398,
        'mut_pred': 0.6869999766349792,
        'primate_ai': 0.6995947360992432,
        'splice_ai': 0.0,
        'splice_ai_consequence': 'No consequence',
        'vest': 0.8579999804496765,
        'mut_taster': 'D',
        'polyphen': 'D',
        'revel': 0.5260000228881836,
        'sift': 'D',
    },
    'transcripts': {
        'ENSG00000097046': [
            {'aminoAcids': 'F/C', 'canonical': 1, 'codons': 'tTt/tGt', 'geneId': 'ENSG00000097046', 'hgvsc': 'ENST00000428239.5:c.425T>G', 'hgvsp': 'ENSP00000393139.1:p.Phe142Cys', 'transcriptId': 'ENST00000428239', 'isLofNagnag': None, 'transcriptRank': 0, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
            {'aminoAcids': 'F/C', 'canonical': None, 'codons': 'tTt/tGt', 'geneId': 'ENSG00000097046', 'hgvsc': 'ENST00000234626.10:c.425T>G', 'hgvsp': 'ENSP00000234626.6:p.Phe142Cys', 'transcriptId': 'ENST00000234626', 'isLofNagnag': None, 'transcriptRank': 1, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
            {'aminoAcids': 'F/C', 'canonical': None, 'codons': 'tTt/tGt', 'geneId': 'ENSG00000097046', 'hgvsc': 'ENST00000426137.1:c.425T>G', 'hgvsp': 'ENSP00000398077.1:p.Phe142Cys', 'transcriptId': 'ENST00000426137', 'isLofNagnag': None, 'transcriptRank': 2, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
        ],
    },
    'mainTranscriptId': 'ENST00000428239',
    '_sort': [1091511686],
}


class HailSearchTestCase(AioHTTPTestCase):

    async def get_application(self):
        return init_web_app()

    async def test_status(self):
        async with self.client.request('GET', '/status') as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, {'success': True})

    async def test_search(self):
        search_body = get_hail_search_body(sample_data=FAMILY_2_VARIANT_SAMPLE_DATA, sort='xpos')
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertSetEqual(set(resp_json.keys()), {'results', 'total'})
        self.assertEqual(resp_json['total'], 3)
        self.assertListEqual(resp_json['results'], [VARIANT1, VARIANT2, VARIANT3])

    async def test_search_missing_data(self):
        search_body = get_hail_search_body(sample_data=FAMILY_2_MISSING_SAMPLE_DATA)
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 400)
            text = await resp.text()
        self.assertEqual(text, 'The following samples are available in seqr but missing the loaded data: NA19675, NA19678')
