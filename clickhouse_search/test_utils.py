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
    SV_VARIANT1 as HAIL_SV_VARIANT1,
    SV_VARIANT2 as HAIL_SV_VARIANT2,
    SV_VARIANT3 as HAIL_SV_VARIANT3,
    SV_VARIANT4 as HAIL_SV_VARIANT4,
    GCNV_VARIANT1 as HAIL_GCNV_VARIANT1,
    GCNV_VARIANT2 as HAIL_GCNV_VARIANT2,
    GCNV_VARIANT3 as HAIL_GCNV_VARIANT3,
    GCNV_VARIANT4 as HAIL_GCNV_VARIANT4,
)

VARIANT1 = {**deepcopy(HAIL_VARIANT1), 'key': 1, 'populations': {**deepcopy(HAIL_VARIANT1)['populations'], 'seqr': {'ac': 8, 'hom': 3}}}
VARIANT2 = {**deepcopy(HAIL_VARIANT2), 'key': 2, 'populations': {**deepcopy(HAIL_VARIANT2)['populations'], 'seqr': {'ac': 7, 'hom': 2}}}
VARIANT3 = {**deepcopy(HAIL_VARIANT3), 'key': 3, 'populations': {**deepcopy(HAIL_VARIANT3)['populations'], 'seqr': {'ac': 6, 'hom': 0}}}
VARIANT4 = {**deepcopy(HAIL_VARIANT4), 'key': 4, 'populations': {**deepcopy(HAIL_VARIANT4)['populations'], 'seqr': {'ac': 4, 'hom': 1}}}
PROJECT_2_VARIANT = {**deepcopy(HAIL_PROJECT_2_VARIANT), 'key': 5, 'populations': {**deepcopy(HAIL_PROJECT_2_VARIANT)['populations'], 'seqr': {'ac': 2, 'hom': 0}}}
MITO_VARIANT1 = {**deepcopy(HAIL_MITO_VARIANT1), 'key': 6, 'populations': {**deepcopy(HAIL_MITO_VARIANT1)['populations'], 'seqr': {'ac': 0}, 'seqr_heteroplasmy': {'ac': 1}}}
MITO_VARIANT2 = {**deepcopy(HAIL_MITO_VARIANT2), 'key': 7, 'populations': {**deepcopy(HAIL_MITO_VARIANT2)['populations'], 'seqr': {'ac': 0}, 'seqr_heteroplasmy': {'ac': 1}}}
MITO_VARIANT3 = {**deepcopy(HAIL_MITO_VARIANT3), 'key': 8, 'populations': {**deepcopy(HAIL_MITO_VARIANT3)['populations'], 'seqr': {'ac': 1}, 'seqr_heteroplasmy': {'ac': 0}}}
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
    'populations': {**deepcopy(HAIL_GRCH37_VARIANT)['populations'], 'seqr': {'ac': 3, 'hom': 1}},
}
for genotype in GRCH37_VARIANT['genotypes'].values():
    genotype['sampleType'] = 'WES'
GRCH37_VARIANT['predictions'].update({'fathmm': None, 'mut_pred': None, 'vest': None})
for variant in [GRCH37_VARIANT, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3]:
    for transcripts in variant['transcripts'].values():
        for transcript in transcripts:
            transcript['loftee'] = {field: transcript.pop(field) for field in ['isLofNagnag', 'lofFilters']}
SV_VARIANT1 = {**deepcopy(HAIL_SV_VARIANT1), 'key': 12, 'populations': {**HAIL_SV_VARIANT1['populations'], 'sv_callset': {'ac': 1, 'hom': 0}}}
SV_VARIANT2 = {**deepcopy(HAIL_SV_VARIANT2), 'key': 13, 'populations': {**HAIL_SV_VARIANT2['populations'], 'sv_callset': {'ac': 2, 'hom': 0}}}
SV_VARIANT3 = {**deepcopy(HAIL_SV_VARIANT3), 'key': 14, 'populations': {**HAIL_SV_VARIANT3['populations'], 'sv_callset': {'ac': 4, 'hom': 1}}}
SV_VARIANT4 = {**deepcopy(HAIL_SV_VARIANT4), 'key': 15, 'populations': {**HAIL_SV_VARIANT4['populations'], 'sv_callset': {'ac': 4, 'hom': 1}}}
for variant in [SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4]:
    variant['familyGuids'] = ['F000014_14']
    variant['genotypes'] = {
        'I000018_na21234': {**variant['genotypes']['I000015_na20885'], 'sampleId': 'NA21234', 'individualGuid': 'I000018_na21234', 'familyGuid': 'F000014_14'},
        'I000019_na21987': {**variant['genotypes']['I000025_na20884'], 'sampleId': 'NA21987', 'individualGuid': 'I000019_na21987', 'familyGuid': 'F000014_14'},
        'I000021_na21654': {**variant['genotypes']['I000035_na20883'], 'sampleId': 'NA21654', 'individualGuid': 'I000021_na21654', 'familyGuid': 'F000014_14'},
    }
SV_VARIANT3['cpxIntervals'][0]['chrom'] = SV_VARIANT3['cpxIntervals'][0]['chrom'].replace('chr', '')
GCNV_VARIANT1 = {**deepcopy(HAIL_GCNV_VARIANT1), 'key': 16}
GCNV_VARIANT2 = {**deepcopy(HAIL_GCNV_VARIANT2), 'key': 17}
GCNV_VARIANT3 = {**deepcopy(HAIL_GCNV_VARIANT3), 'key': 18}
GCNV_VARIANT4 = {**deepcopy(HAIL_GCNV_VARIANT4), 'key': 19}

for variant in [VARIANT1, VARIANT2, VARIANT3, VARIANT4, PROJECT_2_VARIANT, GRCH37_VARIANT, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3,
                SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4]:
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
    if variant.get('clinvar'):
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
MULTI_DATA_TYPE_COMP_HET_VARIANT2 = {**VARIANT2, 'selectedMainTranscriptId': 'ENST00000450625'}

GCNV_MULTI_FAMILY_VARIANT1 = deepcopy(GCNV_VARIANT1)
GCNV_MULTI_FAMILY_VARIANT1.update({
    'pos': 22418039,
    'end': 22507821,
    'transcripts': {
        'ENSG00000129562': [{'geneId': 'ENSG00000129562', 'majorConsequence': 'COPY_GAIN'}],
    },
})
GCNV_MULTI_FAMILY_VARIANT1['familyGuids'].append('F000003_3')
GCNV_MULTI_FAMILY_VARIANT1['genotypes'].update({'I000007_na20870': {
    'sampleId': 'NA20870', 'sampleType': 'WES', 'individualGuid': 'I000007_na20870', 'familyGuid': 'F000003_3',
    'numAlt': 1, 'cn': 3, 'qs': 164, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
    'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False, 'filters': [],
}})
GCNV_MULTI_FAMILY_VARIANT1['genotypes']['I000004_hg00731'].update({'start': 22438910, 'end': 22469796, 'geneIds': []})

GCNV_MULTI_FAMILY_VARIANT2 = deepcopy(GCNV_VARIANT2)
GCNV_MULTI_FAMILY_VARIANT2['numExon'] = 26
GCNV_MULTI_FAMILY_VARIANT2['familyGuids'].append('F000003_3')
for genotype in GCNV_MULTI_FAMILY_VARIANT2['genotypes'].values():
    genotype.update({'numExon': 8, 'geneIds': ['ENSG00000103495', 'ENSG00000167371', 'ENSG00000280893']})
GCNV_MULTI_FAMILY_VARIANT2['genotypes'].update({'I000007_na20870': {
    'sampleId': 'NA20870', 'sampleType': 'WES', 'individualGuid': 'I000007_na20870', 'familyGuid': 'F000003_3',
    'numAlt': 1, 'cn': 3, 'qs': 40, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
    'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False, 'filters': [],
}})
GCNV_MULTI_FAMILY_VARIANT2['transcripts'].update({
    'ENSG00000013364': [{'geneId': 'ENSG00000013364', 'majorConsequence': 'LOF'}],
    'ENSG00000079616': [{'geneId': 'ENSG00000079616', 'majorConsequence': 'LOF'}],
    'ENSG00000281348': [{'geneId': 'ENSG00000281348', 'majorConsequence': 'LOF'}],
    'ENSG00000280789': [{'geneId': 'ENSG00000280789', 'majorConsequence': 'LOF'}],
})
MULTI_PROJECT_GCNV_VARIANT3 = {
    **GCNV_VARIANT3,
    'familyGuids': GCNV_VARIANT3['familyGuids'] + ['F000014_14'],
    'genotypes': {
        **GCNV_VARIANT3['genotypes'],
        'I000018_na21234': {
            'sampleId': 'NA21234', 'sampleType': 'WES', 'individualGuid': 'I000018_na21234', 'familyGuid': 'F000014_14',
            'numAlt': 2, 'cn': 4, 'qs': 27, 'defragged': True, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': True, 'prevCall': False, 'prevOverlap': False, 'filters': [],
        },
        'I000019_na21987': {
            'sampleId': 'NA21987', 'sampleType': 'WES', 'individualGuid': 'I000019_na21987', 'familyGuid': 'F000014_14',
            'numAlt': 1, 'cn': 3, 'qs': 51, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': False, 'prevOverlap': True, 'filters': [],
        },
        'I000021_na21654': {
            'sampleId': 'NA21654', 'sampleType': 'WES', 'individualGuid': 'I000021_na21654', 'familyGuid': 'F000014_14', 'numAlt': 0,
            'cn': None, 'qs': None, 'defragged': None, 'start': None, 'end': None, 'numExon': None, 'geneIds': None,
            'newCall': None, 'prevCall': None, 'prevOverlap': None, 'filters': [],
        },
    },
}

LOOKUP_GENOTYPE = {k: v for k, v in PROJECT_2_VARIANT1['genotypes']['I000015_na20885'].items() if k != 'individualGuid'}
VARIANT_LOOKUP_VARIANT = {
    **VARIANT1,
    'liftedFamilyGuids': ['F000014_14'],
    'familyGenotypes': {
        VARIANT1['familyGuids'][0]: sorted([
            {k: v for k, v in g.items() if k != 'individualGuid'} for gs in VARIANT1_BOTH_SAMPLE_TYPES['genotypes'].values() for g in gs
        ], key=lambda x: (x['sampleType'] == 'WES', x['sampleId']), reverse=True),
        'F000011_11': [{**LOOKUP_GENOTYPE, 'sampleType': 'WES'}, LOOKUP_GENOTYPE],
        'F000014_14': [{
            'sampleId': 'NA21234', 'sampleType': 'WGS', 'familyGuid': 'F000014_14',
            'numAlt': 1, 'dp': 27, 'gq': 87, 'ab': 0.531, 'filters': [],
        }],
    }
}
for k in {'familyGuids', 'genotypes'}:
    VARIANT_LOOKUP_VARIANT.pop(k)

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

ALL_SNV_INDEL_PASS_FILTERS = {
    'annotations': {'splice_ai': '0.0'},
    'pathogenicity': {'clinvar': ['likely_pathogenic']},
}
COMP_HET_ALL_PASS_FILTERS = {
    **ALL_SNV_INDEL_PASS_FILTERS,
    'annotations': {**ALL_SNV_INDEL_PASS_FILTERS['annotations'], 'structural': ['DEL', 'CPX', 'INS', 'gCNV_DEL', 'gCNV_DUP']},
}

NEW_SV_FILTER = {'new_structural_variants': ['NEW']}

SV_GENE_COUNTS = {
    'ENSG00000171621': {'total': 2, 'families': {'F000011_11': 2}},
    'ENSG00000083544': {'total': 1, 'families': {'F000011_11': 1}},
    'ENSG00000184986': {'total': 1, 'families': {'F000011_11': 1}},
    'null': {'total': 1, 'families': {'F000011_11': 1}},
}

GCNV_GENE_COUNTS = {
    'ENSG00000103495': {'total': 1, 'families': {'F000002_2': 1}},
    'ENSG00000167371': {'total': 1, 'families': {'F000002_2': 1}},
    'ENSG00000280893': {'total': 1, 'families': {'F000002_2': 1}},
    'ENSG00000275023': {'total': 2, 'families': {'F000002_2': 2}},
    'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
    'ENSG00000277972': {'total': 1, 'families': {'F000002_2': 1}},
}
