from copy import deepcopy

VARIANT1 = {
    'key': 1,
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
            'numAlt': 1, 'dp': 10, 'gq': 99, 'ab': 0.5, 'filters': [],
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'dp': 24, 'gq': 0, 'ab': 0.0, 'filters': [],
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'dp': 60, 'gq': 20, 'ab': 0.0, 'filters': [],
        },
    },
    'clinvar': {
       'alleleId': 19473,
       'conflictingPathogenicities': None,
       'goldStars': None,
       'pathogenicity': 'Likely_pathogenic',
       'assertions': None,
       'submitters': None,
       'conditions': None,
    },
    'hgmd': None,
    'screenRegionType': None,
    'populations': {
        'seqr': {'ac': 8, 'hom': 3, 'ac_wes': 3, 'ac_wgs': 5, 'hom_wes': 1, 'hom_wgs': 2},
        'topmed': {'af': 0.07842, 'ac': 20757, 'an': 264690, 'hom': 0, 'het': 20757},
        'exac': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'het': 0, 'filter_af': 0.0},
        'gnomad_exomes': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'filter_af': 0.0},
        'gnomad_genomes': {'af': 0.03444932, 'ac': 927, 'an': 26912, 'hom': 48, 'hemi': 0, 'filter_af': 0.04027665},
    },
    'predictions': {
        'cadd': 4.668,
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
    'sortedMotifFeatureConsequences': None,
    'sortedRegulatoryFeatureConsequences': None,
    'mainTranscriptId': None,
    'selectedMainTranscriptId': None,
    'CAID': 'CA16717152',
}
VARIANT2 = {
    'key': 2,
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
           'numAlt': 2, 'dp': 36, 'gq': 99, 'ab': 1.0, 'filters': [],
       },
       'I000005_hg00732': {
           'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
           'numAlt': 1, 'dp': 32, 'gq': 99, 'ab': 0.625, 'filters': [],
       },
       'I000006_hg00733': {
           'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
           'numAlt': 0, 'dp': 33, 'gq': 40, 'ab': 0.0, 'filters': [],
       },
    },
    'clinvar': {
       'alleleId': 18560,
       'conflictingPathogenicities': [
           {'count': 1, 'pathogenicity': 'Likely_pathogenic'},
           {'count': 1, 'pathogenicity': 'Uncertain_significance'},
           {'count': 1, 'pathogenicity': 'Likely_benign'},
           {'count': 5, 'pathogenicity': 'Benign'},
       ],
       'goldStars': 1,
       'pathogenicity': 'Conflicting_classifications_of_pathogenicity',
       'assertions': ['other'],
       'submitters': [
           'Broad Center for Mendelian Genomics, Broad Institute of MIT and Harvard',
           'Illumina Laboratory Services, Illumina',
           'Blueprint Genetics',
           'GenomeConnect, ClinGen'
       ],
       'conditions': [
           'ABCA4-Related Disorders',
           'Severe early-childhood-onset retinal dystrophy',
           'not specified',
           'not provided'
       ],
    },
    'hgmd': {'accession': 'CM981315', 'class': 'DFP'},
    'screenRegionType': None,
    'populations': {
       'seqr': {'ac': 10, 'hom': 3, 'ac_wes': 7, 'ac_wgs': 3, 'hom_wes': 2, 'hom_wgs': 1},
       'topmed': {'af': 0.246152, 'ac': 65154, 'an': 264690, 'hom': 8775, 'het': 47604},
       'exac': {'af': 0.29499999, 'ac': 35805, 'an': 121372, 'hom': 5872, 'hemi': 0, 'het': 24061, 'filter_af': 0.41530353},
       'gnomad_exomes': {'af': 0.00288997, 'ac': 72672, 'an': 251462, 'hom': 1, 'hemi': 0, 'filter_af': 0.0041164},
       'gnomad_genomes': {'af': 0.00344493, 'ac': 927, 'an': 26912, 'hom': 0, 'hemi': 0, 'filter_af': 0.00402766},
    },
    'predictions': {
       'cadd': 25.9,
       'eigen': 2.001,
       'fathmm': 0,
       'gnomad_noncoding': 5.86851,
       'mpc': 0.28205,
       'mut_pred': None,
       'primate_ai': 0.46558,
       'splice_ai': 0.0,
       'splice_ai_consequence': 'No consequence',
       'vest': 0.211,
       'mut_taster': 'P',
       'polyphen': 0.1,
       'revel': 0.197,
       'sift': 0.05,
    },
    'transcripts': {
       'ENSG00000177000': [
           {'aminoAcids': 'L/F', 'canonical': 1, 'codons': 'ttA/ttC', 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000383791.8:c.156A>C', 'hgvsp': 'ENSP00000373301.3:p.Leu52Phe', 'transcriptId': 'ENST00000383791', 'maneSelect': 'NM_004844.5', 'manePlusClinical': None, 'exon': {'index': 2, 'total': 9}, 'intron': None, 'alphamissense': {'pathogenicity': 0.9978}, 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'spliceregion': {'extended_intronic_splice_region_variant': False}, 'utrannotator': {'existingInframeOorfs': None, 'existingOutofframeOorfs': None, 'existingUorfs': None, 'fiveutrAnnotation': None, 'fiveutrConsequence': None}, 'refseqTranscriptId': 'NM_004844.5', 'biotype': 'protein_coding', 'majorConsequence': 'missense_variant', 'consequenceTerms': ['missense_variant'], 'transcriptRank': 0},
           {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000408919.7:c.-384A>C', 'hgvsp': None, 'transcriptId': 'ENST00000408919', 'maneSelect': None, 'manePlusClinical': None, 'exon': {'index': 2, 'total': 9}, 'intron': None, 'alphamissense': {'pathogenicity': None}, 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'spliceregion': {'extended_intronic_splice_region_variant': False}, 'refseqTranscriptId': 'NM_001018009.4', 'biotype': 'protein_coding', 'majorConsequence': '5_prime_UTR_variant', 'consequenceTerms': ['5_prime_UTR_variant'], 'transcriptRank': 1, 'utrannotator': {
               'existingInframeOorfs': 0, 'existingOutofframeOorfs': 1, 'existingUorfs': 10, 'fiveutrConsequence': '5_prime_UTR_stop_codon_loss_variant',
               'fiveutrAnnotation': {'type': None, 'KozakContext': 'GCGATGC', 'KozakStrength': 'Moderate', 'DistanceToCDS': None, 'CapDistanceToStart': None, 'DistanceToStop': None, 'Evidence': False, 'AltStop': 'True', 'AltStopDistanceToCDS': 310, 'FrameWithCDS': 'outOfFrame', 'StartDistanceToCDS': None, 'newSTOPDistanceToCDS': None, 'alt_type': None, 'alt_type_length': None,'ref_StartDistanceToCDS': None, 'ref_type': None, 'ref_type_length': None},
           }},
           {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000426925.5:c.-677A>C', 'hgvsp': None, 'transcriptId': 'ENST00000426925', 'maneSelect': None, 'manePlusClinical': None, 'exon': {'index': 2, 'total': 11}, 'intron': None, 'alphamissense': {'pathogenicity': None}, 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'spliceregion': {'extended_intronic_splice_region_variant': False}, 'refseqTranscriptId': None, 'biotype': 'protein_coding', 'majorConsequence': '5_prime_UTR_variant', 'consequenceTerms': ['5_prime_UTR_variant'], 'transcriptRank': 2, 'utrannotator': {
               'existingInframeOorfs': 0, 'existingOutofframeOorfs': 1, 'existingUorfs': 8,'fiveutrConsequence': '5_prime_UTR_stop_codon_loss_variant',
                'fiveutrAnnotation': {'type': None, 'KozakContext': 'TCAATGC', 'KozakStrength': 'Weak', 'DistanceToCDS': None, 'CapDistanceToStart': None, 'DistanceToStop': None, 'Evidence': False, 'AltStop': 'True', 'AltStopDistanceToCDS': 588, 'FrameWithCDS': 'inFrame', 'StartDistanceToCDS': None, 'newSTOPDistanceToCDS': None, 'alt_type': None, 'alt_type_length': None, 'ref_StartDistanceToCDS': None, 'ref_type': None, 'ref_type_length': None},
            }},
           {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000412806.1:c.138+1722A>C', 'hgvsp': None, 'transcriptId': 'ENST00000412806', 'maneSelect': None, 'manePlusClinical': None, 'exon': None, 'intron': {'index': 1, 'total': 3},'alphamissense': {'pathogenicity': None}, 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'spliceregion': {'extended_intronic_splice_region_variant': False}, 'utrannotator': {'existingInframeOorfs': None, 'existingOutofframeOorfs': None, 'existingUorfs': None, 'fiveutrAnnotation': None, 'fiveutrConsequence': None}, 'refseqTranscriptId': None, 'biotype': 'nonsense_mediated_decay', 'majorConsequence': 'missense_variant', 'consequenceTerms': ['missense_variant'], 'transcriptRank': 3},
           {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000459627.1:n.298A>C', 'hgvsp': None, 'transcriptId': 'ENST00000459627', 'maneSelect': None, 'manePlusClinical': None, 'exon': {'index': 2, 'total': 3}, 'intron': None, 'alphamissense': {'pathogenicity': None}, 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'spliceregion': {'extended_intronic_splice_region_variant': False}, 'utrannotator': {'existingInframeOorfs': None, 'existingOutofframeOorfs': None, 'existingUorfs': None, 'fiveutrAnnotation': None, 'fiveutrConsequence': None}, 'refseqTranscriptId': None, 'biotype': 'protein_coding_CDS_not_defined', 'majorConsequence': 'non_coding_transcript_exon_variant', 'consequenceTerms': ['non_coding_transcript_exon_variant'], 'transcriptRank': 4},
           {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000465894.6:n.33A>C', 'hgvsp': None, 'transcriptId': 'ENST00000465894', 'maneSelect': None, 'manePlusClinical': None, 'exon': {'index': 2, 'total': 5}, 'intron': None, 'alphamissense': {'pathogenicity': None}, 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'spliceregion': {'extended_intronic_splice_region_variant': False}, 'utrannotator': {'existingInframeOorfs': None, 'existingOutofframeOorfs': None, 'existingUorfs': None, 'fiveutrAnnotation': None, 'fiveutrConsequence': None}, 'refseqTranscriptId': None, 'biotype': 'protein_coding_CDS_not_defined', 'majorConsequence': 'non_coding_transcript_exon_variant', 'consequenceTerms': ['non_coding_transcript_exon_variant'], 'transcriptRank': 5},
       ],
       'ENSG00000277258': [
           {'aminoAcids': 'L/F', 'canonical': None, 'codons': 'ttA/ttC', 'geneId': 'ENSG00000277258', 'hgvsc': 'ENST00000450625.1:c.156A>C', 'hgvsp': 'ENSP00000389484.1:p.Leu52Phe', 'transcriptId': 'ENST00000450625', 'maneSelect': 'NM_004944.5', 'manePlusClinical': None, 'exon': {'index': 2, 'total': 5}, 'intron': None, 'alphamissense': {'pathogenicity': 0.9978}, 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'spliceregion': {'extended_intronic_splice_region_variant': False}, 'utrannotator': {'existingInframeOorfs': None, 'existingOutofframeOorfs': None, 'existingUorfs': None, 'fiveutrAnnotation': None, 'fiveutrConsequence': None}, 'refseqTranscriptId': 'NM_004944.5', 'biotype': 'nonsense_mediated_decay', 'majorConsequence': 'missense_variant', 'consequenceTerms': ['missense_variant', 'NMD_transcript_variant'], 'transcriptRank': 0},
       ]
    },
    'mainTranscriptId': 'ENST00000383791',
    'sortedMotifFeatureConsequences': None,
    'sortedRegulatoryFeatureConsequences': None,
    'selectedMainTranscriptId': None,
    'CAID': None,
}
VARIANT3 = {
    'key': 3,
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
            'numAlt': 1, 'dp': 40, 'gq': 99, 'ab': 1.0, 'filters': [],
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'dp': 37, 'gq': 99, 'ab': 0.45946, 'filters': [],
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'dp': 27, 'gq': 99, 'ab': 0.40741, 'filters': [],
        },
    },
    'clinvar': None,
    'hgmd': None,
    'screenRegionType': None,
    'populations': {
        'seqr': {'ac': 7, 'hom': 0, 'ac_wes': 5, 'ac_wgs': 2, 'hom_wes': 0, 'hom_wgs': 0},
        'topmed': {'af': 0.362681, 'ac': 95998, 'an': 264690, 'hom': 19369, 'het': 57260},
        'exac': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'het': 0, 'filter_af': 0.0},
        'gnomad_exomes': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'filter_af': 0.0},
        'gnomad_genomes': {'af': 0.00380411, 'ac': 57757, 'an': 151828, 'hom': 1, 'hemi': 0, 'filter_af': 0.00479778},
    },
    'predictions': {
        'cadd': 28.754,
        'eigen': 1.378,
        'fathmm': None,
        'gnomad_noncoding': 0.73896,
        'mpc': None,
        'mut_pred': None,
        'primate_ai': None,
        'splice_ai': 0.01,
        'splice_ai_consequence': 'Donor gain',
        'vest': None,
        'mut_taster': None,
        'polyphen': None,
        'revel': None,
        'sift': None,
    },
    'transcripts': {
        'ENSG00000097046': [
            {'aminoAcids': None, 'canonical': 1, 'codons': None, 'geneId': 'ENSG00000097046', 'hgvsc': 'ENST00000234626.11:c.-63-251G>A', 'hgvsp': None, 'transcriptId': 'ENST00000234626', 'maneSelect': None, 'manePlusClinical': None, 'exon': None, 'intron': {'index': 1, 'total': 11}, 'alphamissense': {'pathogenicity': None}, 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'spliceregion': {'extended_intronic_splice_region_variant': False}, 'utrannotator': {'existingInframeOorfs': None, 'existingOutofframeOorfs': None, 'existingUorfs': None, 'fiveutrAnnotation': None, 'fiveutrConsequence': None}, 'refseqTranscriptId': None, 'biotype': 'protein_coding', 'majorConsequence': 'intron_variant', 'consequenceTerms': ['intron_variant'], 'transcriptRank': 0},
            {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000097046', 'hgvsc': 'ENST00000428239.5:c.-64+100G>A', 'hgvsp': None, 'transcriptId': 'ENST00000428239', 'maneSelect': None, 'manePlusClinical': None, 'exon': None, 'intron': {'index': 1, 'total': 11}, 'alphamissense': {'pathogenicity': None}, 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'spliceregion': {'extended_intronic_splice_region_variant': False}, 'utrannotator': {'existingInframeOorfs': None, 'existingOutofframeOorfs': None, 'existingUorfs': None, 'fiveutrAnnotation': None, 'fiveutrConsequence': None}, 'refseqTranscriptId': 'NM_001134420.2', 'biotype': 'protein_coding', 'majorConsequence': 'intron_variant', 'consequenceTerms': ['intron_variant'], 'transcriptRank': 1},
            {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000097046', 'hgvsc': 'ENST00000497611.1:n.244G>A', 'hgvsp': None, 'transcriptId': 'ENST00000497611', 'maneSelect': 'NM_003503.4', 'manePlusClinical': None, 'exon': {'index': 1, 'total': 4}, 'intron': None, 'alphamissense': {'pathogenicity': None}, 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'spliceregion': {'extended_intronic_splice_region_variant': False}, 'utrannotator': {'existingInframeOorfs': None, 'existingOutofframeOorfs': None, 'existingUorfs': None, 'fiveutrAnnotation': None, 'fiveutrConsequence': None}, 'refseqTranscriptId': 'NM_003503.4', 'biotype': 'protein_coding_CDS_not_defined', 'majorConsequence': 'non_coding_transcript_exon_variant', 'consequenceTerms': ['non_coding_transcript_exon_variant'], 'transcriptRank': 2},
        ],
        'ENSG00000177000': [
            {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000177000', 'hgvsc': 'ENST00000426137.1:c.-64+100G>A', 'hgvsp': None, 'transcriptId': 'ENST00000426137', 'maneSelect': None, 'manePlusClinical': None, 'exon': None, 'intron': {'index': 1, 'total': 5}, 'alphamissense': {'pathogenicity': None}, 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'spliceregion': {'extended_intronic_splice_region_variant': False}, 'utrannotator': {'existingInframeOorfs': None, 'existingOutofframeOorfs': None, 'existingUorfs': None, 'fiveutrAnnotation': None, 'fiveutrConsequence': None}, 'refseqTranscriptId': None, 'biotype': 'protein_coding', 'majorConsequence': 'intron_variant', 'consequenceTerms': ['intron_variant'], 'transcriptRank': 0},
        ],
    },
    'mainTranscriptId': 'ENST00000234626',
    'sortedMotifFeatureConsequences': None,
    'sortedRegulatoryFeatureConsequences': [{'biotype': 'promoter', 'consequenceTerms': ['regulatory_region_variant'], 'regulatoryFeatureId': 'ENSR00000009706'}],
    'selectedMainTranscriptId': None,
    'CAID': 'CA10960369',
}
VARIANT4 = {
    'key': 4,
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
            'numAlt': 1, 'dp': 29, 'gq': 58, 'ab': 0.27241, 'filters': ['VQSRTrancheSNP99.95to100.00'],
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'dp': 24, 'gq': 30, 'ab': 0.0, 'filters': ['VQSRTrancheSNP99.95to100.00'],
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'dp': 45, 'gq': 30, 'ab': 0.0, 'filters': ['VQSRTrancheSNP99.95to100.00'],
        },
    },
    'clinvar': None,
    'hgmd': None,
    'screenRegionType': 'CTCF-only',
    'populations': {
        'seqr': {'ac': 5, 'hom': 1, 'ac_wes': 2, 'ac_wgs': 3, 'hom_wes': 0, 'hom_wgs': 1},
        'topmed': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'het': 0},
        'exac': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'het': 0, 'filter_af': 0.0},
        'gnomad_exomes': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'filter_af': 0.0},
        'gnomad_genomes': {'af': 0.00026519, 'ac': 39, 'an': 147062, 'hom': 0, 'hemi': 0, 'filter_af': 0.00150301},
    },
    'predictions': {
        'cadd': 29.9,
        'eigen': 9.491,
        'fathmm': 0,
        'gnomad_noncoding': 0.23005,
        'mpc': 0.83268,
        'mut_pred': 0.687,
        'primate_ai': 0.69959,
        'splice_ai': 0.0,
        'splice_ai_consequence': 'No consequence',
        'vest': 0.858,
        'mut_taster': 'N',
        'polyphen': 0,
        'revel': 0.526,
        'sift': 0,
    },
    'transcripts': {
        'ENSG00000097046': [
            {'aminoAcids': None, 'canonical': None, 'codons': None, 'geneId': 'ENSG00000097046', 'hgvsc': 'ENST00000466716.5:c.-264+1G>A', 'hgvsp': None, 'transcriptId': 'ENST00000466716', 'maneSelect': None, 'manePlusClinical': None, 'exon': None, 'intron': {'index': 1, 'total': 3}, 'alphamissense': {'pathogenicity': None}, 'loftee': {'isLofNagnag': None, 'lofFilters': ['5UTR_SPLICE']}, 'spliceregion': {'extended_intronic_splice_region_variant': True}, 'utrannotator': {'existingInframeOorfs': None, 'existingOutofframeOorfs': None, 'existingUorfs': None, 'fiveutrAnnotation': None, 'fiveutrConsequence': None}, 'refseqTranscriptId': None, 'biotype': 'protein_coding', 'majorConsequence': 'splice_donor_variant', 'consequenceTerms': ['splice_donor_variant'],  'transcriptRank': 0},
            {'aminoAcids': None, 'canonical': 1, 'codons': None, 'geneId': 'ENSG00000097046', 'hgvsc': 'ENST00000350997.12:c.375+139G>A', 'hgvsp': None, 'transcriptId': 'ENST00000350997', 'maneSelect': 'NM_013402.7', 'manePlusClinical': None, 'exon': None, 'intron': {'index': 1, 'total': 11}, 'alphamissense': {'pathogenicity': 0.1}, 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'spliceregion': {'extended_intronic_splice_region_variant': False}, 'utrannotator': {'existingInframeOorfs': None, 'existingOutofframeOorfs': None, 'existingUorfs': None, 'fiveutrAnnotation': None, 'fiveutrConsequence': None}, 'refseqTranscriptId': 'NM_013402.7', 'biotype': 'protein_coding', 'majorConsequence': 'missense_variant', 'consequenceTerms': ['missense_variant'], 'transcriptRank': 1},
            {'aminoAcids': 'T/I', 'canonical': None, 'codons': 'aCc/aTc', 'geneId': 'ENSG00000097046', 'hgvsc': 'ENST00000257261.10:c.131C>T', 'hgvsp': 'ENSP00000257261.6:p.Thr44Ile', 'transcriptId': 'ENST00000257261', 'maneSelect': None, 'manePlusClinical': None, 'exon': {'index': 1, 'total': 12}, 'intron': None, 'alphamissense': {'pathogenicity': None}, 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'spliceregion': {'extended_intronic_splice_region_variant': False}, 'utrannotator': {'existingInframeOorfs': None, 'existingOutofframeOorfs': None, 'existingUorfs': None, 'fiveutrAnnotation': None, 'fiveutrConsequence': None}, 'refseqTranscriptId': 'NM_001281501.1', 'biotype': 'protein_coding', 'majorConsequence': 'missense_variant', 'consequenceTerms': ['missense_variant'], 'transcriptRank': 2},
        ],
    },
    'mainTranscriptId': 'ENST00000466716',
    'sortedMotifFeatureConsequences': [
        {'consequenceTerms': ['TF_binding_site_variant'], 'motifFeatureId': 'ENSM00093424674'},
        {'consequenceTerms': ['TF_binding_site_variant'], 'motifFeatureId': 'ENSM00036268032'},
    ],
    'sortedRegulatoryFeatureConsequences': [
        {'biotype': 'promoter', 'consequenceTerms': ['regulatory_region_variant'], 'regulatoryFeatureId': 'ENSR00000040341'},
    ],
    'selectedMainTranscriptId': None,
    'CAID': 'CA341062623',
}

PROJECT_2_VARIANT = {
    'key': 5,
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
            'sampleId': 'NA20885', 'sampleType': 'WES', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
            'numAlt': 1, 'dp': 8, 'gq': 14, 'ab': 0.875, 'filters': [],
        }
    },
    'clinvar': None,
    'hgmd': None,
    'screenRegionType': None,
    'populations': {
        'seqr': {'ac': 2, 'hom': 0, 'ac_wes': 1, 'ac_wgs': 1, 'hom_wes': 0, 'hom_wgs': 0},
        'topmed': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'het': 0},
        'exac': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'het': 0, 'filter_af': 0.0},
        'gnomad_exomes': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'filter_af': 0.0},
        'gnomad_genomes': {'af': 0.0001243, 'ac': 2, 'an': 16090, 'hom': 0, 'hemi': 0, 'filter_af': 0.00234},
    },
    'predictions': {
        'cadd': 4.653,
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
    'sortedMotifFeatureConsequences': None,
    'sortedRegulatoryFeatureConsequences': None,
    'CAID': 'CA520798130',
}

GRCH37_VARIANT = {
    'key': 11,
    'variantId': '7-143270172-A-G',
    'xpos': 7143270172,
    'chrom': '7',
    'pos': 143270172,
    'ref': 'A',
    'alt': 'G',
    'genomeVersion': '37',
    'liftedOverGenomeVersion': '38',
    'liftedOverChrom': '7',
    'liftedOverPos': 143271368,
    'rsid': 'rs72611576',
    'familyGuids': ['F000002_2'],
    'genotypes': {
        'I000004_hg00731': {
            'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731',
            'familyGuid': 'F000002_2', 'numAlt': 2, 'dp': 16, 'gq': 48, 'ab': 1, 'filters': ['VQSRTrancheSNP99.90to99.95'],
        }, 'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733',
            'familyGuid': 'F000002_2', 'numAlt': None, 'dp': None, 'gq': 0, 'ab': None,
            'filters': ['VQSRTrancheSNP99.90to99.95'],
        },
    },
    'populations': {
        'seqr': {'ac': 2, 'hom': 1, 'ac_wes': 2, 'ac_wgs': 0, 'hom_wes': 1, 'hom_wgs': 0},
        'topmed': {'af': 0.52131897, 'ac': 65461, 'an': 125568, 'hom': 16156, 'het': 33149},
        'exac': {'af': 0.63, 'ac': 66593, 'an': 104352, 'hom': 22162, 'hemi': 0, 'het': 22269, 'filter_af': 0.81987739},
        'gnomad_exomes': {'af': 0.63542193, 'ac': 137532, 'an': 216442, 'hom': 45869, 'hemi': 0, 'filter_af': 0.82261163},
        'gnomad_genomes': {'af': 0.61364776, 'ac': 14649, 'an': 23872, 'hom': 4584, 'hemi': 0, 'filter_af': 0.82843894},
    },
    'predictions': {
        'cadd': 13.02, 'eigen': 3.951, 'primate_ai': 0.49064,
        'splice_ai': 0, 'splice_ai_consequence': 'No consequence', 'fathmm': None,
        'mpc': None, 'mut_taster': None, 'polyphen': None, 'revel': None, 'sift': None, 'mut_pred': None, 'vest': None,
    },
    'clinvar': None,
    'hgmd': None,
    'transcripts': {
        'ENSG00000271079': [
            {'aminoAcids': 'E/G', 'canonical': 1, 'codons': 'gAa/gGa', 'geneId': 'ENSG00000271079',
             'hgvsc': 'ENST00000420911.2:c.1262A>G', 'hgvsp': 'ENSP00000474204.1:p.Glu421Gly',
             'transcriptId': 'ENST00000420911', 'loftee': {'isLofNagnag': None, 'lofFilters': None},'transcriptRank': 0,
             'consequenceTerms': ['missense_variant'], 'biotype': 'protein_coding', 'majorConsequence': 'missense_variant'},
        ],
        'ENSG00000176227': [
            {'aminoAcids': None, 'canonical': 1, 'codons': None, 'geneId': 'ENSG00000176227',
             'hgvsc': 'ENST00000447022.1:n.1354A>G', 'hgvsp': None,
             'transcriptId': 'ENST00000447022', 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'transcriptRank': 0,
             'biotype': 'processed_pseudogene', 'majorConsequence': 'non_coding_transcript_exon_variant',
             'consequenceTerms': ['non_coding_transcript_exon_variant', 'non_coding_transcript_variant']},
        ],
    },
    'mainTranscriptId': 'ENST00000420911',
    'selectedMainTranscriptId': None,
    'CAID': 'CA4540310',
}

MITO_VARIANT1 = {
    'key': 6,
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
    'genotypes': {'I000004_hg00731': {
        'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
        'numAlt': 1, 'dp': 3955, 'hl': 0.083, 'mitoCn': 230, 'contamination': 0.0, 'filters': [],
    }},
    'populations': {
        'seqr': {'ac': 0, 'ac_wes': 0, 'ac_wgs': 0},
        'seqr_heteroplasmy': {'ac': 1, 'ac_wes': 1, 'ac_wgs': 0},
        'gnomad_mito': {'af': 0.0, 'ac': 0, 'an': 56419},
        'gnomad_mito_heteroplasmy': {'af': 0.0, 'ac': 0, 'an': 56419, 'max_hl': 0.0},
        'helix': {'af': 0.0, 'ac': 0, 'an': 195983},
        'helix_heteroplasmy': {'af': 0.00001531, 'ac': 3, 'an': 195983, 'max_hl': 0.20635},
    },
    'predictions': {
        'apogee': None,
        'haplogroup_defining': None,
        'hmtvar': 0.05,
        'mitotip': 'likely_pathogenic',
        'mut_taster': None,
        'sift': None,
        'mlc': 3.38874,
    },
    'commonLowHeteroplasmy': False,
    'mitomapPathogenic': None,
    'clinvar': {
        'alleleId': 677748,
        'conflictingPathogenicities': None,
        'goldStars': 1,
        'pathogenicity': 'Uncertain_significance',
        'assertions': None,
        'conditions': None,
        'submitters': None,
    },
    'transcripts': {
        'ENSG00000210112': [
            {'aminoAcids': None, 'canonical': 1, 'codons': None, 'geneId': 'ENSG00000210112', 'hgvsc': 'ENST00000387377.1:n.28G>A', 'hgvsp': None, 'transcriptId': 'ENST00000387377', 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'transcriptRank': 0, 'biotype': 'Mt_tRNA', 'majorConsequence': 'non_coding_transcript_exon_variant', 'consequenceTerms': ['non_coding_transcript_exon_variant']},
        ],
    },
    'mainTranscriptId': 'ENST00000387377',
    'selectedMainTranscriptId': None,
}
MITO_VARIANT2 = {
    'key': 7,
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
    'genotypes': {'I000004_hg00731': {
        'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
        'numAlt': 1, 'dp': 3845, 'hl': 0.029, 'mitoCn': 247, 'contamination': 0.015, 'filters': [],
    }},
    'populations': {
        'seqr': {'ac': 0, 'ac_wes': 0, 'ac_wgs': 0},
        'seqr_heteroplasmy': {'ac': 1, 'ac_wes': 1, 'ac_wgs': 0},
        'gnomad_mito': {'af': 0.0, 'ac': 0, 'an': 0},
        'gnomad_mito_heteroplasmy': {'af': 0.0, 'ac': 0, 'an': 0, 'max_hl': 0.0},
        'helix': {'af': 0.0, 'ac': 0, 'an': 0},
        'helix_heteroplasmy': {'af': 0.0, 'ac': 0, 'an': 0, 'max_hl': 0.0},
    },
    'predictions': {
        'apogee': 0.58,
        'haplogroup_defining': None,
        'hmtvar': 0.75,
        'mitotip': None,
        'mut_taster': 'N',
        'sift': 0,
        'mlc': None,
    },
    'commonLowHeteroplasmy': False,
    'mitomapPathogenic': None,
    'clinvar': None,
    'transcripts': {
        'ENSG00000198886': [
            {'aminoAcids': 'T/A', 'canonical': 1, 'codons': 'Aca/Gca', 'geneId': 'ENSG00000198886', 'hgvsc': 'ENST00000361381.2:c.838A>G', 'hgvsp': 'ENSP00000354961.2:p.Thr280Ala', 'transcriptId': 'ENST00000361381', 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'transcriptRank': 0, 'biotype': 'protein_coding', 'majorConsequence': 'missense_variant', 'consequenceTerms': ['missense_variant']},
        ],
    },
    'mainTranscriptId': 'ENST00000361381',
    'selectedMainTranscriptId': None,
}
MITO_VARIANT3 = {
    'key': 8,
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
    'genotypes': {'I000004_hg00731': {
        'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
        'numAlt': 2, 'dp': 3943, 'hl': 1.0, 'mitoCn': 214, 'contamination': 0.0, 'filters': ['artifact_prone_site'],
    }},
    'populations': {
        'seqr': {'ac': 1, 'ac_wes': 1, 'ac_wgs': 0},
        'seqr_heteroplasmy': {'ac': 0, 'ac_wes': 0, 'ac_wgs': 0},
        'gnomad_mito': {'af': 0.05534649, 'ac': 3118, 'an': 56336},
        'gnomad_mito_heteroplasmy': {'af': 0.00005325, 'ac': 3, 'an': 56336, 'max_hl': 1.0},
        'helix': {'af': 0.04884607, 'ac': 9573, 'an': 195983},
        'helix_heteroplasmy': {'af': 0.00009184, 'ac': 18, 'an': 195983, 'max_hl': 0.96269},
    },
    'predictions': {
        'apogee': None,
        'haplogroup_defining': True,
        'hmtvar': None,
        'mitotip': None,
        'mut_taster': None,
        'sift': None,
        'mlc': 0.7514,
    },
    'commonLowHeteroplasmy': True,
    'mitomapPathogenic': True,
    'clinvar': {
        'alleleId': 150280,
        'conflictingPathogenicities': None,
        'goldStars': 0,
        'pathogenicity': 'Likely_pathogenic',
        'assertions': None,
        'conditions': None,
        'submitters': None,
    },
    'transcripts': {
        'ENSG00000198727': [
            {'aminoAcids': 'L', 'canonical': 1, 'codons': 'Tta/Cta', 'geneId': 'ENSG00000198727', 'hgvsc': 'ENST00000361789.2:c.37T>C', 'hgvsp': 'ENSP00000354554.2:p.Leu13=', 'transcriptId': 'ENST00000361789', 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'transcriptRank': 0, 'biotype': 'protein_coding', 'majorConsequence': 'synonymous_variant', 'consequenceTerms': ['synonymous_variant']},
        ],
    },
    'mainTranscriptId': 'ENST00000361789',
    'selectedMainTranscriptId': None,
}

SV_VARIANT1 = {
    'key': 12,
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
    'familyGuids': ['F000014_14'],
    'genotypes': {
        'I000018_na21234': {
            'sampleId': 'NA21234', 'sampleType': 'WGS', 'individualGuid': 'I000018_na21234', 'familyGuid': 'F000014_14',
            'numAlt': 1, 'cn': 2, 'gq': 0, 'newCall': False, 'prevCall': True, 'prevNumAlt': None, 'filters': ['HIGH_SR_BACKGROUND'],
        }, 'I000019_na21987': {
            'sampleId': 'NA21987', 'sampleType': 'WGS', 'individualGuid': 'I000019_na21987', 'familyGuid': 'F000014_14',
            'numAlt': 0, 'cn': 2, 'gq': 6, 'newCall': False, 'prevCall': True, 'prevNumAlt': None, 'filters': ['HIGH_SR_BACKGROUND'],
        }, 'I000021_na21654': {
            'sampleId': 'NA21654', 'sampleType': 'WGS', 'individualGuid': 'I000021_na21654', 'familyGuid': 'F000014_14',
            'numAlt': 0, 'cn': 2, 'gq': 99, 'newCall': False, 'prevCall': True, 'prevNumAlt': None, 'filters': ['HIGH_SR_BACKGROUND'],
        },
    },
    'populations': {
        'sv_callset': {'ac': 1, 'hom': 0},
        'gnomad_svs': {'af': 0.0, 'id': '', 'hom': 0, 'het': 0},
    },
    'predictions': {'strvctvre': None},
    'cpxIntervals': None,
    'svSourceDetail': None,
    'svType': 'DEL',
    'svTypeDetail': None,
    'transcripts': {
        'ENSG00000171621': [{'geneId': 'ENSG00000171621', 'majorConsequence': 'INTRONIC'}],
    },
}
SV_VARIANT2 = {
    'key': 13,
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
    'familyGuids': ['F000014_14'],
    'genotypes': {
        'I000018_na21234': {
            'sampleId': 'NA21234', 'sampleType': 'WGS', 'individualGuid': 'I000018_na21234', 'familyGuid': 'F000014_14',
            'numAlt': 1, 'cn': None, 'gq': 0, 'newCall': True, 'prevCall': False, 'prevNumAlt': None, 'filters': ['HIGH_SR_BACKGROUND'],
        }, 'I000019_na21987': {
            'sampleId': 'NA21987', 'sampleType': 'WGS', 'individualGuid': 'I000019_na21987', 'familyGuid': 'F000014_14',
            'numAlt': 0, 'cn': None, 'gq': 99, 'newCall': True, 'prevCall': False, 'prevNumAlt': None, 'filters': ['HIGH_SR_BACKGROUND'],
        }, 'I000021_na21654': {
            'sampleId': 'NA21654', 'sampleType': 'WGS', 'individualGuid': 'I000021_na21654', 'familyGuid': 'F000014_14',
            'numAlt': 1, 'cn': None, 'gq': 0, 'newCall': True, 'prevCall': False, 'prevNumAlt': None, 'filters': ['HIGH_SR_BACKGROUND'],
        },
    },
    'populations': {
        'sv_callset': {'ac': 2, 'hom': 0},
        'gnomad_svs': {'af': 0.005423, 'id': 'gnomAD-SV_v3_INS_1_299', 'hom': 10359, 'het': 35634},
    },
    'predictions': {'strvctvre': None},
    'cpxIntervals': None,
    'svSourceDetail': {'chrom': '4'},
    'svType': 'INS',
    'svTypeDetail': None,
    'transcripts': {
        'ENSG00000171621': [{'geneId': 'ENSG00000171621', 'majorConsequence': 'NEAREST_TSS'}],
    },
}
SV_VARIANT3 = {
    'key': 14,
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
    'familyGuids': ['F000014_14'],
    'genotypes': {
        'I000018_na21234': {
            'sampleId': 'NA21234', 'sampleType': 'WGS', 'individualGuid': 'I000018_na21234', 'familyGuid': 'F000014_14',
            'numAlt': 1, 'cn': None, 'gq': 62, 'newCall': False, 'prevCall': True, 'prevNumAlt': None, 'filters': ['HIGH_SR_BACKGROUND'],
        }, 'I000019_na21987': {
            'sampleId': 'NA21987', 'sampleType': 'WGS', 'individualGuid': 'I000019_na21987', 'familyGuid': 'F000014_14',
            'numAlt': 2, 'cn': None, 'gq': 42, 'newCall': False, 'prevCall': True, 'prevNumAlt': None, 'filters': ['HIGH_SR_BACKGROUND'],
        }, 'I000021_na21654': {
            'sampleId': 'NA21654', 'sampleType': 'WGS', 'individualGuid': 'I000021_na21654', 'familyGuid': 'F000014_14',
            'numAlt': 1, 'cn': None, 'gq': 79, 'newCall': False, 'prevCall': True, 'prevNumAlt': None, 'filters': ['HIGH_SR_BACKGROUND'],
        },
    }, 'populations': {
        'sv_callset': {'ac': 4, 'hom': 1},
        'gnomad_svs': {'af': 0.0, 'id': '', 'hom': 0, 'het': 0},
    },
    'predictions': {'strvctvre': None},
    'cpxIntervals': [{'chrom': '17', 'start': 22150735, 'end': 22151179, 'type': 'DUP'}],
    'svSourceDetail': None,
    'svType': 'CPX',
    'svTypeDetail': 'dDUP',
    'transcripts': {
        'ENSG00000083544': [{'geneId': 'ENSG00000083544', 'majorConsequence': 'NEAREST_TSS'}],
        'null': [{'geneId': None, 'majorConsequence': 'NEAREST_TSS'}],
    },
}
SV_VARIANT4 = {
    'key': 15,
    'variantId': 'phase2_DEL_chr14_4640',
    'chrom': '17',
    'endChrom': None,
    'pos': 38719997,
    'end': 38737237,
    'rg37LocusEnd': None,
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '17',
    'liftedOverPos': 107150261,
    'xpos': 17038719997,
    'algorithms': 'depth,manta',
    'bothsidesSupport': False,
    'familyGuids': ['F000014_14'],
    'genotypes': {
        'I000018_na21234': {
            'sampleId': 'NA21234', 'sampleType': 'WGS', 'individualGuid': 'I000018_na21234', 'familyGuid': 'F000014_14',
            'numAlt': 2, 'cn': 0, 'gq': 99, 'newCall': False, 'prevCall': True, 'prevNumAlt': None, 'filters': [],
        }, 'I000019_na21987': {
            'sampleId': 'NA21987', 'sampleType': 'WGS', 'individualGuid': 'I000019_na21987', 'familyGuid': 'F000014_14',
            'numAlt': 1, 'cn': 1, 'gq': 99, 'newCall': False, 'prevCall': False, 'prevNumAlt': 2, 'filters': [],
        }, 'I000021_na21654': {
            'sampleId': 'NA21654', 'sampleType': 'WGS', 'individualGuid': 'I000021_na21654', 'familyGuid': 'F000014_14',
            'numAlt': 1, 'cn': 1, 'gq': 99, 'newCall': False, 'prevCall': False, 'prevNumAlt': 2, 'filters': [],
        },
    },
    'populations': {
        'sv_callset': {'ac': 4, 'hom': 1},
        'gnomad_svs': {'af': 0.0, 'id': '', 'hom': 0, 'het': 0},
    },
    'predictions': {'strvctvre': 0.161},
    'cpxIntervals': None,
    'svSourceDetail': None,
    'svType': 'DEL',
    'svTypeDetail': None,
    'transcripts': {
        'ENSG00000184986': [{'geneId': 'ENSG00000184986', 'majorConsequence': 'NEAREST_TSS'}],
    },
}

GCNV_VARIANT1 = {
    'key': 16,
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
    'genotypes': {
        'I000004_hg00731': {
            'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'cn': 3, 'qs': 38, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False, 'filters': [],
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'cn': None, 'qs': None, 'defragged': None, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': None, 'prevCall': None, 'prevOverlap': None, 'filters': [],
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'cn': None, 'qs': None, 'defragged': None, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': None, 'prevCall': None, 'prevOverlap': None, 'filters': [],
        }
    },
    'populations': {'sv_callset': {'af': 0.07649254, 'ac': 1763, 'an': 23048, 'hom': 0, 'het': 0}},
    'predictions': {'strvctvre': 0.181},
    'numExon': 0,
    'svType': 'DUP',
    'transcripts': {},
}
GCNV_VARIANT2 = {
    'key': 17,
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
    'genotypes': {
        'I000004_hg00731': {
            'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'cn': 3, 'qs': 29, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False, 'filters': [],
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'cn': 3, 'qs': 46, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False, 'filters': [],
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'cn': 3, 'qs': 37, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False, 'filters': [],
        }
    },
    'populations': {'sv_callset': {'af': 0.01232211, 'ac': 284, 'an': 23047, 'hom': 0, 'het': 0}},
    'predictions': {'strvctvre': 0.548},
    'numExon': 8,
    'svType': 'DUP',
    'transcripts': {
        'ENSG00000103495': [{'geneId': 'ENSG00000103495', 'majorConsequence': 'COPY_GAIN'}],
        'ENSG00000167371': [{'geneId': 'ENSG00000167371', 'majorConsequence': 'COPY_GAIN'}],
        'ENSG00000280893': [{'geneId': 'ENSG00000280893', 'majorConsequence': 'COPY_GAIN'}],
    },
}
GCNV_VARIANT3 = {
    'key': 18,
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
    'genotypes': {
        'I000004_hg00731': {
            'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
            'numAlt': 2, 'cn': 4, 'qs': 13, 'defragged': True, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': True, 'prevCall': False, 'prevOverlap': False, 'filters': [],
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'cn': 3, 'qs': 7, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': False, 'prevOverlap': True, 'filters': [],
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2', 'numAlt': 0,
            'cn': None, 'qs': None, 'defragged': None, 'start': None, 'end': None, 'numExon': None, 'geneIds': None,
            'newCall': None, 'prevCall': None, 'prevOverlap': None, 'filters': [],
        },
    },
    'populations': {'sv_callset': {'af': 0.00151857, 'ac': 35, 'an': 23048, 'hom': 0, 'het': 0}},
    'predictions': {'strvctvre': 0.786},
    'numExon': 3,
    'svType': 'DUP',
    'transcripts': {
        'ENSG00000275023': [{'geneId': 'ENSG00000275023', 'majorConsequence': 'LOF'}],
    },
}
GCNV_VARIANT4 = {
    'key': 19,
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
    'xpos': 17038721781,
    'genotypes': {
        'I000004_hg00731': {
            'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'cn': 3, 'qs': 28, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False, 'filters': [],
        },
        'I000005_hg00732': {
            'sampleId': 'HG00732', 'sampleType': 'WES', 'individualGuid': 'I000005_hg00732', 'familyGuid': 'F000002_2',
            'numAlt': 0, 'cn': None, 'qs': None, 'defragged': None, 'start': None, 'end': None, 'numExon': None,
            'geneIds': None, 'newCall': None, 'prevCall': None, 'prevOverlap': None, 'filters': [],
        },
        'I000006_hg00733': {
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733', 'familyGuid': 'F000002_2',
            'numAlt': 1, 'cn': 3, 'qs': 29, 'defragged': False, 'start': None, 'end': 38734440, 'numExon': None,
            'geneIds': None, 'newCall': False, 'prevCall': True, 'prevOverlap': False, 'filters': [],
        }
    },
    'populations': {'sv_callset': {'af': 0.00498959, 'ac': 115, 'an': 23048, 'hom': 0, 'het': 0}},
    'predictions': {'strvctvre': 0.71},
    'numExon': 7,
    'svType': 'DEL',
    'transcripts': {
        'ENSG00000275023': [{'geneId': 'ENSG00000275023', 'majorConsequence': 'LOF'}],
        'ENSG00000277258': [{'geneId': 'ENSG00000277258', 'majorConsequence': 'LOF'}],
        'ENSG00000277972': [{'geneId': 'ENSG00000277972', 'majorConsequence': 'COPY_GAIN'}],
    },
}

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
PROJECT_2_VARIANT2 = deepcopy(VARIANT2)
PROJECT_2_VARIANT2['familyGuids'] = ['F000011_11']
PROJECT_2_VARIANT2['genotypes'] = {
    'I000015_na20885': {
        'sampleId': 'NA20885', 'sampleType': 'WGS', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
        'numAlt': 1, 'dp': 28, 'gq': 99, 'ab': 0.5, 'filters': [],
    },
}
MULTI_PROJECT_VARIANT1 = deepcopy(VARIANT1)
MULTI_PROJECT_VARIANT1['familyGuids'] += PROJECT_2_VARIANT1['familyGuids']
MULTI_PROJECT_VARIANT1['genotypes'].update(deepcopy(PROJECT_2_VARIANT1['genotypes']))
MULTI_PROJECT_VARIANT2 = deepcopy(VARIANT2)
MULTI_PROJECT_VARIANT2['familyGuids'] += PROJECT_2_VARIANT2['familyGuids']
MULTI_PROJECT_VARIANT2['genotypes'].update(deepcopy(PROJECT_2_VARIANT2['genotypes']))

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
VARIANT4_BOTH_SAMPLE_TYPES['genotypes']['I000006_hg00733'][1]['gq'] = 0
VARIANT4_BOTH_SAMPLE_TYPES['genotypes']['I000005_hg00732'][1]['gq'] = 0
VARIANT4_BOTH_SAMPLE_TYPES['genotypes']['I000004_hg00731'][1]['ab'] = 0.17241

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
            'numAlt': 2, 'cn': 3, 'qs': 51, 'defragged': False, 'start': None, 'end': None, 'numExon': None,
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
SV_LOOKUP_VARIANT = {
    **SV_VARIANT4,
    'familyGenotypes': {
        SV_VARIANT4['familyGuids'][0]: [{k: v for k, v in g.items() if k != 'individualGuid'} for g in SV_VARIANT4['genotypes'].values()],
    },
}
GCNV_LOOKUP_VARIANT = {
    **GCNV_VARIANT4,
    'familyGenotypes': {
        GCNV_VARIANT4['familyGuids'][0]: [{k: v for k, v in g.items() if k != 'individualGuid'} for g in GCNV_VARIANT4['genotypes'].values()],
        'F000002_2_x': [
            {**{k: v for k, v in g.items() if k != 'individualGuid'}, 'familyGuid': 'F000002_2_x'}
            for individual_guid, g in GCNV_VARIANT4['genotypes'].items() if individual_guid != 'I000005_hg00732'
        ],
    },
}
GCNV_LOOKUP_VARIANT_3 = {
    **MULTI_PROJECT_GCNV_VARIANT3,
    'familyGenotypes': {
        **{family_guid: [
            {k: v for k, v in g.items() if k != 'individualGuid'} for g in MULTI_PROJECT_GCNV_VARIANT3['genotypes'].values()
            if g['familyGuid'] == family_guid] for family_guid in MULTI_PROJECT_GCNV_VARIANT3['familyGuids']
        },
        'F000002_2_x': [
            {**{k: v for k, v in g.items() if k != 'individualGuid'}, 'familyGuid': 'F000002_2_x'}
            for individual_guid, g in GCNV_VARIANT3['genotypes'].items() if individual_guid != 'I000005_hg00732'
        ],
    },
}
for k in {'familyGuids', 'genotypes'}:
    VARIANT_LOOKUP_VARIANT.pop(k)
    SV_LOOKUP_VARIANT.pop(k)
    GCNV_LOOKUP_VARIANT.pop(k)
    GCNV_LOOKUP_VARIANT_3.pop(k)

PROJECT_4_COMP_HET_VARIANT = {
    'key': 22,
    'variantId': '1-9310123-T-C',
    'chrom': '1',
    'pos': 9310123,
    'ref': 'T',
    'alt': 'C',
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '1',
    'liftedOverPos': 9310113,
    'xpos': 1009310123,
    'rsid': None,
    'familyGuids': ['F000014_14'],
    'genotypes': {
        'I000018_na21234': {
            'sampleId': 'NA21234', 'sampleType': 'WGS', 'individualGuid': 'I000018_na21234', 'familyGuid': 'F000014_14',
            'numAlt': 2, 'dp': 45, 'gq': 0, 'ab': 0, 'filters': [],
        },
        'I000019_na21987': {
            'sampleId': 'NA21987', 'sampleType': 'WGS', 'individualGuid': 'I000019_na21987', 'familyGuid': 'F000014_14',
            'numAlt': 1, 'dp': 29, 'gq': 58, 'ab': 0.17241, 'filters': [],
        },
        'I000021_na21654': {
            'sampleId': 'NA21654', 'sampleType': 'WGS', 'individualGuid': 'I000021_na21654', 'familyGuid': 'F000014_14',
            'numAlt': 0, 'dp': 24, 'gq': 0, 'ab': 0, 'filters': [],
        }
    },
    'clinvar': None,
    'hgmd': None,
    'screenRegionType': None,
    'populations': {
        'seqr': {'ac': 3, 'hom': 1, 'ac_wes': 0, 'hom_wes': 0, 'ac_wgs': 3, 'hom_wgs': 1},
        'topmed': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'het': 0},
        'exac': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'het': 0, 'filter_af': 0.0},
        'gnomad_exomes': {'af': 0.00004, 'ac': 4, 'an': 90386, 'hom': 0, 'hemi': 0, 'filter_af': 0.0001},
        'gnomad_genomes': {'af': 0.00004, 'ac': 13, 'an': 264690, 'hom': 13, 'hemi': 0, 'filter_af': 0.0002},
    },
    'predictions': {
        'cadd': 1.92299,
        'eigen': 2.24799,
        'fathmm': None,
        'gnomad_noncoding': None,
        'mpc': None,
        'mut_pred': None,
        'primate_ai': None,
        'splice_ai': 0.01,
        'splice_ai_consequence': 'No consequence',
        'vest': None,
        'mut_taster': None,
        'polyphen': None,
        'revel': None,
        'sift': None,
    },
    'transcripts': {'ENSG00000171621': [{
        'alphamissense': {'pathogenicity': None}, 'aminoAcids': 'T/I', 'canonical': 1, 'codons': 'aCc/aTc',
        'geneId': 'ENSG00000171621', 'hgvsc': 'ENST00000257261.10:c.131C>T', 'hgvsp': 'ENSP00000257261.6:p.Thr44Ile',
        'transcriptId': 'ENST00000257261', 'loftee': {'isLofNagnag': None, 'lofFilters': None}, 'transcriptRank': 0,
        'consequenceTerms': ['missense_variant'], 'biotype': 'protein_coding', 'majorConsequence': 'missense_variant',
        'exon': {'index': 1, 'total': 12}, 'intron': None, 'manePlusClinical': None, 'maneSelect': None,
        'refseqTranscriptId': 'NM_001281501.1', 'spliceregion': {'extended_intronic_splice_region_variant': False},
        'utrannotator': {'existingInframeOorfs': None, 'existingOutofframeOorfs': None, 'existingUorfs': None, 'fiveutrAnnotation': None, 'fiveutrConsequence': None},
    }]},
    'mainTranscriptId': 'ENST00000257261',
    'selectedMainTranscriptId': None,
    'sortedMotifFeatureConsequences': None,
    'sortedRegulatoryFeatureConsequences': None,
    'CAID': None,
}

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
    'alphamissensePathogenicity': 0.1,
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
22: [{
    'alphamissensePathogenicity': None,
    'canonical': 1,
    'consequenceTerms': ['missense_variant'],
    'extendedIntronicSpliceRegionVariant': False,
    'fiveutrConsequence': None,
    'geneId': 'ENSG00000171621',
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
    'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2, 'F000011_11': 1}},
    'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1, 'F000011_11': 1}},
}
MITO_GENE_COUNTS = {
    'ENSG00000210112': {'total': 1, 'families': {'F000002_2': 1}},
    'ENSG00000198886': {'total': 1, 'families': {'F000002_2': 1}},
    'ENSG00000198727': {'total': 1, 'families': {'F000002_2': 1}},
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
    'ENSG00000171621': {'total': 2, 'families': {'F000014_14': 2}},
    'ENSG00000083544': {'total': 1, 'families': {'F000014_14': 1}},
    'ENSG00000184986': {'total': 1, 'families': {'F000014_14': 1}},
    'null': {'total': 1, 'families': {'F000014_14': 1}},
}

GCNV_GENE_COUNTS = {
    'ENSG00000103495': {'total': 1, 'families': {'F000002_2': 1}},
    'ENSG00000167371': {'total': 1, 'families': {'F000002_2': 1}},
    'ENSG00000280893': {'total': 1, 'families': {'F000002_2': 1}},
    'ENSG00000275023': {'total': 2, 'families': {'F000002_2': 2}},
    'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
    'ENSG00000277972': {'total': 1, 'families': {'F000002_2': 1}},
}
