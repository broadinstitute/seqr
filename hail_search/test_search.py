from aiohttp.test_utils import AioHTTPTestCase
from copy import deepcopy

from hail_search.test_utils import get_hail_search_body, FAMILY_2_VARIANT_SAMPLE_DATA, FAMILY_2_MISSING_SAMPLE_DATA, \
    MULTI_PROJECT_SAMPLE_DATA, MULTI_PROJECT_MISSING_SAMPLE_DATA
from hail_search.web_app import init_web_app

VARIANT_ID_1 = '1-10439-AC-A'
VARIANT1 = {
    'variantId': VARIANT_ID_1,
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
VARIANT_ID_2 = '1-11794419-T-G'
VARIANT2 = {
    'variantId': VARIANT_ID_2,
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
           'numAlt': 2, 'dp': 36, 'gq': 99, 'ab': 1.0,
       },
       'I000005_hg00732': {
           'sampleId': 'HG00732', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
           'numAlt': 0, 'dp': 33, 'gq': 40, 'ab': 0.0,
       },
       'I000006_hg00733': {
           'sampleId': 'HG00733', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
           'numAlt': 1, 'dp': 32, 'gq': 99, 'ab': 0.625,
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
VARIANT_ID_3 = '1-91502721-G-A'
VARIANT3 = {
    'variantId': VARIANT_ID_3,
    'chrom': '1',
    'pos': 91502721,
    'ref': 'G',
    'alt': 'A',
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '1',
    'liftedOverPos': 91968278,
    'xpos': 1091502721,
    'rsid': 'rs13447464',
    'familyGuids': ['F000002_2'],
    'genotypes': {
        'I000004_hg00731': {
            'sampleId': 'HG00731', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'dp': 40, 'gq': 99, 'ab': 1.0,
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'dp': 37, 'gq': 99, 'ab': 0.4594594594594595,
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'dp': 27, 'gq': 99, 'ab': 0.4074074074074074,
        },
    },
    'genotypeFilters': '',
    'clinvar': None,
    'hgmd': None,
    'screenRegionType': None,
    'populations': {
        'seqr': {'af': 0.6666666865348816, 'ac': 4, 'an': 6, 'hom': 1},
        'topmed': {'af': 0.36268100142478943, 'ac': 95998, 'an': 264690, 'hom': 19369, 'het': 57260},
        'exac': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'het': 0, 'filter_af': 0.0},
        'gnomad_exomes': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'filter_af': 0.0},
        'gnomad_genomes': {'af': 0.38041073083877563, 'ac': 57757, 'an': 151828, 'hom': 12204, 'hemi': 0, 'filter_af': 0.4797786474227905},
    },
    'predictions': {
        'cadd': 2.753999948501587,
        'eigen': 1.378000020980835,
        'fathmm': None,
        'gnomad_noncoding': 0.7389647960662842,
        'mpc': None,
        'mut_pred': None,
        'primate_ai': None,
        'splice_ai': 0.009999999776482582,
        'splice_ai_consequence': 'Donor gain',
        'vest': None,
        'mut_taster': None,
        'polyphen': None,
        'revel': None,
        'sift': None,
    },
    'transcripts': {
        'ENSG00000097046': [
            {'aminoAcids': None, 'canonical': 1, 'codons': None, 'geneId': 'ENSG00000097046', 'hgvsc': 'ENST00000428239.5:c.115+890G>A', 'hgvsp': None, 'transcriptId': 'ENST00000428239', 'isLofNagnag': None, 'transcriptRank': 0, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'intron_variant'},
            {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000097046', 'hgvsc': 'ENST00000234626.10:c.115+890G>A', 'hgvsp': None, 'transcriptId': 'ENST00000234626', 'isLofNagnag': None, 'transcriptRank': 1, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'intron_variant'},
            {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000097046', 'hgvsc': 'ENST00000426137.1:c.115+890G>A', 'hgvsp': None, 'transcriptId': 'ENST00000426137', 'isLofNagnag': None, 'transcriptRank': 2, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'intron_variant'},
        ],
        'ENSG00000177000': [
            {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000497611.1:n.501+890G>A', 'hgvsp': None, 'transcriptId': 'ENST00000497611', 'isLofNagnag': None, 'transcriptRank': 3, 'biotype': 'processed_transcript', 'lofFilters': None, 'majorConsequence': 'intron_variant'},
        ],
    },
    'mainTranscriptId': 'ENST00000428239',
    '_sort': [1091502721],
}
VARIANT_ID_4 = '1-91511686-T-G'
VARIANT4 = {
    'variantId': VARIANT_ID_4,
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

        await self._assert_expected_search(
            [VARIANT2, FAMILY_3_VARIANT], quality_filter={'min_gq': 40, 'min_ab': 50}, omit_sample_type='SV_WES',
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
