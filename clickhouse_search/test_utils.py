from copy import deepcopy

from hail_search.test_utils import (
    VARIANT1 as HAIL_VARIANT1,
    VARIANT2 as HAIL_VARIANT2,
    VARIANT3 as HAIL_VARIANT3,
    VARIANT4 as HAIL_VARIANT4,
)

VARIANT1 = {**deepcopy(HAIL_VARIANT1), 'key': 1}
VARIANT2 = {**deepcopy(HAIL_VARIANT2), 'key': 2}
VARIANT3 = {**deepcopy(HAIL_VARIANT3), 'key': 3}
VARIANT4 = {**deepcopy(HAIL_VARIANT4), 'key': 4}
for variant in [VARIANT1, VARIANT2, VARIANT3, VARIANT4]:
    # clickhouse uses fixed length decimals so values are rounded relative to hail backend
    for genotype in variant['genotypes'].values():
        genotype['ab'] = round(genotype['ab'], 5)
    for pred, pred_val in variant['predictions'].items():
        if isinstance(pred_val, float):
            variant['predictions'][pred] = round(pred_val, 5)
    for pop in variant['populations'].values():
        if 'af' in pop:
            pop['af'] = round(pop['af'], 5)
        if 'filter_af' in pop:
            pop['filter_af'] = round(pop['filter_af'], 5)
    for transcripts in variant['transcripts'].values():
        for transcript in transcripts:
            if transcript['alphamissense']['pathogenicity']:
                transcript['alphamissense']['pathogenicity'] = round(transcript['alphamissense']['pathogenicity'], 5)
    # sort is not computed/annotated at query time
    del variant['_sort']

del VARIANT1['clinvar']['version']
del VARIANT2['clinvar']['version']

FAMILY_3_VARIANT = deepcopy(VARIANT3)
FAMILY_3_VARIANT['familyGuids'] = ['F000003_3']
FAMILY_3_VARIANT['genotypes'] = {
    'I000007_na20870': {
        'sampleId': 'NA20870', 'sampleType': 'WES', 'individualGuid': 'I000007_na20870', 'familyGuid': 'F000003_3',
        'numAlt': 1, 'dp': 28, 'gq': 99, 'ab': 0.6785714285714286, 'filters': [],
    },
}

MULTI_FAMILY_VARIANT = deepcopy(VARIANT3)
MULTI_FAMILY_VARIANT['familyGuids'] += FAMILY_3_VARIANT['familyGuids']
MULTI_FAMILY_VARIANT['genotypes'].update(FAMILY_3_VARIANT['genotypes'])

#SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT = {**MULTI_FAMILY_VARIANT, 'selectedMainTranscriptId': 'ENST00000426137'}
SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT = {**VARIANT3, 'selectedMainTranscriptId': 'ENST00000426137'}
SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4 = {**VARIANT4, 'selectedMainTranscriptId': 'ENST00000350997'}
SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_3 = {**VARIANT3, 'selectedMainTranscriptId': 'ENST00000497611'}
SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2 = {**VARIANT2, 'selectedMainTranscriptId': 'ENST00000459627'}

CACHED_VARIANTS_BY_KEY = {
    variant['key']: {
        'sortedTranscriptConsequences': [],
        **{k: v for k, v in variant.items() if k not in ['mainTranscriptId', 'selectedMainTranscriptId', 'transcripts']},
    } for variant in [VARIANT1, VARIANT2, VARIANT3, VARIANT4]
}
CACHED_VARIANTS_BY_KEY[2]['sortedTranscriptConsequences'] = [{
    'alphamissensePathogenicity': 0.99779,
    'canonical': 1,
    'consequenceTerms': ['missense_variant'],
    'extendedIntronicSpliceRegionVariant': False,
    'fiveutrConsequence': None,
    'geneId': 'ENSG00000177000',
}, {
    'alphamissensePathogenicity': None,
    'canonical': None,
    'consequenceTerms': ['5_prime_UTR_variant'],
    'extendedIntronicSpliceRegionVariant': False,
    'fiveutrConsequence': '5_prime_UTR_stop_codon_loss_variant',
    'geneId': 'ENSG00000177000',
}, {
    'alphamissensePathogenicity': None,
    'canonical': None,
    'consequenceTerms': ['5_prime_UTR_variant'],
    'extendedIntronicSpliceRegionVariant': False,
    'fiveutrConsequence': '5_prime_UTR_stop_codon_loss_variant',
    'geneId': 'ENSG00000177000',
}, {
    'alphamissensePathogenicity': 0.99779,
    'canonical': None,
    'consequenceTerms': ['missense_variant', 'NMD_transcript_variant'],
    'extendedIntronicSpliceRegionVariant': False,
    'fiveutrConsequence': None,
    'geneId': 'ENSG00000277258',
}, {
    'alphamissensePathogenicity': None,
    'canonical': None,
    'consequenceTerms': ['missense_variant'],
    'extendedIntronicSpliceRegionVariant': False,
    'fiveutrConsequence': None,
    'geneId': 'ENSG00000177000',
}, {
    'alphamissensePathogenicity': None,
    'canonical': None,
    'consequenceTerms': ['non_coding_transcript_exon_variant'],
    'extendedIntronicSpliceRegionVariant': False,
    'fiveutrConsequence': None,
    'geneId': 'ENSG00000177000',
}, {
    'alphamissensePathogenicity': None,
    'canonical': None,
    'consequenceTerms': ['non_coding_transcript_exon_variant'],
    'extendedIntronicSpliceRegionVariant': False,
    'fiveutrConsequence': None,
    'geneId': 'ENSG00000177000',
}]
CACHED_VARIANTS_BY_KEY[3]['sortedTranscriptConsequences'] = [{
    'alphamissensePathogenicity': None,
    'canonical': 1,
    'consequenceTerms': ['intron_variant'],
    'extendedIntronicSpliceRegionVariant': False,
    'fiveutrConsequence': None,
    'geneId': 'ENSG00000097046',
}, {
    'alphamissensePathogenicity': None,
    'canonical': None,
    'consequenceTerms': ['intron_variant'],
    'extendedIntronicSpliceRegionVariant': False,
    'fiveutrConsequence': None,
    'geneId': 'ENSG00000177000',
}, {
    'alphamissensePathogenicity': None,
    'canonical': None,
    'consequenceTerms': ['intron_variant'],
    'extendedIntronicSpliceRegionVariant': False,
    'fiveutrConsequence': None,
    'geneId': 'ENSG00000097046',
}, {
    'alphamissensePathogenicity': None,
    'canonical': None,
    'consequenceTerms': ['non_coding_transcript_exon_variant'],
    'extendedIntronicSpliceRegionVariant': False,
    'fiveutrConsequence': None,
    'geneId': 'ENSG00000097046',
}]
CACHED_VARIANTS_BY_KEY[4]['sortedTranscriptConsequences'] = [{
    'alphamissensePathogenicity': None,
    'canonical': None,
    'consequenceTerms': ['splice_donor_variant'],
    'extendedIntronicSpliceRegionVariant': True,
    'fiveutrConsequence': None,
    'geneId': 'ENSG00000097046',
}, {
    'alphamissensePathogenicity': None,
    'canonical': 1,
    'consequenceTerms': ['missense_variant'],
    'extendedIntronicSpliceRegionVariant': False,
    'fiveutrConsequence': None,
    'geneId': 'ENSG00000097046',
}, {
    'alphamissensePathogenicity': None,
    'canonical': None,
    'consequenceTerms': ['missense_variant'],
    'extendedIntronicSpliceRegionVariant': False,
    'fiveutrConsequence': None,
    'geneId': 'ENSG00000097046',
}]

VARIANT_IDS =  ['1-10439-AC-A', '1-91511686-TCA-G']
VARIANT_ID_SEARCH = {
    'locus': {'rawVariantItems': '\n'.join(VARIANT_IDS)}
}

GENE_IDS = ['ENSG00000097046', 'ENSG00000177000']
INTERVALS = ['chr2:1234-5678', 'chr7:1-11100']
LOCATION_SEARCH = {
    'locus': {'rawItems': '\n'.join(GENE_IDS+INTERVALS)},
}
