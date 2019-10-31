from copy import deepcopy
import mock
import json
from collections import defaultdict
from django.test import TestCase

from seqr.models import Family, Sample, VariantSearch, VariantSearchResults
from seqr.utils.es_utils import get_es_variants_for_variant_tuples, get_single_es_variant, get_es_variants, \
    get_es_variant_gene_counts, _genotype_inheritance_filter

INDEX_NAME = 'test_index'
SECOND_INDEX_NAME = 'test_index_second'

ES_VARIANTS = [
    {
        '_source': {
          'gnomad_exomes_Hemi': None,
          'originalAltAlleles': [
            '1-248367227-TC-T'
          ],
          'hgmd_accession': None,
          'g1k_AF': None,
          'gnomad_genomes_Hom': 0,
          'cadd_PHRED': 25.9,
          'exac_AC_Hemi': None,
          'g1k_AC': None,
          'topmed_AN': 125568,
          'g1k_AN': None,
          'topmed_AF': 0.00016724,
          'dbnsfp_MutationTaster_pred': None,
          'ref': 'TC',
          'exac_AC_Hom': 0,
          'topmed_AC': 21,
          'dbnsfp_REVEL_score': None,
          'primate_ai_score': None,
          'variantId': '1-248367227-TC-T',
          'sortedTranscriptConsequences': [
            {
              'amino_acids': 'LL/L',
              'biotype': 'nonsense_mediated_decay',
              'lof': None,
              'lof_flags': None,
              'major_consequence_rank': 10,
              'codons': 'ctTCTc/ctc',
              'gene_symbol': 'MFSD9',
              'domains': [
                'Transmembrane_helices:TMhelix',
                'Gene3D:1',
              ],
              'canonical': None,
              'transcript_rank': 1,
              'cdna_end': 143,
              'lof_filter': None,
              'hgvs': 'ENSP00000413641.1:p.Leu48del',
              'hgvsc': 'ENST00000428085.1:c.141_143delTCT',
              'cdna_start': 141,
              'transcript_id': 'ENST00000428085',
              'protein_id': 'ENSP00000413641',
              'category': 'missense',
              'gene_id': 'ENSG00000135953',
              'hgvsp': 'ENSP00000413641.1:p.Leu48del',
              'major_consequence': 'frameshift_variant',
              'consequence_terms': [
                'frameshift_variant',
                'inframe_deletion',
                'NMD_transcript_variant'
              ]
            },
            {
              'amino_acids': 'P/X',
              'biotype': 'protein_coding',
              'lof': None,
              'lof_flags': None,
              'major_consequence_rank': 4,
              'codons': 'Ccc/cc',
              'gene_symbol': 'OR2M3',
              'domains': [
                  'Transmembrane_helices:TMhelix',
                  'Prints_domain:PR00237',
              ],
              'canonical': 1,
              'transcript_rank': 0,
              'cdna_end': 897,
              'lof_filter': None,
              'hgvs': 'ENSP00000389625.1:p.Leu288SerfsTer10',
              'hgvsc': 'ENST00000456743.1:c.862delC',
              'cdna_start': 897,
              'transcript_id': 'ENST00000456743',
              'protein_id': 'ENSP00000389625',
              'category': 'lof',
              'gene_id': 'ENSG00000228198',
              'hgvsp': 'ENSP00000389625.1:p.Leu288SerfsTer10',
              'major_consequence': 'frameshift_variant',
              'consequence_terms': [
                  'frameshift_variant'
              ]
            }
          ],
          'hgmd_class': None,
          'AC': 2,
          'exac_AN_Adj': 121308,
          'mpc_MPC': None,
          'AF': 0.063,
          'alt': 'T',
          'clinvar_clinical_significance': None,
          'rsid': None,
          'dbnsfp_DANN_score': None,
          'AN': 32,
          'gnomad_genomes_AF_POPMAX_OR_GLOBAL': 0.0004590314436538903,
          'exac_AF': 0.00006589,
          'dbnsfp_GERP_RS': None,
          'dbnsfp_SIFT_pred': None,
          'exac_AC_Adj': 8,
          'g1k_POPMAX_AF': None,
          'topmed_Hom': 0,
          'gnomad_genomes_AN': 30946,
          'dbnsfp_MetaSVM_pred': None,
          'dbnsfp_Polyphen2_HVAR_pred': None,
          'clinvar_allele_id': None,
          'gnomad_exomes_Hom': 0,
          'gnomad_exomes_AF_POPMAX_OR_GLOBAL': 0.0009151523074911753,
          'gnomad_genomes_Hemi': None,
          'xpos': 1248367227,
          'start': 248367227,
          'filters': [],
          'dbnsfp_phastCons100way_vertebrate': None,
          'gnomad_exomes_AN': 245930,
          'contig': '1',
          'clinvar_gold_stars': None,
          'eigen_Eigen_phred': None,
          'exac_AF_POPMAX': 0.0006726888333653661,
          'gnomad_exomes_AC': 16,
          'dbnsfp_FATHMM_pred': None,
          'gnomad_exomes_AF': 0.00006505916317651364,
          'gnomad_genomes_AF': 0.00012925741614425127,
          'gnomad_genomes_AC': 4,
          'genotypes': [
            {
              'num_alt': 2,
              'ab': 1,
              'dp': 74,
              'gq': 99,
              'sample_id': 'NA20870',
            },
            {
              'num_alt': 0,
              'ab': 0,
              'dp': 88,
              'gq': 99,
              'sample_id': 'HG00731',
            },
            {
                'num_alt': 1,
                'ab': 0.631,
                'dp': 50,
                'gq': 99,
                'sample_id': 'NA20885',
            },
          ],
          'samples_num_alt_1': ['NA20885'],
          'samples_num_alt_2': ['NA20870'],
        },
        'matched_queries': {INDEX_NAME: ['F000003_3'], SECOND_INDEX_NAME: ['F000011_11']},
      },
    {
        '_source': {
          'gnomad_exomes_Hemi': None,
          'originalAltAlleles': [
            '2-103343353-GAGA-G'
          ],
          'hgmd_accession': None,
          'g1k_AF': None,
          'gnomad_genomes_Hom': None,
          'cadd_PHRED': 17.26,
          'exac_AC_Hemi': None,
          'g1k_AC': None,
          'topmed_AN': None,
          'g1k_AN': None,
          'topmed_AF': None,
          'dbnsfp_MutationTaster_pred': None,
          'ref': 'GAGA',
          'exac_AC_Hom': 0,
          'topmed_AC': None,
          'dbnsfp_REVEL_score': None,
          'primate_ai_score': None,
          'variantId': '2-103343353-GAGA-G',
          'sortedTranscriptConsequences': [
              {
                  'amino_acids': 'LL/L',
                  'biotype': 'protein_coding',
                  'lof': None,
                  'lof_flags': None,
                  'major_consequence_rank': 10,
                  'codons': 'ctTCTc/ctc',
                  'gene_symbol': 'MFSD9',
                  'domains': [
                      'Transmembrane_helices:TMhelix',
                      'PROSITE_profiles:PS50850',
                  ],
                  'canonical': 1,
                  'transcript_rank': 0,
                  'cdna_end': 421,
                  'lof_filter': None,
                  'hgvs': 'ENSP00000258436.5:p.Leu126del',
                  'hgvsc': 'ENST00000258436.5:c.375_377delTCT',
                  'cdna_start': 419,
                  'transcript_id': 'ENST00000258436',
                  'protein_id': 'ENSP00000258436',
                  'category': 'missense',
                  'gene_id': 'ENSG00000135953',
                  'hgvsp': 'ENSP00000258436.5:p.Leu126del',
                  'major_consequence': 'inframe_deletion',
                  'consequence_terms': [
                      'inframe_deletion'
                  ]
              },
              {
                  'amino_acids': 'P/X',
                  'biotype': 'protein_coding',
                  'lof': None,
                  'lof_flags': None,
                  'major_consequence_rank': 4,
                  'codons': 'Ccc/cc',
                  'gene_symbol': 'OR2M3',
                  'domains': [
                      'Transmembrane_helices:TMhelix',
                      'Prints_domain:PR00237',
                  ],
                  'canonical': 1,
                  'transcript_rank': 0,
                  'cdna_end': 897,
                  'lof_filter': None,
                  'hgvs': 'ENSP00000389625.1:p.Leu288SerfsTer10',
                  'hgvsc': 'ENST00000456743.1:c.862delC',
                  'cdna_start': 897,
                  'transcript_id': 'ENST00000456743',
                  'protein_id': 'ENSP00000389625',
                  'category': 'lof',
                  'gene_id': 'ENSG00000228198',
                  'hgvsp': 'ENSP00000389625.1:p.Leu288SerfsTer10',
                  'major_consequence': 'frameshift_variant',
                  'consequence_terms': [
                      'frameshift_variant'
                  ]
              }
          ],
          'hgmd_class': None,
          'AC': 1,
          'exac_AN_Adj': 121336,
          'mpc_MPC': None,
          'AF': 0.031,
          'alt': 'G',
          'clinvar_clinical_significance': None,
          'rsid': None,
          'dbnsfp_DANN_score': None,
          'AN': 32,
          'gnomad_genomes_AF_POPMAX_OR_GLOBAL': None,
          'exac_AF': 0.00004942,
          'dbnsfp_GERP_RS': None,
          'dbnsfp_SIFT_pred': None,
          'exac_AC_Adj': 6,
          'g1k_POPMAX_AF': None,
          'topmed_Hom': None,
          'gnomad_genomes_AN': None,
          'dbnsfp_MetaSVM_pred': None,
          'dbnsfp_Polyphen2_HVAR_pred': None,
          'clinvar_allele_id': None,
          'gnomad_exomes_Hom': 0,
          'gnomad_exomes_AF_POPMAX_OR_GLOBAL': 0.00016269686320447742,
          'gnomad_genomes_Hemi': None,
          'xpos': 2103343353,
          'start': 103343353,
          'filters': [],
          'dbnsfp_phastCons100way_vertebrate': None,
          'gnomad_exomes_AN': 245714,
          'contig': '2',
          'clinvar_gold_stars': None,
          'eigen_Eigen_phred': None,
          'exac_AF_POPMAX': 0.000242306760358614,
          'gnomad_exomes_AC': 6,
          'dbnsfp_FATHMM_pred': None,
          'gnomad_exomes_AF': 0.000024418633044922146,
          'gnomad_genomes_AF': None,
          'gnomad_genomes_AC': None,
          'genotypes': [
            {
                'num_alt': 1,
                'ab': 0.70212764,
                'dp': 50,
                'gq': 46,
                'sample_id': 'NA20870',
            },
            {
                'num_alt': 1,
                'ab': 0.631,
                'dp': 50,
                'gq': 99,
                'sample_id': 'NA20885',
            },
            {
                'num_alt': 0,
                'ab': 0,
                'dp': 67,
                'gq': 99,
                'sample_id': 'HG00731',
            },
            {
                'num_alt': 2,
                'ab': 0,
                'dp': 42,
                'gq': 96,
                'sample_id': 'HG00732',
            },
            {
                'num_alt': 1,
                'ab': 0,
                'dp': 42,
                'gq': 96,
                'sample_id': 'HG00733',
            }
          ],
          'samples_num_alt_1': ['NA20870', 'HG00733', 'NA20885'],
          'samples_num_alt_2': ['HG00732'],
        },
        'matched_queries': {INDEX_NAME: ['F000003_3', 'F000002_2'], SECOND_INDEX_NAME: ['F000011_11']},
      },
]
BUILD_38_ES_VARIANT = deepcopy(ES_VARIANTS[1])
BUILD_38_ES_VARIANT['_source'].update({
    'start': 103343363,
    'xpos': 2103343363,
    'variantId': '2-103343363-GAGA-G'
})

OR2M3_COMPOUND_HET_ES_VARIANTS = deepcopy(ES_VARIANTS)
transcripts = OR2M3_COMPOUND_HET_ES_VARIANTS[1]['_source']['sortedTranscriptConsequences']
transcripts[0]['major_consequence'] = 'frameshift_variant'
OR2M3_COMPOUND_HET_ES_VARIANTS[1]['_source']['sortedTranscriptConsequences'] = [transcripts[1], transcripts[0]]
MFSD9_COMPOUND_HET_ES_VARIANTS = deepcopy(OR2M3_COMPOUND_HET_ES_VARIANTS)
for var in MFSD9_COMPOUND_HET_ES_VARIANTS:
    var['_source']['variantId'] = '{}-het'.format(var['_source']['variantId'])
EXTRA_FAMILY_ES_VARIANTS = deepcopy(ES_VARIANTS) + [deepcopy(ES_VARIANTS[0])]
EXTRA_FAMILY_ES_VARIANTS[2]['matched_queries'][INDEX_NAME] = ['F000005_5']
MISSING_SAMPLE_ES_VARIANTS = deepcopy(ES_VARIANTS)
MISSING_SAMPLE_ES_VARIANTS[1]['_source']['samples_num_alt_1'] = []
COMPOUND_HET_INDEX_VARIANTS = {
    INDEX_NAME: {'ENSG00000135953': EXTRA_FAMILY_ES_VARIANTS, 'ENSG00000228198': EXTRA_FAMILY_ES_VARIANTS},
    SECOND_INDEX_NAME: {
        'ENSG00000135953': MFSD9_COMPOUND_HET_ES_VARIANTS, 'ENSG00000228198': OR2M3_COMPOUND_HET_ES_VARIANTS,
    },
    '{},{}'.format(SECOND_INDEX_NAME, INDEX_NAME): {'ENSG00000135953': MISSING_SAMPLE_ES_VARIANTS},
}

INDEX_ES_VARIANTS = {INDEX_NAME: ES_VARIANTS, SECOND_INDEX_NAME: [BUILD_38_ES_VARIANT]}

TRANSCRIPT_1 = {
  'aminoAcids': 'LL/L',
  'biotype': 'protein_coding',
  'lof': None,
  'lofFlags': None,
  'majorConsequenceRank': 10,
  'codons': 'ctTCTc/ctc',
  'geneSymbol': 'MFSD9',
  'domains': [
    'Transmembrane_helices:TMhelix',
    'PROSITE_profiles:PS50850',
  ],
  'canonical': 1,
  'transcriptRank': 0,
  'cdnaEnd': 421,
  'lofFilter': None,
  'hgvs': 'ENSP00000258436.5:p.Leu126del',
  'hgvsc': 'ENST00000258436.5:c.375_377delTCT',
  'cdnaStart': 419,
  'transcriptId': 'ENST00000258436',
  'proteinId': 'ENSP00000258436',
  'category': 'missense',
  'geneId': 'ENSG00000135953',
  'hgvsp': 'ENSP00000258436.5:p.Leu126del',
  'majorConsequence': 'inframe_deletion',
  'consequenceTerms': [
    'inframe_deletion'
  ]
}
TRANSCRIPT_2 = {
  'aminoAcids': 'P/X',
  'biotype': 'protein_coding',
  'lof': None,
  'lofFlags': None,
  'majorConsequenceRank': 4,
  'codons': 'Ccc/cc',
  'geneSymbol': 'OR2M3',
  'domains': [
    'Transmembrane_helices:TMhelix',
    'Prints_domain:PR00237',
  ],
  'canonical': 1,
  'transcriptRank': 0,
  'cdnaEnd': 897,
  'lofFilter': None,
  'hgvs': 'ENSP00000389625.1:p.Leu288SerfsTer10',
  'hgvsc': 'ENST00000456743.1:c.862delC',
  'cdnaStart': 897,
  'transcriptId': 'ENST00000456743',
  'proteinId': 'ENSP00000389625',
  'category': 'lof',
  'geneId': 'ENSG00000228198',
  'hgvsp': 'ENSP00000389625.1:p.Leu288SerfsTer10',
  'majorConsequence': 'frameshift_variant',
  'consequenceTerms': [
    'frameshift_variant'
  ]
}
TRANSCRIPT_3 = {
  'aminoAcids': 'LL/L',
  'biotype': 'nonsense_mediated_decay',
  'lof': None,
  'lofFlags': None,
  'majorConsequenceRank': 10,
  'codons': 'ctTCTc/ctc',
  'geneSymbol': 'MFSD9',
  'domains': [
    'Transmembrane_helices:TMhelix',
    'Gene3D:1',
  ],
  'canonical': None,
  'transcriptRank': 1,
  'cdnaEnd': 143,
  'lofFilter': None,
  'hgvs': 'ENSP00000413641.1:p.Leu48del',
  'hgvsc': 'ENST00000428085.1:c.141_143delTCT',
  'cdnaStart': 141,
  'transcriptId': 'ENST00000428085',
  'proteinId': 'ENSP00000413641',
  'category': 'missense',
  'geneId': 'ENSG00000135953',
  'hgvsp': 'ENSP00000413641.1:p.Leu48del',
  'majorConsequence': 'frameshift_variant',
  'consequenceTerms': [
    'frameshift_variant',
    'inframe_deletion',
    'NMD_transcript_variant'
  ]
}

PARSED_VARIANTS = [
    {
        'alt': 'T',
        'chrom': '1',
        'clinvar': {'clinicalSignificance': None, 'alleleId': None, 'variationId': None, 'goldStars': None},
        'familyGuids': ['F000003_3'],
        'genotypes': {
            'I000007_na20870': {'ab': 1, 'ad': None, 'gq': 99, 'sampleId': 'NA20870', 'numAlt': 2, 'dp': 74, 'pl': None}
        },
        'genomeVersion': '37',
        'genotypeFilters': '',
        'hgmd': {'accession': None, 'class': None},
        'liftedOverChrom': None,
        'liftedOverGenomeVersion': None,
        'liftedOverPos': None,
        'mainTranscriptId': TRANSCRIPT_3['transcriptId'],
        'originalAltAlleles': ['T'],
        'populations': {
            'callset': {'an': 32, 'ac': 2, 'hom': None, 'af': 0.063, 'hemi': None},
            'g1k': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0},
            'gnomad_genomes': {'an': 30946, 'ac': 4, 'hom': 0, 'af': 0.0004590314436538903, 'hemi': 0},
            'exac': {'an': 121308, 'ac': 8, 'hom': 0, 'af': 0.0006726888333653661, 'hemi': 0},
            'gnomad_exomes': {'an': 245930, 'ac': 16, 'hom': 0, 'af': 0.0009151523074911753, 'hemi': 0},
            'topmed': {'an': 125568, 'ac': 21, 'hom': 0, 'af': 0.00016724, 'hemi': 0}
        },
        'pos': 248367227,
        'predictions': {'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None,
                        'polyphen': None, 'dann': None, 'sift': None, 'cadd': 25.9, 'metasvm': None, 'primate_ai': None,
                        'gerp_rs': None, 'mpc': None, 'phastcons_100_vert': None},
        'ref': 'TC',
        'rsid': None,
        'transcripts': {
            'ENSG00000135953': [TRANSCRIPT_3],
            'ENSG00000228198': [TRANSCRIPT_2],
        },
        'variantId': '1-248367227-TC-T',
        'xpos': 1248367227,
        '_sort': [1248367227],
    },
    {
        'alt': 'G',
        'chrom': '2',
        'clinvar': {'clinicalSignificance': None, 'alleleId': None, 'variationId': None, 'goldStars': None},
        'familyGuids': ['F000002_2', 'F000003_3'],
        'genotypes': {
            'I000004_hg00731': {'ab': 0, 'ad': None, 'gq': 99, 'sampleId': 'HG00731', 'numAlt': 0, 'dp': 67, 'pl': None},
            'I000005_hg00732': {'ab': 0, 'ad': None, 'gq': 96, 'sampleId': 'HG00732', 'numAlt': 2, 'dp': 42, 'pl': None},
            'I000006_hg00733': {'ab': 0, 'ad': None, 'gq': 96, 'sampleId': 'HG00733', 'numAlt': 1, 'dp': 42, 'pl': None},
            'I000007_na20870': {'ab': 0.70212764, 'ad': None, 'gq': 46, 'sampleId': 'NA20870', 'numAlt': 1, 'dp': 50, 'pl': None}
        },
        'genotypeFilters': '',
        'genomeVersion': '37',
        'hgmd': {'accession': None, 'class': None},
        'liftedOverGenomeVersion': None,
        'liftedOverChrom': None,
        'liftedOverPos': None,
        'mainTranscriptId': TRANSCRIPT_1['transcriptId'],
        'originalAltAlleles': ['G'],
        'populations': {
            'callset': {'an': 32, 'ac': 1, 'hom': None, 'af': 0.031, 'hemi': None},
            'g1k': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0},
            'gnomad_genomes': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0},
            'exac': {'an': 121336, 'ac': 6, 'hom': 0, 'af': 0.000242306760358614, 'hemi': 0},
            'gnomad_exomes': {'an': 245714, 'ac': 6, 'hom': 0, 'af': 0.00016269686320447742, 'hemi': 0},
            'topmed': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0}
        },
        'pos': 103343353,
        'predictions': {
            'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None, 'polyphen': None,
            'dann': None, 'sift': None, 'cadd': 17.26, 'metasvm': None, 'primate_ai': None, 'gerp_rs': None,
            'mpc': None, 'phastcons_100_vert': None
        },
        'ref': 'GAGA',
        'rsid': None,
        'transcripts': {
            'ENSG00000135953': [TRANSCRIPT_1],
            'ENSG00000228198': [TRANSCRIPT_2],
        },
        'variantId': '2-103343353-GAGA-G',
        'xpos': 2103343353,
        '_sort': [2103343353],
    },
]
PARSED_COMPOUND_HET_VARIANTS = deepcopy(PARSED_VARIANTS)
PARSED_COMPOUND_HET_VARIANTS[0]['_sort'] = [1248367327]
PARSED_COMPOUND_HET_VARIANTS[1]['_sort'] = [2103343453]
PARSED_COMPOUND_HET_VARIANTS[1]['familyGuids'] = ['F000003_3']

PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT = deepcopy(PARSED_COMPOUND_HET_VARIANTS)
for variant in PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT:
    variant['familyGuids'].append('F000011_11')
    variant['genotypes'].update({
        'I000015_na20885': {'ab': 0.631, 'ad': None, 'gq': 99, 'sampleId': 'NA20885', 'numAlt': 1, 'dp': 50, 'pl': None},
    })
PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT[1]['transcripts']['ENSG00000135953'][0]['majorConsequence'] = 'frameshift_variant'
PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT[1]['mainTranscriptId'] = TRANSCRIPT_2['transcriptId']

PARSED_COMPOUND_HET_VARIANTS_PROJECT_2 = deepcopy(PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT)
for variant in PARSED_COMPOUND_HET_VARIANTS_PROJECT_2:
    variant.update({
        'variantId': '{}-het'.format(variant['variantId']),
        'familyGuids': ['F000011_11'],
        'genotypes': {
            'I000015_na20885': {'ab': 0.631, 'ad': None, 'gq': 99, 'sampleId': 'NA20885', 'numAlt': 1, 'dp': 50, 'pl': None},
        },
        'genomeVersion': '38',
        'liftedOverGenomeVersion': '37',
        'liftedOverPos': variant['pos'] - 10,
        'liftedOverChrom': variant['chrom'],
    })

PARSED_COMPOUND_HET_VARIANTS_MULTI_GENOME_VERSION = deepcopy(PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT)
for variant in PARSED_COMPOUND_HET_VARIANTS_MULTI_GENOME_VERSION:
    variant.update({
        'genomeVersion': '38',
        'liftedOverGenomeVersion': '37',
        'liftedOverPos': variant['pos'] - 10,
        'liftedOverChrom': variant['chrom'],
    })

PARSED_NO_SORT_VARIANTS = deepcopy(PARSED_VARIANTS)
for var in PARSED_NO_SORT_VARIANTS:
    del var['_sort']

PARSED_MULTI_INDEX_VARIANT = deepcopy(PARSED_VARIANTS[1])
PARSED_MULTI_INDEX_VARIANT.update({
    'familyGuids': ['F000002_2', 'F000003_3', 'F000011_11'],
    'genotypes': {
        'I000004_hg00731': {'ab': 0, 'ad': None, 'gq': 99, 'sampleId': 'HG00731', 'numAlt': 0, 'dp': 67, 'pl': None},
        'I000005_hg00732': {'ab': 0, 'ad': None, 'gq': 96, 'sampleId': 'HG00732', 'numAlt': 2, 'dp': 42, 'pl': None},
        'I000006_hg00733': {'ab': 0, 'ad': None, 'gq': 96, 'sampleId': 'HG00733', 'numAlt': 1, 'dp': 42, 'pl': None},
        'I000007_na20870': {'ab': 0.70212764, 'ad': None, 'gq': 46, 'sampleId': 'NA20870', 'numAlt': 1, 'dp': 50, 'pl': None},
        'I000015_na20885': {'ab': 0.631, 'ad': None, 'gq': 99, 'sampleId': 'NA20885', 'numAlt': 1, 'dp': 50, 'pl': None},
    },
})

PARSED_MULTI_GENOME_VERSION_VARIANT = deepcopy(PARSED_MULTI_INDEX_VARIANT)
PARSED_MULTI_GENOME_VERSION_VARIANT.update({
    'genomeVersion': '38',
    'liftedOverGenomeVersion': '37',
    'liftedOverPos': PARSED_MULTI_INDEX_VARIANT['pos'],
    'liftedOverChrom': PARSED_MULTI_INDEX_VARIANT['chrom'],
    'pos': PARSED_MULTI_INDEX_VARIANT['pos'] + 10,
    'xpos': PARSED_MULTI_INDEX_VARIANT['xpos'] + 10,
    'variantId': PARSED_MULTI_INDEX_VARIANT['variantId'].replace(
        str(PARSED_MULTI_INDEX_VARIANT['pos']), str(PARSED_MULTI_INDEX_VARIANT['pos'] + 10)
    ),
    '_sort': [PARSED_MULTI_INDEX_VARIANT['_sort'][0] + 10],
})

MAPPING_FIELDS = [
    'start',
    'rsid',
    'originalAltAlleles',
    'filters',
    'xpos',
    'alt',
    'ref',
    'contig',
    'variantId',
    'dbnsfp_MutationTaster_pred',
    'dbnsfp_phastCons100way_vertebrate',
    'dbnsfp_MetaSVM_pred',
    'mpc_MPC',
    'dbnsfp_DANN_score',
    'eigen_Eigen_phred',
    'dbnsfp_REVEL_score',
    'dbnsfp_GERP_RS',
    'splice_ai_delta_score',
    'dbnsfp_FATHMM_pred',
    'primate_ai_score',
    'dbnsfp_SIFT_pred',
    'dbnsfp_Polyphen2_HVAR_pred',
    'cadd_PHRED',
    'sortedTranscriptConsequences',
    'genotypes',
    'samples_num_alt_1',
    'samples_num_alt_2',
    'clinvar_clinical_significance',
    'clinvar_allele_id',
    'clinvar_variation_id',
    'clinvar_gold_stars',
    'hgmd_accession',
    'hgmd_class',
    'AC',
    'AF',
    'callset_AF',
    'callset_AF_POPMAX_OR_GLOBAL',
    'AN',
    'callset_AN',
    'g1k_AC',
    'g1k_Hom',
    'g1k_Hemi',
    'g1k_POPMAX_AF',
    'g1k_AF',
    'g1k_AF_POPMAX_OR_GLOBAL',
    'g1k_AN',
    'gnomad_genomes_AC',
    'gnomad_genomes_Hom',
    'gnomad_genomes_Hemi',
    'gnomad_genomes_AF',
    'gnomad_genomes_AF_POPMAX_OR_GLOBAL',
    'gnomad_genomes_AN',
    'gnomad_exomes_AC',
    'gnomad_exomes_Hom',
    'gnomad_exomes_Hemi',
    'gnomad_exomes_AF',
    'gnomad_exomes_AF_POPMAX_OR_GLOBAL',
    'gnomad_exomes_AN',
    'exac_AC_Adj',
    'exac_AC',
    'exac_AC_Hom',
    'exac_Hom',
    'exac_AC_Hemi',
    'exac_Hemi',
    'exac_AF_POPMAX',
    'exac_AF',
    'exac_AF_POPMAX_OR_GLOBAL',
    'exac_AN_Adj',
    'exac_AN',
    'topmed_AC',
    'topmed_Hom',
    'topmed_Hemi',
    'topmed_AF',
    'topmed_AF_POPMAX_OR_GLOBAL',
    'topmed_AN',
    'callset_AC',
]
SOURCE_FIELDS = {'callset_Hom', 'callset_Hemi'}
SOURCE_FIELDS.update(MAPPING_FIELDS)

INDEX_METADATA = {
    INDEX_NAME: {'genomeVersion': '37', 'fields': MAPPING_FIELDS},
    SECOND_INDEX_NAME: {'genomeVersion': '38', 'fields': MAPPING_FIELDS},
}

ALL_INHERITANCE_QUERY = {
    'bool': {
        'should': [
            {'bool': {
                'must': [
                    {'bool': {'should': [
                        {'terms': {'samples_num_alt_1': ['HG00731', 'HG00732', 'HG00733']}},
                        {'terms': {'samples_num_alt_2': ['HG00731', 'HG00732', 'HG00733']}}
                    ]}}
                ],
                '_name': 'F000002_2'
            }},
            {'bool': {
                'must': [
                    {'bool': {'should': [
                        {'terms': {'samples_num_alt_1': ['NA20870']}},
                        {'terms': {'samples_num_alt_2': ['NA20870']}}
                    ]}}
                ],
                '_name': 'F000003_3'
            }},
            {'bool': {
                'must': [
                    {'bool': {'should': [
                        {'terms': {'samples_num_alt_1': ['NA20874']}},
                        {'terms': {'samples_num_alt_2': ['NA20874']}},
                    ]}}
                ],
                '_name': 'F000005_5'
            }}
        ]
    }
}

COMPOUND_HET_INHERITANCE_QUERY = {
    'bool': {
        'should': [
            {'bool': {
                '_name': 'F000002_2',
                'must': [
                    {'bool': {
                        'must_not': [
                            {'term': {'samples_no_call': 'HG00732'}},
                            {'term': {'samples_num_alt_2': 'HG00732'}},
                            {'term': {'samples_no_call': 'HG00733'}},
                            {'term': {'samples_num_alt_2': 'HG00733'}}
                        ],
                        'must': [{'term': {'samples_num_alt_1': 'HG00731'}}]
                    }},
                    {'bool': {'must_not': [
                        {'term': {'samples_gq_0_to_5': 'HG00731'}},
                        {'term': {'samples_gq_5_to_10': 'HG00731'}},
                        {'term': {'samples_gq_0_to_5': 'HG00732'}},
                        {'term': {'samples_gq_5_to_10': 'HG00732'}},
                        {'term': {'samples_gq_0_to_5': 'HG00733'}},
                        {'term': {'samples_gq_5_to_10': 'HG00733'}},
                    ]}},
                ]
            }},
            {'bool': {
                '_name': 'F000003_3',
                'must': [
                    {'term': {'samples_num_alt_1': 'NA20870'}},
                    {'bool': {'must_not': [
                        {'term': {'samples_gq_0_to_5': 'NA20870'}},
                        {'term': {'samples_gq_5_to_10': 'NA20870'}}
                    ]}}
                ]
            }},
        ]
    }
}

RECESSIVE_INHERITANCE_QUERY = {
    'bool': {
        'should': [
            {'bool': {
                '_name': 'F000002_2',
                'must': [
                    {'bool': {
                        'should': [
                            {'bool': {
                                'must_not': [
                                    {'term': {'samples_no_call': 'HG00732'}},
                                    {'term': {'samples_num_alt_2': 'HG00732'}},
                                    {'term': {'samples_no_call': 'HG00733'}},
                                    {'term': {'samples_num_alt_2': 'HG00733'}}
                                ],
                                'must': [{'term': {'samples_num_alt_2': 'HG00731'}}]
                            }},
                            {'bool': {
                                'must_not': [
                                    {'term': {'samples_no_call': 'HG00732'}},
                                    {'term': {'samples_num_alt_1': 'HG00732'}},
                                    {'term': {'samples_num_alt_2': 'HG00732'}},
                                    {'term': {'samples_no_call': 'HG00733'}},
                                    {'term': {'samples_num_alt_2': 'HG00733'}}
                                ],
                                'must': [{'match': {'contig': 'X'}}, {'term': {'samples_num_alt_2': 'HG00731'}}]
                            }}
                        ]
                    }},
                    {'bool': {'must_not': [
                        {'term': {'samples_gq_0_to_5': 'HG00731'}},
                        {'term': {'samples_gq_5_to_10': 'HG00731'}},
                        {'term': {'samples_gq_0_to_5': 'HG00732'}},
                        {'term': {'samples_gq_5_to_10': 'HG00732'}},
                        {'term': {'samples_gq_0_to_5': 'HG00733'}},
                        {'term': {'samples_gq_5_to_10': 'HG00733'}},
                    ]}},
                ]
            }},
            {'bool': {
                '_name': 'F000003_3',
                'must': [
                    {'bool': {
                        'should': [
                            {'bool': {'must': [
                                {'match': {'contig': 'X'}},
                                {'term': {'samples_num_alt_2': 'NA20870'}}
                            ]}},
                            {'term': {'samples_num_alt_2': 'NA20870'}},
                        ]
                    }},
                    {'bool': {'must_not': [
                        {'term': {'samples_gq_0_to_5': 'NA20870'}},
                        {'term': {'samples_gq_5_to_10': 'NA20870'}}
                    ]}}
                ]
            }},
        ]
    }
}

REDIS_CACHE = {}
def _set_cache(k, v):
    REDIS_CACHE[k] = v
MOCK_REDIS = mock.MagicMock()
MOCK_REDIS.get.side_effect = REDIS_CACHE.get
MOCK_REDIS.set.side_effect =_set_cache

MOCK_LIFTOVER = mock.MagicMock()
MOCK_LIFTOVER.convert_coordinate.side_effect = lambda chrom, pos: [[chrom, pos - 10]]


class MockHit:

    def __init__(self, matched_queries=None, _source=None, increment_sort=False, no_matched_queries=False, sort=None, index=INDEX_NAME):
        self.meta = mock.MagicMock()
        if no_matched_queries:
            del self.meta.matched_queries
        else:
            self.meta.matched_queries = []
            for subindex in index.split(','):
                self.meta.matched_queries += matched_queries[subindex]
        self.meta.index = index
        self.meta.id = _source['variantId']
        if sort or increment_sort:
            sort = _source['xpos']
            if increment_sort:
                sort += 100
            self.meta.sort = [sort]
        else:
            del self.meta.sort
        self._dict = _source
        mock_transcripts = []
        for transcript in self._dict['sortedTranscriptConsequences']:
            mock_transcript = mock.MagicMock()
            mock_transcript.to_dict.return_value = transcript
            mock_transcripts.append(mock_transcript)
        self._dict['sortedTranscriptConsequences'] = mock_transcripts

    def __getitem__(self, key):
        return self._dict[key]

    def __iter__(self):
        return self._dict.__iter__()


def create_mock_response(search, index=INDEX_NAME):
    indices = index.split(',')
    no_matched_queries = True
    for search_filter in search['query']['bool']['filter']:
        possible_inheritance_filters = search_filter.get('bool', {}).get('should', [])
        if any('_name' in possible_filter.get('bool', {}) for possible_filter in possible_inheritance_filters):
            no_matched_queries = False
            break

    mock_response = mock.MagicMock()
    mock_response.hits.total = 5
    hits = []
    for index_name in sorted(indices):
        hits += [
            MockHit(no_matched_queries=no_matched_queries, sort=search.get('sort'), index=index_name, **var)
            for var in deepcopy(INDEX_ES_VARIANTS[index_name])
        ]
    mock_response.__iter__.return_value = hits
    mock_response.hits.__getitem__.side_effect = hits.__getitem__

    if search.get('aggs'):
        index_vars = COMPOUND_HET_INDEX_VARIANTS.get(index, {})
        mock_response.aggregations.genes.buckets = [{'key': gene_id, 'doc_count': 3}
                                                    for gene_id in ['ENSG00000135953', 'ENSG00000228198']]
        if search['aggs']['genes']['aggs'].get('vars_by_gene'):
            for bucket in mock_response.aggregations.genes.buckets:
                bucket['vars_by_gene'] = [MockHit(increment_sort=True, index=index, **var)
                                          for var in deepcopy(index_vars.get(bucket['key'], ES_VARIANTS))]
        else:
            for bucket in mock_response.aggregations.genes.buckets:
                for sample_field in ['samples_num_alt_1', 'samples_num_alt_2']:
                    gene_samples = defaultdict(int)
                    for var in index_vars.get(bucket['key'], ES_VARIANTS):
                        for sample in var['_source'][sample_field]:
                            gene_samples[sample] += 1
                    bucket[sample_field] = {'buckets': [{'key': k, 'doc_count': v} for k, v in gene_samples.items()]}
    else:
        del mock_response.aggregations.genes
    return mock_response


@mock.patch('seqr.utils.es_utils.redis.StrictRedis', lambda **kwargs: MOCK_REDIS)
@mock.patch('seqr.utils.es_utils.get_index_metadata', lambda index_name, client: {k: INDEX_METADATA[k] for k in index_name.split(',')})
@mock.patch('seqr.utils.es_utils._liftover_grch38_to_grch37', lambda: MOCK_LIFTOVER)
class EsUtilsTest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data']

    def setUp(self):
        Sample.objects.filter(sample_id='NA19678').update(is_active=False)
        self.families = Family.objects.filter(guid__in=['F000003_3', 'F000002_2', 'F000005_5'])
        self.executed_search = None
        self.searched_indices = []

        def mock_execute_search(search):
            self.executed_search = deepcopy(search.to_dict())
            self.searched_indices += search._index

            if isinstance(self.executed_search, list):
                return [create_mock_response(search, index=self.executed_search[i-1]['index'][0])
                        for i, search in enumerate(self.executed_search) if search.get('query')]
            else:
                return create_mock_response(self.executed_search, index=self.searched_indices[0])

        patcher = mock.patch('seqr.utils.es_utils.BaseEsSearch._execute_search')
        patcher.start().side_effect = mock_execute_search
        self.addCleanup(patcher.stop)

    def assertExecutedSearch(self, filters=None, start_index=0, size=2, sort=None, gene_aggs=False, gene_count_aggs=None, index=INDEX_NAME):
        self.assertIsInstance(self.executed_search, dict)
        self.assertEqual(self.searched_indices, [index])
        self.assertSameSearch(
            self.executed_search, dict(filters=filters, start_index=start_index, size=size, sort=sort, gene_aggs=gene_aggs, gene_count_aggs=gene_count_aggs)
        )
        self.executed_search = None
        self.searched_indices = []

    def assertExecutedSearches(self, searches):
        self.assertIsInstance(self.executed_search, list)
        self.assertEqual(len(self.executed_search), len(searches)*2)
        for i, expected_search in enumerate(searches):
            self.assertDictEqual(self.executed_search[i*2], {'index': [expected_search.get('index', INDEX_NAME)]})
            self.assertSameSearch(self.executed_search[(i*2)+1], expected_search)
        self.executed_search = None
        self.searched_indices = []

    def assertSameSearch(self, executed_search, expected_search_params):
        expected_search = {
            'query': {
                'bool': {
                    'filter': expected_search_params['filters']
                }
            },
            'from': expected_search_params['start_index'],
            'size': expected_search_params['size']
        }

        if expected_search_params.get('sort'):
            expected_search['sort'] = expected_search_params['sort']

        if expected_search_params.get('gene_aggs'):
            expected_search['aggs'] = {
                'genes': {'terms': {'field': 'geneIds', 'min_doc_count': 2, 'size': 1001}, 'aggs': {
                    'vars_by_gene': {
                        'top_hits': {'sort': expected_search_params['sort'], '_source': mock.ANY, 'size': 100}
                    }
                }}}
        elif expected_search_params.get('gene_count_aggs'):
            expected_search['aggs'] = {'genes': {
                'terms': {'field': 'mainTranscript_gene_id', 'size': 1001},
                'aggs': expected_search_params['gene_count_aggs']
            }}
        else:
            expected_search['_source'] = mock.ANY

        self.assertDictEqual(executed_search, expected_search)

        if not expected_search_params.get('gene_count_aggs'):
            source = executed_search['aggs']['genes']['aggs']['vars_by_gene']['top_hits']['_source'] \
                if expected_search_params.get('gene_aggs')  else executed_search['_source']
            self.assertSetEqual(SOURCE_FIELDS, set(source))

    def assertCachedResults(self, results_model, expected_results, sort='xpos'):
        self.assertDictEqual(json.loads(REDIS_CACHE.get('search_results__{}__{}'.format(results_model.guid, sort))), expected_results)

    def test_get_es_variants_for_variant_tuples(self):
        variants = get_es_variants_for_variant_tuples(
            self.families,
            [(2103343353, 'GAGA', 'G'), (1248367227, 'TC', 'T')]
        )

        self.assertEqual(len(variants), 2)
        self.assertDictEqual(variants[0], PARSED_NO_SORT_VARIANTS[0])
        self.assertDictEqual(variants[1], PARSED_NO_SORT_VARIANTS[1])

        self.assertExecutedSearch(
            filters=[{'terms': {'variantId': ['2-103343353-GAGA-G', '1-248367227-TC-T']}}],
        )

    def test_get_single_es_variant(self):
        variant = get_single_es_variant(self.families, '2-103343353-GAGA-G')
        self.assertDictEqual(variant, PARSED_NO_SORT_VARIANTS[0])
        self.assertExecutedSearch(
            filters=[{'term': {'variantId': '2-103343353-GAGA-G'}}], size=1
        )

        variant = get_single_es_variant(self.families, '2-103343353-GAGA-G', return_all_queried_families=True)
        all_family_variant = deepcopy(PARSED_NO_SORT_VARIANTS[0])
        all_family_variant['familyGuids'] = ['F000002_2', 'F000003_3', 'F000005_5']
        all_family_variant['genotypes']['I000004_hg00731'] = {'ab': 0, 'ad': None, 'gq': 99, 'sampleId': 'HG00731', 'numAlt': 0, 'dp': 88, 'pl': None}
        self.assertDictEqual(variant, all_family_variant)
        self.assertExecutedSearch(
            filters=[{'term': {'variantId': '2-103343353-GAGA-G'}}], size=1
        )

    def test_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, total_results = get_es_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertDictEqual(variants[0], PARSED_VARIANTS[0])
        self.assertDictEqual(variants[1], PARSED_VARIANTS[1])
        self.assertEqual(total_results, 5)

        self.assertCachedResults(results_model, {'all_results': variants, 'total_results': 5})

        self.assertExecutedSearch(filters=[ALL_INHERITANCE_QUERY], sort=['xpos'])

        # does not save non-consecutive pages
        variants, total_results = get_es_variants(results_model, page=3, num_results=2)
        self.assertEqual(total_results, 5)
        self.assertCachedResults(results_model, {'all_results': variants, 'total_results': 5})
        self.assertExecutedSearch(filters=[ALL_INHERITANCE_QUERY], sort=['xpos'], start_index=4, size=2)

        # test pagination
        variants, total_results = get_es_variants(results_model, page=2, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertEqual(total_results, 5)
        self.assertCachedResults(results_model, {'all_results': PARSED_VARIANTS + PARSED_VARIANTS, 'total_results': 5})
        self.assertExecutedSearch(filters=[ALL_INHERITANCE_QUERY], sort=['xpos'], start_index=2, size=2)

        # test does not re-fetch page
        variants, total_results = get_es_variants(results_model, page=1, num_results=3)
        self.assertIsNone(self.executed_search)
        self.assertEqual(len(variants), 3)
        self.assertListEqual(variants, PARSED_VARIANTS + PARSED_VARIANTS[:1])
        self.assertEqual(total_results, 5)

        # test load_all
        variants, _ = get_es_variants(results_model, page=1, num_results=2, load_all=True)
        self.assertExecutedSearch(filters=[ALL_INHERITANCE_QUERY], sort=['xpos'], start_index=4, size=1)
        self.assertEqual(len(variants), 5)
        self.assertListEqual(variants, PARSED_VARIANTS + PARSED_VARIANTS + PARSED_VARIANTS[:1])

    def test_filtered_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'locus': {'rawItems': 'DDX11L1, chr2:1234-5678', 'rawVariantItems': 'rs9876,chr2-1234-A-C'},
            'pathogenicity': {
                'clinvar': ['pathogenic', 'likely_pathogenic'],
                'hgmd': ['disease_causing', 'likely_disease_causing'],
            },
            'annotations': {
                'in_frame': ['inframe_insertion', 'inframe_deletion'],
                'other': ['5_prime_UTR_variant', 'intergenic_variant'],
            },
            'freqs': {
                'callset': {'af': 0.1},
                'exac': {'ac': 2},
                'g1k': {'ac': None, 'af': 0.001},
                'gnomad_exomes': {'ac': 3, 'hh': 3},
                'gnomad_genomes': {'af': 0.01, 'hh': 3},
                'topmed': {'ac': 2, 'af': None},
            },
            'qualityFilter': {'min_ab': 10, 'min_gq': 15, 'vcf_filter': 'pass'},
            'inheritance': {'mode': 'de_novo'}
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, total_results = get_es_variants(results_model, sort='protein_consequence', num_results=2)
        self.assertListEqual(variants, PARSED_VARIANTS)
        self.assertEqual(total_results, 5)

        self.assertExecutedSearch(filters=[
            {
                'bool': {
                    'should': [
                        {'range': {'xpos': {'gte': 2000001234, 'lte': 2000005678}}},
                        {'terms': {'geneIds': ['ENSG00000223972']}},
                        {'terms': {'rsid': ['rs9876']}},
                        {'terms': {'variantId': ['2-1234-A-C']}},
                    ]
                }
            },
            {
                'bool': {
                    'should': [
                        {'bool': {'must_not': [{'exists': {'field': 'transcriptConsequenceTerms'}}]}},
                        {'terms': {
                            'transcriptConsequenceTerms': [
                                '5_prime_UTR_variant',
                                'intergenic_variant',
                                'inframe_insertion',
                                'inframe_deletion',
                            ]
                        }},
                        {'terms': {
                            'clinvar_clinical_significance': [
                                'Pathogenic', 'Likely_pathogenic', 'Pathogenic/Likely_pathogenic'
                            ]
                        }},
                        {'terms': {'hgmd_class': ['DM', 'DM?']}},
                    ]
                }
            },
            {
                'bool': {
                    'minimum_should_match': 1,
                    'should': [
                        {'bool': {'must_not': [{'exists': {'field': 'AF'}}]}},
                        {'range': {'AF': {'lte': 0.1}}}
                    ],
                    'must': [
                        {'bool': {
                            'minimum_should_match': 1,
                            'should': [
                                {'bool': {'must_not': [{'exists': {'field': 'g1k_POPMAX_AF'}}]}},
                                {'range': {'g1k_POPMAX_AF': {'lte': 0.001}}}
                            ]
                        }},
                        {'bool': {
                            'minimum_should_match': 1,
                            'should': [
                                {'bool': {'must_not': [{'exists': {'field': 'gnomad_genomes_AF_POPMAX_OR_GLOBAL'}}]}},
                                {'range': {'gnomad_genomes_AF_POPMAX_OR_GLOBAL': {'lte': 0.01}}}
                            ]
                        }},
                        {'bool': {
                            'minimum_should_match': 1,
                            'should': [
                                {'bool': {'must_not': [{'exists': {'field': 'gnomad_genomes_Hom'}}]}},
                                {'range': {'gnomad_genomes_Hom': {'lte': 3}}}
                            ]
                        }},
                        {'bool': {
                            'minimum_should_match': 1,
                            'should': [
                                {'bool': {'must_not': [{'exists': {'field': 'gnomad_genomes_Hemi'}}]}},
                                {'range': {'gnomad_genomes_Hemi': {'lte': 3}}}
                            ]}
                        },
                        {'bool': {
                            'minimum_should_match': 1,
                            'should': [
                                {'bool': {'must_not': [{'exists': {'field': 'gnomad_exomes_AC'}}]}},
                                {'range': {'gnomad_exomes_AC': {'lte': 3}}}
                            ]
                        }},
                        {'bool': {
                            'minimum_should_match': 1,
                            'should': [
                                {'bool': {'must_not': [{'exists': {'field': 'gnomad_exomes_Hom'}}]}},
                                {'range': {'gnomad_exomes_Hom': {'lte': 3}}}
                            ]
                        }},
                        {'bool': {
                            'minimum_should_match': 1,
                            'should': [
                                {'bool': {'must_not': [{'exists': {'field': 'gnomad_exomes_Hemi'}}]}},
                                {'range': {'gnomad_exomes_Hemi': {'lte': 3}}}
                            ]}
                        },
                        {'bool': {
                            'minimum_should_match': 1,
                            'should': [
                                {'bool': {'must_not': [{'exists': {'field': 'exac_AC_Adj'}}]}},
                                {'range': {'exac_AC_Adj': {'lte': 2}}}
                            ]}
                        },
                        {'bool': {
                            'minimum_should_match': 1,
                            'should': [
                                {'bool': {'must_not': [{'exists': {'field': 'topmed_AC'}}]}},
                                {'range': {'topmed_AC': {'lte': 2}}}
                            ]}
                        }
                    ]
                }
            },
            {'bool': {'must_not': [{'exists': {'field': 'filters'}}]}},
            {'bool': {
                'should': [
                    {'bool': {
                        'must': [
                            {'bool': {
                                'minimum_should_match': 1,
                                'must_not': [
                                    {'term': {'samples_no_call': 'HG00732'}},
                                    {'term': {'samples_num_alt_1': 'HG00732'}},
                                    {'term': {'samples_num_alt_2': 'HG00732'}},
                                    {'term': {'samples_no_call': 'HG00733'}},
                                    {'term': {'samples_num_alt_1': 'HG00733'}},
                                    {'term': {'samples_num_alt_2': 'HG00733'}}
                                ],
                                'should': [
                                    {'term': {'samples_num_alt_1': 'HG00731'}},
                                    {'term': {'samples_num_alt_2': 'HG00731'}}
                                ]
                            }},
                            {'bool': {
                                'minimum_should_match': 1,
                                'should': [
                                    {'bool': {
                                        'must_not': [
                                            {'term': {'samples_ab_0_to_5': 'HG00731'}},
                                            {'term': {'samples_ab_5_to_10': 'HG00731'}},
                                        ]
                                    }},
                                    {'bool': {'must_not': [{'term': {'samples_num_alt_1': 'HG00731'}}]}}
                                ],
                                'must_not': [
                                    {'term': {'samples_gq_0_to_5': 'HG00731'}},
                                    {'term': {'samples_gq_5_to_10': 'HG00731'}},
                                    {'term': {'samples_gq_10_to_15': 'HG00731'}},
                                    {'term': {'samples_gq_0_to_5': 'HG00732'}},
                                    {'term': {'samples_gq_5_to_10': 'HG00732'}},
                                    {'term': {'samples_gq_10_to_15': 'HG00732'}},
                                    {'term': {'samples_gq_0_to_5': 'HG00733'}},
                                    {'term': {'samples_gq_5_to_10': 'HG00733'}},
                                    {'term': {'samples_gq_10_to_15': 'HG00733'}},
                                ],
                                'must': [
                                    {'bool': {
                                        'minimum_should_match': 1,
                                        'should': [
                                            {'bool': {
                                                'must_not': [
                                                    {'term': {'samples_ab_0_to_5': 'HG00732'}},
                                                    {'term': {'samples_ab_5_to_10': 'HG00732'}},
                                                ]
                                            }},
                                            {'bool': {'must_not': [{'term': {'samples_num_alt_1': 'HG00732'}}]}}
                                        ]
                                    }},
                                    {'bool': {
                                        'minimum_should_match': 1,
                                        'should': [
                                            {'bool': {
                                                'must_not': [
                                                    {'term': {'samples_ab_0_to_5': 'HG00733'}},
                                                    {'term': {'samples_ab_5_to_10': 'HG00733'}},
                                                ]
                                            }},
                                            {'bool': {'must_not': [{'term': {'samples_num_alt_1': 'HG00733'}}]}}
                                        ]
                                    }},
                                ]
                            }}
                        ],
                        '_name': 'F000002_2'
                    }},
                    {'bool': {
                        'must': [
                            {'bool': {'should': [
                                {'term': {'samples_num_alt_1': 'NA20870'}},
                                {'term': {'samples_num_alt_2': 'NA20870'}}
                            ]}},
                            {'bool': {
                                'minimum_should_match': 1,
                                'should': [
                                    {'bool': {
                                        'must_not': [
                                            {'term': {'samples_ab_0_to_5': 'NA20870'}},
                                            {'term': {'samples_ab_5_to_10': 'NA20870'}},
                                        ]
                                    }},
                                    {'bool': {'must_not': [{'term': {'samples_num_alt_1': 'NA20870'}}]}}
                                ],
                                'must_not': [
                                    {'term': {'samples_gq_0_to_5': 'NA20870'}},
                                    {'term': {'samples_gq_5_to_10': 'NA20870'}},
                                    {'term': {'samples_gq_10_to_15': 'NA20870'}},
                                ]
                            }}
                        ],
                        '_name': 'F000003_3'
                    }},
                ]
            }}
        ], sort=['mainTranscript_major_consequence_rank', 'xpos'])

    def test_compound_het_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'qualityFilter': {'min_gq': 10},
            'annotations': {'other': []},
            'inheritance': {'mode': 'compound_het'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, total_results = get_es_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertListEqual(variants, PARSED_COMPOUND_HET_VARIANTS)
        self.assertEqual(total_results, 2)

        self.assertCachedResults(results_model, {
            'grouped_results': [{'ENSG00000135953': PARSED_COMPOUND_HET_VARIANTS}],
            'total_results': 2,
        })

        self.assertExecutedSearch(
            filters=[COMPOUND_HET_INHERITANCE_QUERY],
            gene_aggs=True,
            sort=['xpos'],
            start_index=0,
            size=1
        )

        # test pagination does not fetch
        get_es_variants(results_model, page=2, num_results=2)
        self.assertIsNone(self.executed_search)

    def test_recessive_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'qualityFilter': {'min_gq': 10, 'vcf_filter': 'pass'},
            'inheritance': {'mode': 'recessive'}
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, total_results = get_es_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 3)
        self.assertDictEqual(variants[0], PARSED_VARIANTS[0])
        self.assertDictEqual(variants[1], PARSED_COMPOUND_HET_VARIANTS[0])
        self.assertDictEqual(variants[2], PARSED_COMPOUND_HET_VARIANTS[1])
        self.assertEqual(total_results, 7)

        self.assertCachedResults(results_model, {
            'compound_het_results': [],
            'variant_results': [PARSED_VARIANTS[1]],
            'grouped_results': [{'null': [PARSED_VARIANTS[0]]}, {'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS}],
            'duplicate_doc_count': 0,
            'loaded_variant_counts': {'test_index_compound_het': {'total': 2, 'loaded': 2}, INDEX_NAME: {'loaded': 2, 'total': 5}},
            'total_results': 7,
        })

        annotation_query = {'terms': {'transcriptConsequenceTerms': ['frameshift_variant']}}
        pass_filter_query = {'bool': {'must_not': [{'exists': {'field': 'filters'}}]}}

        self.assertExecutedSearches([
            dict(filters=[annotation_query, pass_filter_query, RECESSIVE_INHERITANCE_QUERY], start_index=0, size=2, sort=['xpos']),
            dict(
                filters=[annotation_query, pass_filter_query, COMPOUND_HET_INHERITANCE_QUERY],
                gene_aggs=True,
                sort=['xpos'],
                start_index=0,
                size=1
            )
        ])

        # test pagination

        variants, total_results = get_es_variants(results_model, page=3, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertListEqual(variants, PARSED_VARIANTS)
        self.assertEqual(total_results, 6)

        self.assertCachedResults(results_model, {
            'compound_het_results': [],
            'variant_results': [],
            'grouped_results': [
                {'null': [PARSED_VARIANTS[0]]}, {'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS},
                {'null': [PARSED_VARIANTS[0]]}, {'null': [PARSED_VARIANTS[1]]}],
            'duplicate_doc_count': 1,
            'loaded_variant_counts': {'test_index_compound_het': {'total': 2, 'loaded': 2}, INDEX_NAME: {'loaded': 4, 'total': 5}},
            'total_results': 6,
        })

        self.assertExecutedSearches([dict(filters=[annotation_query, pass_filter_query, RECESSIVE_INHERITANCE_QUERY], start_index=2, size=4, sort=['xpos'])])

        get_es_variants(results_model, page=2, num_results=2)
        self.assertIsNone(self.executed_search)

    def test_all_samples_all_inheritance_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={'annotations': {'frameshift': ['frameshift_variant']}})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(project__guid='R0001_1kg'))

        variants, total_results = get_es_variants(results_model, num_results=2)
        self.assertListEqual(variants, PARSED_VARIANTS)
        self.assertEqual(total_results, 5)

        self.assertExecutedSearch(filters=[{'terms': {'transcriptConsequenceTerms': ['frameshift_variant']}}], sort=['xpos'])

    def test_multi_project_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'qualityFilter': {'min_gq': 10},
            'inheritance': {'mode': 'recessive'}
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(guid__in=['F000011_11', 'F000003_3', 'F000002_2']))

        variants, total_results = get_es_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 3)
        self.assertDictEqual(variants[0], PARSED_VARIANTS[0])
        self.assertDictEqual(variants[1], PARSED_COMPOUND_HET_VARIANTS_PROJECT_2[0])
        self.assertDictEqual(variants[2], PARSED_COMPOUND_HET_VARIANTS_PROJECT_2[1])
        self.assertEqual(total_results, 13)

        self.assertCachedResults(results_model, {
            'compound_het_results': [{'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS_MULTI_GENOME_VERSION}],
            'variant_results': [PARSED_MULTI_GENOME_VERSION_VARIANT],
            'grouped_results': [{'null': [PARSED_VARIANTS[0]]}, {'ENSG00000135953': PARSED_COMPOUND_HET_VARIANTS_PROJECT_2}],
            'duplicate_doc_count': 3,
            'loaded_variant_counts': {
                SECOND_INDEX_NAME: {'loaded': 1, 'total': 5},
                '{}_compound_het'.format(SECOND_INDEX_NAME): {'total': 4, 'loaded': 4},
                INDEX_NAME: {'loaded': 2, 'total': 5},
                '{}_compound_het'.format(INDEX_NAME): {'total': 2, 'loaded': 2},
            },
            'total_results': 13,
        })

        annotation_query = {'terms': {'transcriptConsequenceTerms': ['frameshift_variant']}}

        project_2_search = dict(
            filters=[
                annotation_query,
                {'bool': {
                    'must': [
                        {'bool': {'should': [
                            {'bool': {'must': [
                                {'match': {'contig': 'X'}},
                                {'term': {'samples_num_alt_2': 'NA20885'}}
                            ]}},
                            {'term': {'samples_num_alt_2': 'NA20885'}},
                        ]}},
                        {'bool': {
                            'must_not': [
                                {'term': {'samples_gq_0_to_5': 'NA20885'}},
                                {'term': {'samples_gq_5_to_10': 'NA20885'}},
                            ]
                        }}
                    ],
                    '_name': 'F000011_11'
                }}
            ], start_index=0, size=2, sort=['xpos'], index=SECOND_INDEX_NAME)
        project_1_search = dict(
            filters=[
                annotation_query,
                RECESSIVE_INHERITANCE_QUERY,
            ], start_index=0, size=2, sort=['xpos'], index=INDEX_NAME)
        self.assertExecutedSearches([
            project_2_search,
            dict(
                filters=[
                    annotation_query,
                    {'bool': {
                        '_name': 'F000011_11',
                        'must': [
                            {'term': {'samples_num_alt_1': 'NA20885'}},
                            {'bool': {'must_not': [
                                {'term': {'samples_gq_0_to_5': 'NA20885'}},
                                {'term': {'samples_gq_5_to_10': 'NA20885'}}
                            ]}}
                        ]
                    }}
                ],
                gene_aggs=True, sort=['xpos'], start_index=0, size=1, index=SECOND_INDEX_NAME,
            ),
            project_1_search,
            dict(
                filters=[annotation_query, COMPOUND_HET_INHERITANCE_QUERY],
                gene_aggs=True, sort=['xpos'], start_index=0, size=1, index=INDEX_NAME,
            )
        ])

        # test pagination
        variants, total_results = get_es_variants(results_model, num_results=2, page=2)
        self.assertEqual(len(variants), 3)
        self.assertListEqual(variants, [PARSED_VARIANTS[0]] + PARSED_COMPOUND_HET_VARIANTS_MULTI_GENOME_VERSION)
        self.assertEqual(total_results, 11)

        self.assertCachedResults(results_model, {
            'compound_het_results': [],
            'variant_results': [PARSED_MULTI_GENOME_VERSION_VARIANT],
            'grouped_results': [
                {'null': [PARSED_VARIANTS[0]]},
                {'ENSG00000135953': PARSED_COMPOUND_HET_VARIANTS_PROJECT_2},
                {'null': [PARSED_VARIANTS[0]]},
                {'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS_MULTI_GENOME_VERSION}
            ],
            'duplicate_doc_count': 5,
            'loaded_variant_counts': {
                SECOND_INDEX_NAME: {'loaded': 2, 'total': 5},
                '{}_compound_het'.format(SECOND_INDEX_NAME): {'total': 4, 'loaded': 4},
                INDEX_NAME: {'loaded': 4, 'total': 5},
                '{}_compound_het'.format(INDEX_NAME): {'total': 2, 'loaded': 2},
            },
            'total_results': 11,
        })

        project_2_search['start_index'] = 1
        project_2_search['size'] = 3
        project_1_search['start_index'] = 2
        self.assertExecutedSearches([project_2_search, project_1_search])

    def test_multi_project_all_samples_all_inheritance_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={'annotations': {'frameshift': ['frameshift_variant']}})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.all())

        variants, total_results = get_es_variants(results_model, num_results=2)
        expected_variants = [PARSED_VARIANTS[0], PARSED_MULTI_GENOME_VERSION_VARIANT]
        self.assertListEqual(variants, expected_variants)
        self.assertEqual(total_results, 4)

        self.assertCachedResults(results_model, {
            'all_results': expected_variants,
            'duplicate_doc_count': 1,
            'total_results': 4,
        })

        self.assertExecutedSearch(
            index='{},{}'.format(SECOND_INDEX_NAME, INDEX_NAME),
            filters=[{'terms': {'transcriptConsequenceTerms': ['frameshift_variant']}}],
            sort=['xpos'],
            size=4,
        )

        # test pagination
        variants, total_results = get_es_variants(results_model, num_results=2, page=2)
        expected_variants = [PARSED_VARIANTS[0], PARSED_MULTI_GENOME_VERSION_VARIANT]
        self.assertListEqual(variants, expected_variants)
        self.assertEqual(total_results, 3)

        self.assertCachedResults(results_model, {
            'all_results': expected_variants + expected_variants,
            'duplicate_doc_count': 2,
            'total_results': 3,
        })

        self.assertExecutedSearch(
            index='{},{}'.format(SECOND_INDEX_NAME, INDEX_NAME),
            filters=[{'terms': {'transcriptConsequenceTerms': ['frameshift_variant']}}],
            sort=['xpos'],
            size=5,
            start_index=3,
        )

    def test_multi_project_get_variants_by_id(self):
        search_model = VariantSearch.objects.create(search={
            'locus': {'rawVariantItems': '2-103343363-GAGA-G', 'genomeVersion': '38'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.all())

        variants, total_results = get_es_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 1)
        self.assertDictEqual(variants[0], PARSED_MULTI_GENOME_VERSION_VARIANT)

        self.assertCachedResults(results_model, {
            'all_results': [PARSED_MULTI_GENOME_VERSION_VARIANT],
            'duplicate_doc_count': 2,
            'total_results': 3,
        })

        self.assertExecutedSearch(
            index='{},{}'.format(SECOND_INDEX_NAME, INDEX_NAME),
            filters=[{'terms': {'variantId': ['2-103343363-GAGA-G', '2-103343353-GAGA-G']}}],
            sort=['xpos'],
            size=4,
        )

    def test_get_es_variant_gene_counts(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'qualityFilter': {'min_gq': 10},
            'inheritance': {'mode': 'recessive'}
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(guid__in=['F000003_3', 'F000002_2', 'F000005_5']))

        initial_cached_results = {
            'compound_het_results': [],
            'variant_results': [PARSED_VARIANTS[1]],
            'grouped_results': [{'null': [PARSED_VARIANTS[0]]}, {'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS}],
            'duplicate_doc_count': 0,
            'loaded_variant_counts': {'test_index_compound_het': {'total': 2, 'loaded': 2}, INDEX_NAME: {'loaded': 2, 'total': 5}},
            'total_results': 7,
        }
        _set_cache('search_results__{}__xpos'.format(results_model.guid), json.dumps(initial_cached_results))

        #  Test gene counts
        gene_counts = get_es_variant_gene_counts(results_model)
        self.assertDictEqual(gene_counts, {
            'ENSG00000135953': {'total': 3, 'families': {'F000003_3': 2, 'F000002_2': 1, 'F000005_5': 1}},
            'ENSG00000228198': {'total': 5, 'families': {'F000003_3': 4, 'F000002_2': 1, 'F000005_5': 1}}
        })

        self.assertExecutedSearch(
            filters=[{'terms': {'transcriptConsequenceTerms': ['frameshift_variant']}}, RECESSIVE_INHERITANCE_QUERY],
            size=1, index=INDEX_NAME, gene_count_aggs={'vars_by_gene': {'top_hits': {'_source': 'none', 'size': 100}}})

        expected_cached_results = {'gene_aggs': gene_counts}
        expected_cached_results.update(initial_cached_results)
        self.assertCachedResults(results_model, expected_cached_results)

    def test_multi_project_get_es_variant_gene_counts(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'qualityFilter': {'min_gq': 10},
            'inheritance': {'mode': 'recessive'}
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(guid__in=['F000011_11', 'F000003_3', 'F000002_2', 'F000005_5']))

        initial_cached_results = {
            'compound_het_results': [{'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT}],
            'variant_results': [PARSED_MULTI_INDEX_VARIANT],
            'grouped_results': [{'null': [PARSED_VARIANTS[0]]}, {'ENSG00000135953': PARSED_COMPOUND_HET_VARIANTS_PROJECT_2}],
            'duplicate_doc_count': 3,
            'loaded_variant_counts': {
                SECOND_INDEX_NAME: {'loaded': 1, 'total': 5},
                '{}_compound_het'.format(SECOND_INDEX_NAME): {'total': 4, 'loaded': 4},
                INDEX_NAME: {'loaded': 2, 'total': 5},
                '{}_compound_het'.format(INDEX_NAME): {'total': 2, 'loaded': 2},
            },
            'total_results': 13,
        }
        _set_cache('search_results__{}__xpos'.format(results_model.guid), json.dumps(initial_cached_results))

        #  Test gene counts
        gene_counts = get_es_variant_gene_counts(results_model)
        self.assertDictEqual(gene_counts, {
            'ENSG00000135953': {'total': 6, 'families': {'F000003_3': 2, 'F000002_2': 1, 'F000005_5': 1, 'F000011_11': 4}},
            'ENSG00000228198': {'total': 4, 'families': {'F000003_3': 4, 'F000002_2': 1, 'F000005_5': 1, 'F000011_11': 4}}
        })

        annotation_query = {'terms': {'transcriptConsequenceTerms': ['frameshift_variant']}}
        expected_search = dict(size=1, start_index=0, gene_count_aggs={'vars_by_gene': {'top_hits': {'_source': 'none', 'size': 100}}})
        self.assertExecutedSearches([
            dict(filters=[
                annotation_query,
                {'bool': {
                    'must': [
                        {'bool': {'should': [
                            {'bool': {'must': [
                                {'match': {'contig': 'X'}},
                                {'term': {'samples_num_alt_2': 'NA20885'}}
                            ]}},
                            {'term': {'samples_num_alt_2': 'NA20885'}},
                        ]}},
                        {'bool': {
                            'must_not': [
                                {'term': {'samples_gq_0_to_5': 'NA20885'}},
                                {'term': {'samples_gq_5_to_10': 'NA20885'}},
                            ]
                        }}
                    ],
                    '_name': 'F000011_11'
                }},
            ], index=SECOND_INDEX_NAME, **expected_search),
            dict(filters=[annotation_query, RECESSIVE_INHERITANCE_QUERY], index=INDEX_NAME, **expected_search),
        ])

        expected_cached_results = {'gene_aggs': gene_counts}
        expected_cached_results.update(initial_cached_results)
        self.assertCachedResults(results_model, expected_cached_results)

    def test_multi_project_all_samples_all_inheritance_get_es_variant_gene_counts(self):
        search_model = VariantSearch.objects.create(search={'annotations': {'frameshift': ['frameshift_variant']}})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.all())
        _set_cache('search_results__{}__xpos'.format(results_model.guid), json.dumps({'total_results': 5}))

        gene_counts = get_es_variant_gene_counts(results_model)

        self.assertDictEqual(gene_counts, {
            'ENSG00000135953': {'total': 3, 'families': {'F000003_3': 1, 'F000002_2': 1, 'F000011_11': 1}},
            'ENSG00000228198': {'total': 3, 'families': {'F000003_3': 2, 'F000002_2': 2, 'F000011_11': 2}}
        })

        self.assertExecutedSearch(
            index='{},{}'.format(SECOND_INDEX_NAME, INDEX_NAME),
            filters=[{'terms': {'transcriptConsequenceTerms': ['frameshift_variant']}}],
            size=1,
            gene_count_aggs={
                'samples_num_alt_1': {'terms': {'field': 'samples_num_alt_1', 'size': 10000}},
                'samples_num_alt_2': {'terms': {'field': 'samples_num_alt_2', 'size': 10000}}
            }
        )

        self.assertCachedResults(results_model, {'gene_aggs': gene_counts, 'total_results': 5})

    def test_cached_get_es_variant_gene_counts(self):
        search_model = VariantSearch.objects.create(search={})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        cache_key = 'search_results__{}__xpos'.format(results_model.guid)

        cached_gene_counts = {
            'ENSG00000135953': {'total': 5, 'families': {'F000003_3': 2, 'F000002_2': 1, 'F000011_11': 4}},
            'ENSG00000228198': {'total': 5, 'families': {'F000003_3': 4, 'F000002_2': 1, 'F000011_11': 4}}
        }
        _set_cache(cache_key, json.dumps({'total_results': 5, 'gene_aggs': cached_gene_counts}))
        gene_counts = get_es_variant_gene_counts(results_model)
        self.assertDictEqual(gene_counts, cached_gene_counts)
        self.assertIsNone(self.executed_search)

        _set_cache(cache_key, json.dumps({'all_results': PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT, 'total_results': 2}))
        gene_counts = get_es_variant_gene_counts(results_model)
        self.assertDictEqual(gene_counts, {
            'ENSG00000135953': {'total': 1, 'families': {'F000003_3': 1, 'F000011_11': 1}},
            'ENSG00000228198': {'total': 1, 'families': {'F000003_3': 1, 'F000011_11': 1}}
        })
        self.assertIsNone(self.executed_search)

        _set_cache(cache_key, json.dumps({
            'grouped_results': [
                {'null': [PARSED_VARIANTS[0]]}, {'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT}, {'null': [PARSED_MULTI_INDEX_VARIANT]}
            ],
            'loaded_variant_counts': {
                SECOND_INDEX_NAME: {'loaded': 1, 'total': 1},
                '{}_compound_het'.format(SECOND_INDEX_NAME): {'total': 0, 'loaded': 0},
                INDEX_NAME: {'loaded': 1, 'total': 1},
                '{}_compound_het'.format(INDEX_NAME): {'total': 2, 'loaded': 2},
            },
            'total_results': 4,
        }))
        gene_counts = get_es_variant_gene_counts(results_model)
        self.assertDictEqual(gene_counts, {
            'ENSG00000135953': {'total': 2, 'families': {'F000003_3': 2, 'F000002_2': 1, 'F000011_11': 1}},
            'ENSG00000228198': {'total': 2, 'families': {'F000003_3': 2, 'F000011_11': 2}}
        })
        self.assertIsNone(self.executed_search)

    def test_genotype_inheritance_filter(self):
        samples_by_id = {'F000002_2': {
            sample_id: Sample.objects.get(sample_id=sample_id) for sample_id in ['HG00731', 'HG00732', 'HG00733']
        }}
        custom_affected = {'I000004_hg00731': 'N', 'I000005_hg00732': 'A'}
        custom_multi_affected = {'I000005_hg00732': 'A'}

        # custom genotype
        inheritance_filter = _genotype_inheritance_filter(None, {
            'genotype': {'I000004_hg00731': 'ref_ref', 'I000005_hg00732': 'ref_alt'}
        }, samples_by_id, {})
        self.assertDictEqual(inheritance_filter.to_dict(), {'bool': {'_name': 'F000002_2', 'must': [{
            'bool': {
                'must_not': [
                    {'term': {'samples_no_call': 'HG00731'}},
                    {'term': {'samples_num_alt_1': 'HG00731'}},
                    {'term': {'samples_num_alt_2': 'HG00731'}},
                ],
                'must': [
                    {'term': {'samples_num_alt_1': 'HG00732'}}
                ]
            }
        }]}})

        # de novo
        inheritance_filter = _genotype_inheritance_filter('de_novo', {}, samples_by_id, {})
        self.assertDictEqual(inheritance_filter.to_dict(), {'bool': {'_name': 'F000002_2', 'must': [{
            'bool': {
                'minimum_should_match': 1,
                'must_not': [
                    {'term': {'samples_no_call': 'HG00732'}},
                    {'term': {'samples_num_alt_1': 'HG00732'}},
                    {'term': {'samples_num_alt_2': 'HG00732'}},
                    {'term': {'samples_no_call': 'HG00733'}},
                    {'term': {'samples_num_alt_1': 'HG00733'}},
                    {'term': {'samples_num_alt_2': 'HG00733'}}
                ],
                'should': [
                    {'term': {'samples_num_alt_1': 'HG00731'}},
                    {'term': {'samples_num_alt_2': 'HG00731'}}
                ]
            }
        }]}})
        inheritance_filter = _genotype_inheritance_filter('de_novo', {'affected': custom_affected}, samples_by_id, {})
        self.assertDictEqual(inheritance_filter.to_dict(), {'bool': {'_name': 'F000002_2', 'must': [{
            'bool': {
                'minimum_should_match': 1,
                'must_not': [
                    {'term': {'samples_no_call': 'HG00731'}},
                    {'term': {'samples_num_alt_1': 'HG00731'}},
                    {'term': {'samples_num_alt_2': 'HG00731'}},
                    {'term': {'samples_no_call': 'HG00733'}},
                    {'term': {'samples_num_alt_1': 'HG00733'}},
                    {'term': {'samples_num_alt_2': 'HG00733'}}
                ],
                'should': [
                    {'term': {'samples_num_alt_1': 'HG00732'}},
                    {'term': {'samples_num_alt_2': 'HG00732'}}
                ]
            }
        }]}})
        inheritance_filter = _genotype_inheritance_filter('de_novo', {'affected': custom_multi_affected}, samples_by_id, {})
        self.assertDictEqual(inheritance_filter.to_dict(), {'bool': {'_name': 'F000002_2', 'must': [{
            'bool': {
                'minimum_should_match': 1,
                'must_not': [
                    {'term': {'samples_no_call': 'HG00733'}},
                    {'term': {'samples_num_alt_1': 'HG00733'}},
                    {'term': {'samples_num_alt_2': 'HG00733'}}
                ],
                'should': [
                    {'term': {'samples_num_alt_1': 'HG00731'}},
                    {'term': {'samples_num_alt_2': 'HG00731'}}
                ],
                'must': [{
                    'bool': {
                        'minimum_should_match': 1,
                        'should': [
                            {'term': {'samples_num_alt_1': 'HG00732'}},
                            {'term': {'samples_num_alt_2': 'HG00732'}}
                    ]}
                }]
            }
        }]}})

        recessive_filter = {
            'bool': {
                'must_not': [
                    {'term': {'samples_no_call': 'HG00732'}},
                    {'term': {'samples_num_alt_2': 'HG00732'}},
                    {'term': {'samples_no_call': 'HG00733'}},
                    {'term': {'samples_num_alt_2': 'HG00733'}}
                ],
                'must': [
                    {'term': {'samples_num_alt_2': 'HG00731'}}
                ]
            }
        }
        custom_affected_recessive_filter = {
            'bool': {
                'must_not': [
                    {'term': {'samples_no_call': 'HG00731'}},
                    {'term': {'samples_num_alt_2': 'HG00731'}},
                    {'term': {'samples_no_call': 'HG00733'}},
                    {'term': {'samples_num_alt_2': 'HG00733'}}
                ],
                'must': [
                    {'term': {'samples_num_alt_2': 'HG00732'}}
                ]
            }
        }

        # homozygous recessive
        inheritance_filter = _genotype_inheritance_filter('homozygous_recessive', {}, samples_by_id, {})
        self.assertDictEqual(inheritance_filter.to_dict(), {'bool': {'_name': 'F000002_2', 'must': [recessive_filter]}})
        inheritance_filter = _genotype_inheritance_filter('homozygous_recessive', {'affected': custom_affected}, samples_by_id, {})
        self.assertDictEqual(inheritance_filter.to_dict(), {
            'bool': {'_name': 'F000002_2', 'must': [custom_affected_recessive_filter]}
        })

        # compound het
        inheritance_filter = _genotype_inheritance_filter('compound_het', {}, samples_by_id, {})
        self.assertDictEqual(inheritance_filter.to_dict(), {'bool': {'_name': 'F000002_2', 'must': [{
            'bool': {
                'must_not': [
                    {'term': {'samples_no_call': 'HG00732'}},
                    {'term': {'samples_num_alt_2': 'HG00732'}},
                    {'term': {'samples_no_call': 'HG00733'}},
                    {'term': {'samples_num_alt_2': 'HG00733'}}
                ],
                'must': [
                    {'term': {'samples_num_alt_1': 'HG00731'}},
                ]
            }
        }]}})
        inheritance_filter = _genotype_inheritance_filter('compound_het', {'affected': custom_affected}, samples_by_id, {})
        self.assertDictEqual(inheritance_filter.to_dict(), {'bool': {'_name': 'F000002_2', 'must': [{
            'bool': {
                'must_not': [
                    {'term': {'samples_no_call': 'HG00731'}},
                    {'term': {'samples_num_alt_2': 'HG00731'}},
                    {'term': {'samples_no_call': 'HG00733'}},
                    {'term': {'samples_num_alt_2': 'HG00733'}}
                ],
                'must': [
                    {'term': {'samples_num_alt_1': 'HG00732'}},
                ]
            }
        }]}})

        # x-linked recessive
        x_linked_filter = {
            'bool': {
                'must_not': [
                    {'term': {'samples_no_call': 'HG00732'}},
                    {'term': {'samples_num_alt_1': 'HG00732'}},
                    {'term': {'samples_num_alt_2': 'HG00732'}},
                    {'term': {'samples_no_call': 'HG00733'}},
                    {'term': {'samples_num_alt_2': 'HG00733'}}
                ],
                'must': [
                    {'match': {'contig': 'X'}},
                    {'term': {'samples_num_alt_2': 'HG00731'}},
                ]
            }
        }

        custom_affected_x_linked_filter = {
            'bool': {
                'must_not': [
                    {'term': {'samples_no_call': 'HG00731'}},
                    {'term': {'samples_num_alt_2': 'HG00731'}},
                    {'term': {'samples_no_call': 'HG00733'}},
                    {'term': {'samples_num_alt_2': 'HG00733'}}
                ],
                'must': [
                    {'match': {'contig': 'X'}},
                    {'term': {'samples_num_alt_2': 'HG00732'}},
                ]
            }
        }

        inheritance_filter = _genotype_inheritance_filter('x_linked_recessive', {}, samples_by_id, {})
        self.assertDictEqual(inheritance_filter.to_dict(), {'bool': {'_name': 'F000002_2', 'must': [x_linked_filter]}})
        inheritance_filter = _genotype_inheritance_filter(
            'x_linked_recessive', {'affected': custom_affected}, samples_by_id, {})
        self.assertDictEqual(inheritance_filter.to_dict(), {
            'bool': {'_name': 'F000002_2', 'must': [custom_affected_x_linked_filter]}
        })

        # recessive
        inheritance_filter = _genotype_inheritance_filter('recessive', {}, samples_by_id, {})
        self.assertDictEqual(inheritance_filter.to_dict(), {'bool': {'_name': 'F000002_2', 'must': [{
            'bool': {'should': [recessive_filter, x_linked_filter]}
        }]}})
        inheritance_filter = _genotype_inheritance_filter('recessive', {'affected': custom_affected}, samples_by_id, {})
        self.assertDictEqual(inheritance_filter.to_dict(), {'bool': {'_name': 'F000002_2', 'must': [{
            'bool': {'should': [custom_affected_recessive_filter, custom_affected_x_linked_filter]}
        }]}})

        # any affected
        inheritance_filter = _genotype_inheritance_filter('any_affected', {}, samples_by_id, {})
        self.assertDictEqual(inheritance_filter.to_dict(), {'bool': {'_name': 'F000002_2', 'must': [{
            'bool': {
                'should': [
                    {'term': {'samples_num_alt_1': 'HG00731'}},
                    {'term': {'samples_num_alt_2': 'HG00731'}}
                ]
            }
        }]}})
        inheritance_filter = _genotype_inheritance_filter('any_affected', {'affected': custom_multi_affected}, samples_by_id, {})
        self.assertDictEqual(inheritance_filter.to_dict(), {'bool': {'_name': 'F000002_2', 'must': [{
            'bool': {
                'should': [
                    {'term': {'samples_num_alt_1': 'HG00731'}},
                    {'term': {'samples_num_alt_2': 'HG00731'}},
                    {'term': {'samples_num_alt_1': 'HG00732'}},
                    {'term': {'samples_num_alt_2': 'HG00732'}}
                ]
            }
        }]}})
