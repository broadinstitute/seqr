from copy import deepcopy


FAMILY_3_SAMPLE = {
    'sample_id': 'NA20870', 'individual_guid': 'I000007_na20870', 'family_guid': 'F000003_3',
    'project_guid': 'R0001_1kg', 'affected': 'A',
}
FAMILY_2_VARIANT_SAMPLE_DATA_WITH_SEX = {'SNV_INDEL': [
    {'sample_id': 'HG00731', 'individual_guid': 'I000004_hg00731', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'A', 'sex': 'F'},
    {'sample_id': 'HG00732', 'individual_guid': 'I000005_hg00732', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'M'},
    {'sample_id': 'HG00733', 'individual_guid': 'I000006_hg00733', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'F'},
]}
FAMILY_2_VARIANT_SAMPLE_DATA = deepcopy(FAMILY_2_VARIANT_SAMPLE_DATA_WITH_SEX)
for s in FAMILY_2_VARIANT_SAMPLE_DATA['SNV_INDEL']:
    s.pop('sex')

EXPECTED_SAMPLE_DATA_WITH_SEX = {
    'SV_WES': [
        {'sample_id': 'HG00731', 'individual_guid': 'I000004_hg00731', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'A', 'sex': 'F'},
        {'sample_id': 'HG00732', 'individual_guid': 'I000005_hg00732', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'M'},
        {'sample_id': 'HG00733', 'individual_guid': 'I000006_hg00733', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'F'}
    ],
}
EXPECTED_SAMPLE_DATA_WITH_SEX.update(FAMILY_2_VARIANT_SAMPLE_DATA_WITH_SEX)
EXPECTED_SAMPLE_DATA_WITH_SEX['SNV_INDEL'].append({'sex': 'M', **FAMILY_3_SAMPLE})

EXPECTED_SAMPLE_DATA = deepcopy(EXPECTED_SAMPLE_DATA_WITH_SEX)
for samples in EXPECTED_SAMPLE_DATA.values():
    for s in samples:
        s.pop('sex')

CUSTOM_AFFECTED_SAMPLE_DATA = {'SNV_INDEL': deepcopy(EXPECTED_SAMPLE_DATA['SNV_INDEL'])}
CUSTOM_AFFECTED_SAMPLE_DATA['SNV_INDEL'][0]['affected'] = 'N'
CUSTOM_AFFECTED_SAMPLE_DATA['SNV_INDEL'][1]['affected'] = 'A'
CUSTOM_AFFECTED_SAMPLE_DATA['SNV_INDEL'][2]['affected'] = 'U'

FAMILY_1_SAMPLE_DATA = {
    'SNV_INDEL': [
        {'sample_id': 'NA19675', 'individual_guid': 'I000001_na19675', 'family_guid': 'F000001_1', 'project_guid': 'R0001_1kg', 'affected': 'A'},
        {'sample_id': 'NA19678', 'individual_guid': 'I000002_na19678', 'family_guid': 'F000001_1', 'project_guid': 'R0001_1kg', 'affected': 'N'},
    ],
}
FAMILY_2_MISSING_SAMPLE_DATA = deepcopy(FAMILY_1_SAMPLE_DATA)
for s in FAMILY_2_MISSING_SAMPLE_DATA['SNV_INDEL']:
    s['family_guid'] = 'F000002_2'

FAMILY_2_MITO_SAMPLE_DATA = {'MITO': [
    {'sample_id': 'HG00733', 'individual_guid': 'I000006_hg00733', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N'},
]}
FAMILY_2_ALL_SAMPLE_DATA = deepcopy(FAMILY_2_VARIANT_SAMPLE_DATA)
FAMILY_2_ALL_SAMPLE_DATA.update(FAMILY_2_MITO_SAMPLE_DATA)

ALL_AFFECTED_SAMPLE_DATA = deepcopy(EXPECTED_SAMPLE_DATA)
ALL_AFFECTED_SAMPLE_DATA.update(FAMILY_2_MITO_SAMPLE_DATA)
FAMILY_5_SAMPLE = {
    'sample_id': 'NA20874', 'individual_guid': 'I000009_na20874', 'family_guid': 'F000005_5', 'project_guid': 'R0001_1kg', 'affected': 'N',
}
ALL_AFFECTED_SAMPLE_DATA['SNV_INDEL'].append(FAMILY_5_SAMPLE)
FAMILY_11_SAMPLE = {
    'sample_id': 'NA20885', 'individual_guid': 'I000015_na20885', 'family_guid': 'F000011_11', 'project_guid': 'R0003_test', 'affected': 'A',
}
MULTI_PROJECT_SAMPLE_DATA = deepcopy(FAMILY_2_VARIANT_SAMPLE_DATA)
MULTI_PROJECT_SAMPLE_DATA['SNV_INDEL'].append(FAMILY_11_SAMPLE)
MULTI_PROJECT_MISSING_SAMPLE_DATA = deepcopy(FAMILY_2_MISSING_SAMPLE_DATA)
MULTI_PROJECT_MISSING_SAMPLE_DATA['SNV_INDEL'].append(FAMILY_11_SAMPLE)

SV_WGS_SAMPLE_DATA_WITH_SEX = {'SV_WGS': [{'sex': 'M', **FAMILY_11_SAMPLE}, {
    'sample_id': 'NA20884', 'individual_guid': 'I000025_na20884', 'family_guid': 'F000011_11', 'project_guid': 'R0003_test', 'affected': 'N', 'sex': 'M',
}, {
    'sample_id': 'NA20883', 'individual_guid': 'I000035_na20883', 'family_guid': 'F000011_11', 'project_guid': 'R0003_test', 'affected': 'N', 'sex': 'F',
}]}
SV_WGS_SAMPLE_DATA = deepcopy(SV_WGS_SAMPLE_DATA_WITH_SEX)
for s in SV_WGS_SAMPLE_DATA['SV_WGS']:
    s.pop('sex')

SV_WES_SAMPLE_DATA = {'SV_WES': EXPECTED_SAMPLE_DATA['SV_WES'] + [FAMILY_3_SAMPLE]}

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
            'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'dp': 10, 'gq': 99, 'ab': 0.5,
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'dp': 24, 'gq': 0, 'ab': 0.0,
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'dp': 60, 'gq': 20, 'ab': 0.0,
        },
    },
    'genotypeFilters': '',
    'clinvar': {
       'alleleId': 19473,
       'conflictingPathogenicities': None,
       'goldStars': None,
       'pathogenicity': 'Likely_pathogenic',
       'assertions': None,
       'version': '2023-07-10',
    },
    'hgmd': None,
    'screenRegionType': None,
    'populations': {
        'seqr': {'af': 0.10000000149011612, 'ac': 9, 'an': 90, 'hom': 2},
        'topmed': {'af': 0.0784199982881546, 'ac': 20757, 'an': 264690, 'hom': 0, 'het': 20757},
        'exac': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'het': 0, 'filter_af': 0.0},
        'gnomad_exomes': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'filter_af': 0.0},
        'gnomad_genomes': {'af': 0.034449315071105957, 'ac': 927, 'an': 26912, 'hom': 48, 'hemi': 0, 'filter_af': 0.040276646614074707},
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
    'selectedMainTranscriptId': None,
    '_sort': [1000010439],
}
VARIANT2 = {
    'variantId': '1-38724419-T-G',
    'chrom': '1',
    'pos': 38724419,
    'ref': 'T',
    'alt': 'G',
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '1',
    'liftedOverPos': 11854476,
    'xpos': 1038724419,
    'rsid': 'rs1801131',
    'familyGuids': ['F000002_2'],
    'genotypes': {
       'I000004_hg00731': {
           'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
           'numAlt': 2, 'dp': 36, 'gq': 99, 'ab': 1.0,
       },
       'I000005_hg00732': {
           'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
           'numAlt': 1, 'dp': 32, 'gq': 99, 'ab': 0.625,
       },
       'I000006_hg00733': {
           'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
           'numAlt': 0, 'dp': 33, 'gq': 40, 'ab': 0.0,
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
       'gnomad_genomes': {'af': 0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'filter_af': 0},
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
           {'aminoAcids': 'E/A', 'canonical': None, 'codons': 'gAa/gCa', 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000641446.1:c.1286A>C', 'hgvsp': 'ENSP00000493262.1:p.Glu429Ala', 'transcriptId': 'ENST00000641446', 'isLofNagnag': None, 'transcriptRank': 7, 'biotype': 'nonsense_mediated_decay', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
           {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000641747.1:c.*798A>C', 'hgvsp': None, 'transcriptId': 'ENST00000641747', 'isLofNagnag': None, 'transcriptRank': 8, 'biotype': 'nonsense_mediated_decay', 'lofFilters': None, 'majorConsequence': '3_prime_UTR_variant'},
           {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000641759.1:n.1655A>C', 'hgvsp': None, 'transcriptId': 'ENST00000641759', 'isLofNagnag': None, 'transcriptRank': 9, 'biotype': 'retained_intron', 'lofFilters': None, 'majorConsequence': 'non_coding_transcript_exon_variant'},
           {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000641805.1:n.1803A>C', 'hgvsp': None, 'transcriptId': 'ENST00000641805', 'isLofNagnag': None, 'transcriptRank': 10, 'biotype': 'retained_intron', 'lofFilters': None, 'majorConsequence': 'non_coding_transcript_exon_variant'},
       ],
       'ENSG00000277258': [
           {'aminoAcids': 'E/A', 'canonical': None, 'codons': 'gAa/gCa', 'geneId': 'ENSG00000277258', 'hgvsc': 'ENST00000641820.1:c.551A>C', 'hgvsp': 'ENSP00000492937.1:p.Glu184Ala', 'transcriptId': 'ENST00000641820', 'isLofNagnag': None, 'transcriptRank': 0, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
       ]
    },
    'mainTranscriptId': 'ENST00000376585',
    'selectedMainTranscriptId': None,
    '_sort': [1038724419],
}
VARIANT3 = {
    'variantId': '1-91502721-G-A',
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
            'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'dp': 40, 'gq': 99, 'ab': 1.0,
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'dp': 37, 'gq': 99, 'ab': 0.4594594594594595,
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
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
            {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000097046', 'hgvsc': 'ENST00000426137.1:c.115+890G>A', 'hgvsp': None, 'transcriptId': 'ENST00000426137', 'isLofNagnag': None, 'transcriptRank': 2, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'non_coding_transcript_exon_variant'},
        ],
        'ENSG00000177000': [
            {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000497611.1:n.501+890G>A', 'hgvsp': None, 'transcriptId': 'ENST00000497611', 'isLofNagnag': None, 'transcriptRank': 3, 'biotype': 'processed_transcript', 'lofFilters': None, 'majorConsequence': 'intron_variant'},
        ],
    },
    'mainTranscriptId': 'ENST00000428239',
    'selectedMainTranscriptId': None,
    '_sort': [1091502721],
}
VARIANT4 = {
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
            'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'dp': 29, 'gq': 58, 'ab': 0.1724137931034483,
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'dp': 24, 'gq': 0, 'ab': 0.0,
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
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
    'selectedMainTranscriptId': None,
    '_sort': [1091511686],
}

VARIANT_LOOKUP_VARIANT = {**VARIANT1, 'familyGuids': [], 'genotypes': {}, 'genotypeFilters': ''}

FAMILY_3_VARIANT = deepcopy(VARIANT3)
FAMILY_3_VARIANT['familyGuids'] = ['F000003_3']
FAMILY_3_VARIANT['genotypes'] = {
    'I000007_na20870': {
        'sampleId': 'NA20870', 'sampleType': 'WES', 'individualGuid': 'I000007_na20870', 'familyGuid': 'F000003_3',
        'numAlt': 1, 'dp': 28, 'gq': 99, 'ab': 0.6785714285714286,
    },
}
MULTI_FAMILY_VARIANT = deepcopy(VARIANT3)
MULTI_FAMILY_VARIANT['familyGuids'] += FAMILY_3_VARIANT['familyGuids']
MULTI_FAMILY_VARIANT['genotypes'].update(FAMILY_3_VARIANT['genotypes'])

HAIL_BACKEND_VARIANTS = [VARIANT2, MULTI_FAMILY_VARIANT]
HAIL_BACKEND_SINGLE_FAMILY_VARIANTS = [VARIANT2, VARIANT3]

SV_VARIANT1 = {
    'variantId': 'phase2_DEL_chr1_625',
    'chrom': '1',
    'endChrom': None,
    'pos': 9310023,
    'end': 9310127,
    'rg37LocusEnd': {'contig': '1', 'position': 9370186},
    'xpos': 1009310023,
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '1',
    'liftedOverPos': 9370082,
    'algorithms': 'manta',
    'bothsidesSupport': False,
    'familyGuids': ['F000011_11'],
    'genotypeFilters': 'HIGH_SR_BACKGROUND',
    'genotypes': {
        'I000015_na20885': {
            'sampleId': 'NA20885', 'sampleType': 'WGS', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
            'numAlt': 1, 'cn': 2, 'gq': 0, 'newCall': False, 'prevCall': True, 'prevNumAlt': None,
        }, 'I000025_na20884': {
            'sampleId': 'NA20884', 'sampleType': 'WGS', 'individualGuid': 'I000025_na20884', 'familyGuid': 'F000011_11',
            'numAlt': 0, 'cn': 2, 'gq': 6, 'newCall': False, 'prevCall': True, 'prevNumAlt': None,
        }, 'I000035_na20883': {
            'sampleId': 'NA20883', 'sampleType': 'WGS', 'individualGuid': 'I000035_na20883', 'familyGuid': 'F000011_11',
            'numAlt': 0, 'cn': 2, 'gq': 99, 'newCall': False, 'prevCall': True, 'prevNumAlt': None,
        },
    },
    'populations': {
        'sv_callset': {'af': 0.02421800047159195, 'ac': 141, 'an': 5822, 'hom': 0, 'het': 141},
        'gnomad_svs': {'af': 0.0, 'id': ''},
    },
    'predictions': {'strvctvre': None},
    'cpxIntervals': None,
    'svSourceDetail': None,
    'svType': 'DEL',
    'svTypeDetail': None,
    'transcripts': {
        'ENSG00000171621': [{'geneId': 'ENSG00000171621', 'majorConsequence': 'INTRONIC'}],
    },
    '_sort': [1009310023],
}
SV_VARIANT2 = {
    'variantId': 'cohort_2911.chr1.final_cleanup_INS_chr1_160',
    'chrom': '1',
    'endChrom': None,
    'pos': 9380254,
    'end': 9380286,
    'rg37LocusEnd': {'contig': '4', 'position': 9382012},
    'xpos': 1009380254,
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '1',
    'liftedOverPos': 9440313,
    'algorithms': 'manta',
    'bothsidesSupport': True,
    'familyGuids': ['F000011_11'],
    'genotypeFilters': 'HIGH_SR_BACKGROUND',
    'genotypes': {
        'I000015_na20885': {
            'sampleId': 'NA20885', 'sampleType': 'WGS', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
            'numAlt': 1, 'cn': None, 'gq': 0, 'newCall': True, 'prevCall': False, 'prevNumAlt': None,
        }, 'I000025_na20884': {
            'sampleId': 'NA20884', 'sampleType': 'WGS', 'individualGuid': 'I000025_na20884', 'familyGuid': 'F000011_11',
            'numAlt': 0, 'cn': None, 'gq': 99, 'newCall': True, 'prevCall': False, 'prevNumAlt': None,
        }, 'I000035_na20883': {
            'sampleId': 'NA20883', 'sampleType': 'WGS', 'individualGuid': 'I000035_na20883', 'familyGuid': 'F000011_11',
            'numAlt': 1, 'cn': None, 'gq': 0, 'newCall': True, 'prevCall': False, 'prevNumAlt': None,
        },
    },
    'populations': {
        'sv_callset': {'af': 0.199072003364563, 'ac': 1159, 'an': 5822, 'hom': 0, 'het': 1159},
        'gnomad_svs': {'af': 0.005423000082373619, 'id': 'gnomAD-SV_v2.1_INS_1_299'},
    },
    'predictions': {'strvctvre': None},
    'cpxIntervals': None,
    'svSourceDetail': {'chrom': '4'},
    'svType': 'INS',
    'svTypeDetail': None,
    'transcripts': {
        'ENSG00000171621': [{'geneId': 'ENSG00000171621', 'majorConsequence': 'NEAREST_TSS'}],
    },
    '_sort': [1009380254],
}
SV_VARIANT3 = {
    'variantId': 'phase2_CPX_chr13_35',
    'chrom': '13',
    'endChrom': '17',
    'pos': 63036002,
    'end': 63036041,
    'rg37LocusEnd': {'contig': '17', 'position': 61113402},
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '13',
    'liftedOverPos': 63610135,
    'xpos': 13063036002,
    'algorithms': 'manta',
    'bothsidesSupport': False,
    'familyGuids': ['F000011_11'],
    'genotypeFilters': 'HIGH_SR_BACKGROUND',
    'genotypes': {
        'I000015_na20885': {
            'sampleId': 'NA20885', 'sampleType': 'WGS', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
            'numAlt': 1, 'cn': None, 'gq': 62, 'newCall': False, 'prevCall': True, 'prevNumAlt': None,
        }, 'I000025_na20884': {
            'sampleId': 'NA20884', 'sampleType': 'WGS', 'individualGuid': 'I000025_na20884', 'familyGuid': 'F000011_11',
            'numAlt': 2, 'cn': None, 'gq': 42, 'newCall': False, 'prevCall': True, 'prevNumAlt': None,
        }, 'I000035_na20883': {
            'sampleId': 'NA20883', 'sampleType': 'WGS', 'individualGuid': 'I000035_na20883', 'familyGuid': 'F000011_11',
            'numAlt': 1, 'cn': None, 'gq': 79, 'newCall': False, 'prevCall': True, 'prevNumAlt': None,
        },
    }, 'populations': {
        'sv_callset': {'af': 0.5778080224990845, 'ac': 3364, 'an': 5822, 'hom': 459, 'het': 2446},
        'gnomad_svs': {'af': 0.0, 'id': ''},
    },
    'predictions': {'strvctvre': None},
    'cpxIntervals': [{'chrom': 'chr17', 'start': 22150735, 'end': 22151179, 'type': 'DUP'}],
    'svSourceDetail': None,
    'svType': 'CPX',
    'svTypeDetail': 'dDUP',
    'transcripts': {
        'ENSG00000083544': [{'geneId': 'ENSG00000083544', 'majorConsequence': 'NEAREST_TSS'}],
        'null': [{'geneId': None, 'majorConsequence': 'NEAREST_TSS'}],
    },
    '_sort': [13063036002],
}
SV_VARIANT4 = {
    'variantId': 'phase2_DEL_chr14_4640',
    'chrom': '14',
    'endChrom': None,
    'pos': 106694244,
    'end': 106740587,
    'rg37LocusEnd': None,
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '14',
    'liftedOverPos': 107150261,
    'xpos': 14106694244,
    'algorithms': 'depth,manta',
    'bothsidesSupport': False,
    'familyGuids': ['F000011_11'],
    'genotypeFilters': '',
    'genotypes': {
        'I000015_na20885': {
            'sampleId': 'NA20885', 'sampleType': 'WGS', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
            'numAlt': 2, 'cn': 0, 'gq': 99, 'newCall': False, 'prevCall': True, 'prevNumAlt': None,
        }, 'I000025_na20884': {
            'sampleId': 'NA20884', 'sampleType': 'WGS', 'individualGuid': 'I000025_na20884', 'familyGuid': 'F000011_11',
            'numAlt': 1, 'cn': 1, 'gq': 99, 'newCall': False, 'prevCall': False, 'prevNumAlt': 2,
        }, 'I000035_na20883': {
            'sampleId': 'NA20883', 'sampleType': 'WGS', 'individualGuid': 'I000035_na20883', 'familyGuid': 'F000011_11',
            'numAlt': 1, 'cn': 1, 'gq': 99, 'newCall': False, 'prevCall': False, 'prevNumAlt': 2,
        },
    },
    'populations': {
        'sv_callset': {'af': 0.6100999712944031, 'ac': 3552, 'an': 5822, 'hom': 1053, 'het': 1446},
        'gnomad_svs': {'af': 0.0, 'id': ''},
    },
    'predictions': {'strvctvre': 0.16099999845027924},
    'cpxIntervals': None,
    'svSourceDetail': None,
    'svType': 'DEL',
    'svTypeDetail': None,
    'transcripts': {
        'ENSG00000184986': [{'geneId': 'ENSG00000184986', 'majorConsequence': 'NEAREST_TSS'}],
    },
    '_sort': [14106694244],
}
GCNV_VARIANT1 = {
    'variantId': 'suffix_95340_DUP',
    'chrom': '14',
    'pos': 22438910,
    'end': 22469796,
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '14',
    'liftedOverPos': 22886546,
    'rg37LocusEnd': {'contig': '14', 'position': 23058228},
    'xpos': 14022417556,
    'familyGuids': ['F000002_2'],
    'genotypeFilters': '',
    'genotypes': {
        'I000004_hg00731': {
            'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'cn': 3, 'qs': 38, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False,
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'cn': None, 'qs': None, 'defragged': None, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': None, 'prevCall': None, 'prevOverlap': None,
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'cn': None, 'qs': None, 'defragged': None, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': None, 'prevCall': None, 'prevOverlap': None,
        }
    },
    'populations': {'sv_callset': {'af': 0.076492540538311, 'ac': 1763, 'an': 23048, 'hom': 0, 'het': 0}},
    'predictions': {'strvctvre': 0.1809999942779541},
    'numExon': 0,
    'svType': 'DUP',
    'transcripts': {},
    '_sort': [14022417556],

}
GCNV_VARIANT2 = {
    'variantId': 'suffix_124520_DUP',
    'chrom': '16',
    'pos': 29809156,
    'end': 29815990,
    'xpos': 16029802672,
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '16',
    'liftedOverPos': 29813993,
    'rg37LocusEnd': {'contig': '16', 'position': 29831761},
    'familyGuids': ['F000002_2'],
    'genotypeFilters': '',
    'genotypes': {
        'I000004_hg00731': {
            'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'cn': 3, 'qs': 29, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False,
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'cn': 3, 'qs': 46, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False,
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'cn': 3, 'qs': 37, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False,
        }
    },
    'populations': {'sv_callset': {'af': 0.012322110123932362, 'ac': 284, 'an': 23047, 'hom': 0, 'het': 0}},
    'predictions': {'strvctvre': 0.5479999780654907},
    'numExon': 8,
    'svType': 'DUP',
    'transcripts': {
        'ENSG00000103495': [{'geneId': 'ENSG00000103495', 'majorConsequence': 'COPY_GAIN'}],
        'ENSG00000167371': [{'geneId': 'ENSG00000167371', 'majorConsequence': 'COPY_GAIN'}],
        'ENSG00000280893': [{'geneId': 'ENSG00000280893', 'majorConsequence': 'COPY_GAIN'}],
    },
    '_sort': [16029802672],
}
GCNV_VARIANT3 = {
    'variantId': 'suffix_140593_DUP',
    'chrom': '17',
    'pos': 38717327,
    'end': 38719636,
    'xpos': 17038717327,
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '17',
    'liftedOverPos': 36873580,
    'rg37LocusEnd': {'contig': '17', 'position': 36876246},
    'familyGuids': ['F000002_2'],
    'genotypeFilters': '',
    'genotypes': {
        'I000004_hg00731': {
            'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
            'numAlt': 2, 'cn': 4, 'qs': 13, 'defragged': True, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': True, 'prevCall': False, 'prevOverlap': False,
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'cn': 3, 'qs': 7, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': False, 'prevOverlap': True,
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2', 'numAlt': 0,
            'cn': None, 'qs': None, 'defragged': None, 'start': None, 'end': None, 'numExon': None, 'geneIds': None,
            'newCall': None, 'prevCall': None, 'prevOverlap': None,
        },
    },
    'populations': {'sv_callset': {'af': 0.0015185698866844177, 'ac': 35, 'an': 23048, 'hom': 0, 'het': 0}},
    'predictions': {'strvctvre': 0.7860000133514404},
    'numExon': 3,
    'svType': 'DUP',
    'transcripts': {
        'ENSG00000275023': [{'geneId': 'ENSG00000275023', 'majorConsequence': 'LOF'}],
    },
    '_sort': [17038717327],
}
GCNV_VARIANT4 = {
    'variantId': 'suffix_140608_DUP',
    'chrom': '17',
    'pos': 38721781,
    'end': 38735703,
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '17',
    'liftedOverPos': 36878034,
    'rg37LocusEnd': {'contig': '17', 'position': 36892521},
    'familyGuids': ['F000002_2'],
    'genotypeFilters': '',
    'xpos': 17038721781,
    'genotypes': {
        'I000004_hg00731': {
            'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'cn': 3, 'qs': 28, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False,
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'cn': None, 'qs': None, 'defragged': None, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': None, 'prevCall': None, 'prevOverlap': None,
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'cn': 3, 'qs': 29, 'defragged': False, 'start': None, 'end': 38734440, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False,
        }
    },
    'populations': {'sv_callset': {'af': 0.004989586770534515, 'ac': 115, 'an': 23048, 'hom': 0, 'het': 0}},
    'predictions': {'strvctvre': 0.7099999785423279},
    'numExon': 7,
    'svType': 'DEL',
    'transcripts': {
        'ENSG00000275023': [{'geneId': 'ENSG00000275023', 'majorConsequence': 'LOF'}],
        'ENSG00000277258': [{'geneId': 'ENSG00000277258', 'majorConsequence': 'LOF'}],
        'ENSG00000277972': [{'geneId': 'ENSG00000277972', 'majorConsequence': 'COPY_GAIN'}],
    },
    '_sort': [17038721781],
}

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
    'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False,
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
    'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False,
}})
GCNV_MULTI_FAMILY_VARIANT2['transcripts'].update({
    'ENSG00000013364': [{'geneId': 'ENSG00000013364', 'majorConsequence': 'LOF'}],
    'ENSG00000079616': [{'geneId': 'ENSG00000079616', 'majorConsequence': 'LOF'}],
    'ENSG00000281348': [{'geneId': 'ENSG00000281348', 'majorConsequence': 'LOF'}],
    'ENSG00000280789': [{'geneId': 'ENSG00000280789', 'majorConsequence': 'LOF'}],
})

MITO_VARIANT1 = {
    'variantId': 'M-4429-G-A',
    'chrom': 'M',
    'pos': 4429,
    'ref': 'G',
    'alt': 'A',
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': 'MT',
    'liftedOverPos': 4429,
    'xpos': 25000004429,
    'rsid': 'rs1603219456',
    'familyGuids': ['F000002_2'],
    'genotypes': {'I000006_hg00733': {
        'sampleId': 'HG00733', 'sampleType': 'WGS', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
        'numAlt': 1, 'dp': 3955, 'hl': 0.083, 'mitoCn': 230, 'contamination': 0.0,
    }},
    'genotypeFilters': '',
    'populations': {
        'seqr': {'af': 0.0, 'ac': 0, 'an': 154},
        'seqr_heteroplasmy': {'af': 0.006493506487458944, 'ac': 1, 'an': 154},
        'gnomad_mito': {'af': 0.0, 'ac': 0, 'an': 56419},
        'gnomad_mito_heteroplasmy': {'af': 0.0, 'ac': 0, 'an': 56419, 'max_hl': 0.0},
        'helix': {'af': 0.0, 'ac': 0, 'an': 195983},
        'helix_heteroplasmy': {'af': 1.530745066702366e-05, 'ac': 3, 'an': 195983, 'max_hl': 0.20634999871253967},
    },
    'predictions': {
        'apogee': None,
        'haplogroup_defining': None,
        'hmtvar': 0.05000000074505806,
        'mitotip': 'likely_pathogenic',
        'mut_taster': None,
        'sift': None,
    },
    'commonLowHeteroplasmy': False,
    'highConstraintRegion': True,
    'mitomapPathogenic': None,
    'clinvar': {
        'alleleId': 677748,
        'conflictingPathogenicities': None,
        'goldStars': 1,
        'pathogenicity': 'Uncertain_significance',
        'assertions': [],
        'version': '2023-08-06',
    },
    'transcripts': {
        'ENSG00000210112': [
            {'aminoAcids': None, 'canonical': 1, 'codons': None, 'geneId': 'ENSG00000210112', 'hgvsc': 'ENST00000387377.1:n.28G>A', 'hgvsp': None, 'transcriptId': 'ENST00000387377', 'isLofNagnag': None, 'transcriptRank': 0, 'biotype': 'Mt_tRNA', 'lofFilters': None, 'majorConsequence': 'non_coding_transcript_exon_variant'},
        ],
    },
    'mainTranscriptId': 'ENST00000387377',
    'selectedMainTranscriptId': None,
    '_sort': [25000004429],
}
MITO_VARIANT2 = {
    'variantId': 'M-11597-A-G',
    'chrom': 'M',
    'pos': 11597,
    'ref': 'A',
    'alt': 'G',
    'xpos': 25000011597,
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': 'MT',
    'liftedOverPos': 11597,
    'rsid': None,
    'familyGuids': ['F000002_2'],
    'genotypes': {'I000006_hg00733': {
        'sampleId': 'HG00733', 'sampleType': 'WGS', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
        'numAlt': 1, 'dp': 3845, 'hl': 0.029, 'mitoCn': 247, 'contamination': 0.015,
    }},
    'genotypeFilters': '',
    'populations': {
        'seqr': {'af': 0.0, 'ac': 0, 'an': 154},
        'seqr_heteroplasmy': {'af': 0.006493506487458944, 'ac': 1, 'an': 154},
        'gnomad_mito': {'af': 0.0, 'ac': 0, 'an': 0},
        'gnomad_mito_heteroplasmy': {'af': 0.0, 'ac': 0, 'an': 0, 'max_hl': 0.0},
        'helix': {'af': 0.0, 'ac': 0, 'an': 0},
        'helix_heteroplasmy': {'af': 0.0, 'ac': 0, 'an': 0, 'max_hl': 0.0},
    },
    'predictions': {
        'apogee': 0.5799999833106995,
        'haplogroup_defining': None,
        'hmtvar': 0.75,
        'mitotip': None,
        'mut_taster': 'N',
        'sift': 'D',
    },
    'commonLowHeteroplasmy': False,
    'highConstraintRegion': True,
    'mitomapPathogenic': None,
    'clinvar': None,
    'transcripts': {
        'ENSG00000198886': [
            {'aminoAcids': 'T/A', 'canonical': 1, 'codons': 'Aca/Gca', 'geneId': 'ENSG00000198886', 'hgvsc': 'ENST00000361381.2:c.838A>G', 'hgvsp': 'ENSP00000354961.2:p.Thr280Ala', 'transcriptId': 'ENST00000361381', 'isLofNagnag': None, 'transcriptRank': 0, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
        ],
    },
    'mainTranscriptId': 'ENST00000361381',
    'selectedMainTranscriptId': None,
    '_sort': [25000011597],
}
MITO_VARIANT3 = {
    'variantId': 'M-14783-T-C',
    'chrom': 'M',
    'pos': 14783,
    'ref': 'T',
    'alt': 'C',
    'xpos': 25000014783,
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': 'MT',
    'liftedOverPos': 14783,
    'rsid': 'rs193302982',
    'familyGuids': ['F000002_2'],
    'genotypes': {'I000006_hg00733': {
        'sampleId': 'HG00733', 'sampleType': 'WGS', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
        'numAlt': 2, 'dp': 3943, 'hl': 1.0, 'mitoCn': 214, 'contamination': 0.0,
    }},
    'genotypeFilters': 'artifact_prone_site',
    'populations': {
        'seqr': {'af': 0.019480518996715546, 'ac': 3, 'an': 154},
        'seqr_heteroplasmy': {'af': 0.006493506487458944, 'ac': 1, 'an': 154},
        'gnomad_mito': {'af': 0.05534649267792702, 'ac': 3118, 'an': 56336},
        'gnomad_mito_heteroplasmy': {'af': 5.3251918870955706e-05, 'ac': 3, 'an': 56336, 'max_hl': 1.0},
        'helix': {'af': 0.04884607344865799, 'ac': 9573, 'an': 195983},
        'helix_heteroplasmy': {'af': 9.184470400214195e-05, 'ac': 18, 'an': 195983, 'max_hl': 0.962689995765686},
    },
    'predictions': {
        'apogee': None,
        'haplogroup_defining': 'Y',
        'hmtvar': None,
        'mitotip': None,
        'mut_taster': None,
        'sift': None,
    },
    'commonLowHeteroplasmy': True,
    'highConstraintRegion': False,
    'mitomapPathogenic': True,
    'clinvar': {
        'alleleId': 150280,
        'conflictingPathogenicities': None,
        'goldStars': 0,
        'pathogenicity': 'Likely_pathogenic',
        'assertions': [],
        'version': '2023-08-06',
    },
    'transcripts': {
        'ENSG00000198727': [
            {'aminoAcids': 'L', 'canonical': 1, 'codons': 'Tta/Cta', 'geneId': 'ENSG00000198727', 'hgvsc': 'ENST00000361789.2:c.37T>C', 'hgvsp': 'ENSP00000354554.2:p.Leu13=', 'transcriptId': 'ENST00000361789', 'isLofNagnag': None, 'transcriptRank': 0, 'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'synonymous_variant'},
        ],
    },
    'mainTranscriptId': 'ENST00000361789',
    'selectedMainTranscriptId': None,
    '_sort': [25000014783],
}

LOCATION_SEARCH = {
    'gene_ids': ['ENSG00000177000', 'ENSG00000097046'],
    'intervals': ['2:1234-5678', '7:1-11100', '1:11785723-11806455', '1:91500851-91525764'],
}
EXCLUDE_LOCATION_SEARCH = {'intervals': LOCATION_SEARCH['intervals'], 'exclude_intervals': True}
VARIANT_ID_SEARCH = {'variant_ids': [['1', 10439, 'AC', 'A'], ['1', 91511686, 'TCA', 'G']], 'rs_ids': []}
RSID_SEARCH = {'variant_ids': [], 'rs_ids': ['rs1801131']}

GENE_COUNTS = {
    'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
    'ENSG00000177000': {'total': 3, 'families': {'F000002_2': 2, 'F000011_11': 1}},
    'ENSG00000277258': {'total': 2, 'families': {'F000002_2': 1, 'F000011_11': 1}},
}


def get_hail_search_body(genome_version='GRCh38', num_results=100, sample_data=None, omit_sample_type=None, **search_body):
    sample_data = sample_data or EXPECTED_SAMPLE_DATA
    if omit_sample_type:
        sample_data = {k: v for k, v in sample_data.items() if k != omit_sample_type}

    search = {
        'sample_data': sample_data,
        'genome_version': genome_version,
        'num_results': num_results,
        **search_body,
    }
    search.update(search_body or {})
    return search
