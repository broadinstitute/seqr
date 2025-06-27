from copy import deepcopy

from hail_search.test_utils import (
    VARIANT1 as HAIL_VARIANT1,
    VARIANT2 as HAIL_VARIANT2,
    VARIANT3 as HAIL_VARIANT3,
    VARIANT4 as HAIL_VARIANT4,
    PROJECT_2_VARIANT as HAIL_PROJECT_2_VARIANT,
    GRCH37_VARIANT as HAIL_GRCH37_VARIANT,
    MITO_VARIANT1 as HAIL_MITO_VARIANT1,
    MITO_VARIANT2 as HAIL_MITO_VARIANT2,
    MITO_VARIANT3 as HAIL_MITO_VARIANT3,
)

VARIANT1 = {**deepcopy(HAIL_VARIANT1), 'key': 1}
VARIANT2 = {**deepcopy(HAIL_VARIANT2), 'key': 2}
VARIANT3 = {**deepcopy(HAIL_VARIANT3), 'key': 3}
VARIANT4 = {**deepcopy(HAIL_VARIANT4), 'key': 4}
PROJECT_2_VARIANT = {**deepcopy(HAIL_PROJECT_2_VARIANT), 'key': 5}
MITO_VARIANT1 = {**deepcopy(HAIL_MITO_VARIANT1), 'key': 6}
MITO_VARIANT2 = {**deepcopy(HAIL_MITO_VARIANT2), 'key': 7}
MITO_VARIANT3 = {**deepcopy(HAIL_MITO_VARIANT3), 'key': 8}
for variant in [MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3]:
    variant['genotypes'] = {
        'I000004_hg00731': {
            **variant['genotypes']['I000006_hg00733'], 'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731',
        }
    }
    if variant['clinvar']:
        variant['clinvar'].update({'assertions': None, 'conditions': None, 'submitters': None})
    variant['populations'].update({
        'seqr': {'ac': variant['populations']['seqr']['ac']},
        'seqr_heteroplasmy': {'ac': variant['populations']['seqr_heteroplasmy']['ac']},
    })
MITO_VARIANT3['predictions']['haplogroup_defining'] = True
GRCH37_VARIANT = {
    **deepcopy(HAIL_GRCH37_VARIANT),
    'key': 11,
    'liftedOverGenomeVersion': '38',
    'liftedOverChrom': '7',
    'liftedOverPos': 143271368,
}
for genotype in GRCH37_VARIANT['genotypes'].values():
    genotype['sampleType'] = 'WES'
GRCH37_VARIANT['predictions'].update({'fathmm': None, 'mut_pred': None, 'vest': None})
for variant in [GRCH37_VARIANT, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3]:
    for transcripts in variant['transcripts'].values():
        for transcript in transcripts:
            transcript['loftee'] = {field: transcript.pop(field) for field in ['isLofNagnag', 'lofFilters']}

for variant in [VARIANT1, VARIANT2, VARIANT3, VARIANT4, PROJECT_2_VARIANT, GRCH37_VARIANT, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3]:
    # clickhouse uses fixed length decimals so values are rounded relative to hail backend
    for genotype in variant['genotypes'].values():
        if 'ab' in genotype:
            genotype['ab'] = round(genotype['ab'], 5)
    for pred, pred_val in variant['predictions'].items():
        if isinstance(pred_val, float):
            variant['predictions'][pred] = round(pred_val, 5)
    for pop in variant['populations'].values():
        if 'af' in pop:
            pop['af'] = round(pop['af'], 5)
        if 'filter_af' in pop:
            pop['filter_af'] = round(pop['filter_af'], 5)
        if 'max_hl' in pop:
            pop['max_hl'] = round(pop['max_hl'], 5)
    for transcripts in variant['transcripts'].values():
        for transcript in transcripts:
            if transcript.get('alphamissense', {}).get('pathogenicity'):
                transcript['alphamissense']['pathogenicity'] = round(transcript['alphamissense']['pathogenicity'], 5)
    # sort is not computed/annotated at query time
    del variant['_sort']
    if variant['clinvar']:
        del variant['clinvar']['version']


FAMILY_3_VARIANT = deepcopy(VARIANT3)
FAMILY_3_VARIANT['familyGuids'] = ['F000003_3']
FAMILY_3_VARIANT['genotypes'] = {
    'I000007_na20870': {
        'sampleId': 'NA20870', 'sampleType': 'WES', 'individualGuid': 'I000007_na20870', 'familyGuid': 'F000003_3',
        'numAlt': 1, 'dp': 28, 'gq': 99, 'ab': 0.67857, 'filters': [],
    },
}

MULTI_FAMILY_VARIANT = deepcopy(VARIANT3)
MULTI_FAMILY_VARIANT['familyGuids'] += FAMILY_3_VARIANT['familyGuids']
MULTI_FAMILY_VARIANT['genotypes'].update(FAMILY_3_VARIANT['genotypes'])

# main fixture data has WGS sample_type for this project
PROJECT_2_VARIANT['genotypes']['I000015_na20885']['sampleType'] = 'WGS'
PROJECT_2_VARIANT['populations']['gnomad_genomes']['filter_af'] = 0.00233
PROJECT_2_VARIANT['predictions']['cadd'] = 4.65299

PROJECT_2_VARIANT1 = deepcopy(VARIANT1)
PROJECT_2_VARIANT1['familyGuids'] = ['F000011_11']
PROJECT_2_VARIANT1['genotypes'] = {
    'I000015_na20885': {
        'sampleId': 'NA20885', 'sampleType': 'WGS', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
        'numAlt': 2, 'dp': 6, 'gq': 16, 'ab': 1.0, 'filters': [],
    },
}
MULTI_PROJECT_VARIANT1 = deepcopy(VARIANT1)
MULTI_PROJECT_VARIANT1['familyGuids'] += PROJECT_2_VARIANT1['familyGuids']
MULTI_PROJECT_VARIANT1['genotypes'].update(deepcopy(PROJECT_2_VARIANT1['genotypes']))
MULTI_PROJECT_VARIANT2 = deepcopy(VARIANT2)
MULTI_PROJECT_VARIANT2['familyGuids'].append('F000011_11')
MULTI_PROJECT_VARIANT2['genotypes']['I000015_na20885'] = {
    'sampleId': 'NA20885', 'sampleType': 'WGS', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
    'numAlt': 1, 'dp': 28, 'gq': 99, 'ab': 0.5, 'filters': [],
}

MULTI_PROJECT_BOTH_SAMPLE_TYPE_VARIANTS = [
    deepcopy(v) for v in
    [PROJECT_2_VARIANT, MULTI_PROJECT_VARIANT1, MULTI_PROJECT_VARIANT2, VARIANT3, VARIANT4]
]
for v in MULTI_PROJECT_BOTH_SAMPLE_TYPE_VARIANTS[:-2]:
    v['genotypes']['I000015_na20885'] = [
        {**v['genotypes']['I000015_na20885'], 'sampleType': 'WES'},
        v['genotypes']['I000015_na20885'],
    ]

VARIANT1_BOTH_SAMPLE_TYPES = deepcopy(VARIANT1)
VARIANT1_BOTH_SAMPLE_TYPES['genotypes'] = {
    individual_guid: [genotypes, {**genotypes, 'sampleType': 'WGS'}]
    for individual_guid, genotypes in VARIANT1['genotypes'].items()
}
genotypes = VARIANT1_BOTH_SAMPLE_TYPES['genotypes']
VARIANT1_BOTH_SAMPLE_TYPES['genotypes']['I000004_hg00731'][1]['numAlt'] = 2
VARIANT1_BOTH_SAMPLE_TYPES['genotypes']['I000005_hg00732'][1].update({'gq': 99, 'numAlt': 1})

VARIANT2_BOTH_SAMPLE_TYPES = deepcopy(VARIANT2)
VARIANT2_BOTH_SAMPLE_TYPES['genotypes'] = {
    individual_guid: [genotypes, {**genotypes, 'sampleType': 'WGS'}]
    for individual_guid, genotypes in VARIANT2['genotypes'].items()
}
VARIANT2_BOTH_SAMPLE_TYPES['genotypes']['I000005_hg00732'][1]['numAlt'] = 0

VARIANT3_BOTH_SAMPLE_TYPES = deepcopy(VARIANT3)
VARIANT3_BOTH_SAMPLE_TYPES['genotypes'] = {
    individual_guid: [genotypes, {**genotypes, 'sampleType': 'WGS'}]
    for individual_guid, genotypes in VARIANT3['genotypes'].items()
}

VARIANT4_BOTH_SAMPLE_TYPES = deepcopy(VARIANT4)
VARIANT4_BOTH_SAMPLE_TYPES['genotypes'] = {
    individual_guid: [genotypes, {**genotypes, 'sampleType': 'WGS'}]
    for individual_guid, genotypes in VARIANT4['genotypes'].items()
}
VARIANT4_BOTH_SAMPLE_TYPES['genotypes']['I000006_hg00733'][1]['numAlt'] = 2

SELECTED_ANNOTATION_TRANSCRIPT_MULTI_FAMILY_VARIANT = {**MULTI_FAMILY_VARIANT, 'selectedMainTranscriptId': 'ENST00000497611'}
SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT = {**MULTI_FAMILY_VARIANT, 'selectedMainTranscriptId': 'ENST00000426137'}
SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4 = {**VARIANT4, 'selectedMainTranscriptId': 'ENST00000350997'}
SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_3 = {**VARIANT3, 'selectedMainTranscriptId': 'ENST00000497611'}
SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2 = {**VARIANT2, 'selectedMainTranscriptId': 'ENST00000459627'}

CACHED_CONSEQUENCES_BY_KEY = {1: [], 2: [{
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
}],
3: [{
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
}],
4: [{
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
}],
5: [],
11: [{
    'canonical': 1,
    'consequenceTerms': ['missense_variant'],
    'geneId': 'ENSG00000271079',
}, {
    'canonical': 1,
    'consequenceTerms': ['non_coding_transcript_exon_variant', 'non_coding_transcript_variant'],
    'geneId': 'ENSG00000176227',
}],
}

def format_cached_variant(variant):
    if variant['key'] not in CACHED_CONSEQUENCES_BY_KEY:
        return variant
    return {
        **{k: v for k, v in variant.items() if k not in ['mainTranscriptId', 'selectedMainTranscriptId', 'transcripts']},
        'sortedTranscriptConsequences': CACHED_CONSEQUENCES_BY_KEY[variant['key']],
    }

GENE_COUNTS = {
    'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
    'ENSG00000177000': {'total': 3, 'families': {'F000002_2': 2, 'F000011_11': 1}},
    'ENSG00000277258': {'total': 2, 'families': {'F000002_2': 1, 'F000011_11': 1}},
}

VARIANT_IDS =  ['1-10439-AC-A', '1-91511686-TCA-G']
VARIANT_ID_SEARCH = {
    'locus': {'rawVariantItems': '\n'.join(VARIANT_IDS)}
}

GENE_IDS = ['ENSG00000097046', 'ENSG00000177000']
INTERVALS = ['chr2:1234-5678', 'chr7:1-11100']
LOCATION_SEARCH = {
    'locus': {'rawItems': '\n'.join(GENE_IDS+INTERVALS)},
}

COMP_HET_ALL_PASS_FILTERS = {
    'annotations': {'splice_ai': '0.0', 'structural': ['DEL', 'CPX', 'INS', 'gCNV_DEL', 'gCNV_DUP']},
    'pathogenicity': {'clinvar': ['likely_pathogenic']},
}
