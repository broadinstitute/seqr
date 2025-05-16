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

# TODO add clinvar version to clickhouse
del VARIANT1['clinvar']['version']
del VARIANT2['clinvar']['version']

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
