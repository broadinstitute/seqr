from copy import deepcopy


FAMILY_3_SAMPLE = {
    'sample_id': 'NA20870', 'individual_guid': 'I000007_na20870', 'family_guid': 'F000003_3',
    'project_guid': 'R0001_1kg', 'affected': 'A', 'sex': 'M',
}
FAMILY_2_VARIANT_SAMPLE_DATA = {'VARIANTS': [
    {'sample_id': 'HG00731', 'individual_guid': 'I000004_hg00731', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'A', 'sex': 'F'},
    {'sample_id': 'HG00732', 'individual_guid': 'I000005_hg00732', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'M'},
    {'sample_id': 'HG00733', 'individual_guid': 'I000006_hg00733', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'F'},
]}
EXPECTED_SAMPLE_DATA = {
    'SV_WES': [
        {'sample_id': 'HG00731', 'individual_guid': 'I000004_hg00731', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'A', 'sex': 'F'},
        {'sample_id': 'HG00732', 'individual_guid': 'I000005_hg00732', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'M'},
        {'sample_id': 'HG00733', 'individual_guid': 'I000006_hg00733', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'F'}
    ],
}
EXPECTED_SAMPLE_DATA.update(deepcopy(FAMILY_2_VARIANT_SAMPLE_DATA))
EXPECTED_SAMPLE_DATA['VARIANTS'].append(FAMILY_3_SAMPLE)
CUSTOM_AFFECTED_SAMPLE_DATA = {'VARIANTS': deepcopy(EXPECTED_SAMPLE_DATA['VARIANTS'])}
CUSTOM_AFFECTED_SAMPLE_DATA['VARIANTS'][0]['affected'] = 'N'
CUSTOM_AFFECTED_SAMPLE_DATA['VARIANTS'][1]['affected'] = 'A'
CUSTOM_AFFECTED_SAMPLE_DATA['VARIANTS'][2]['affected'] = 'U'

FAMILY_1_SAMPLE_DATA = {
    'VARIANTS': [
        {'sample_id': 'NA19675', 'individual_guid': 'I000001_na19675', 'family_guid': 'F000001_1', 'project_guid': 'R0001_1kg', 'affected': 'A', 'sex': 'M'},
        {'sample_id': 'NA19678', 'individual_guid': 'I000002_na19678', 'family_guid': 'F000001_1', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'M'},
    ],
}
FAMILY_2_MISSING_SAMPLE_DATA = deepcopy(FAMILY_1_SAMPLE_DATA)
for s in FAMILY_2_MISSING_SAMPLE_DATA['VARIANTS']:
    s['family_guid'] = 'F000002_2'

FAMILY_2_MITO_SAMPLE_DATA = {'MITO': [
    {'sample_id': 'HG00733', 'individual_guid': 'I000006_hg00733', 'family_guid': 'F000002_2', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'F'},
]}
FAMILY_2_ALL_SAMPLE_DATA = deepcopy(FAMILY_2_VARIANT_SAMPLE_DATA)
FAMILY_2_ALL_SAMPLE_DATA.update(FAMILY_2_MITO_SAMPLE_DATA)

ALL_AFFECTED_SAMPLE_DATA = deepcopy(EXPECTED_SAMPLE_DATA)
ALL_AFFECTED_SAMPLE_DATA.update(FAMILY_2_MITO_SAMPLE_DATA)
FAMILY_5_SAMPLE = {
    'sample_id': 'NA20874', 'individual_guid': 'I000009_na20874', 'family_guid': 'F000005_5', 'project_guid': 'R0001_1kg', 'affected': 'N', 'sex': 'M',
}
ALL_AFFECTED_SAMPLE_DATA['VARIANTS'].append(FAMILY_5_SAMPLE)
FAMILY_11_SAMPLE = {
    'sample_id': 'NA20885', 'individual_guid': 'I000015_na20885', 'family_guid': 'F000011_11', 'project_guid': 'R0003_test', 'affected': 'A', 'sex': 'M',
}
MULTI_PROJECT_SAMPLE_DATA = deepcopy(FAMILY_2_VARIANT_SAMPLE_DATA)
MULTI_PROJECT_SAMPLE_DATA['VARIANTS'].append(FAMILY_11_SAMPLE)
MULTI_PROJECT_MISSING_SAMPLE_DATA = deepcopy(FAMILY_2_MISSING_SAMPLE_DATA)
MULTI_PROJECT_MISSING_SAMPLE_DATA['VARIANTS'].append(FAMILY_11_SAMPLE)

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

HAIL_BACKEND_VARIANTS = [VARIANT2, MULTI_FAMILY_VARIANT]
HAIL_BACKEND_SINGLE_FAMILY_VARIANTS = [VARIANT2, VARIANT3]


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
