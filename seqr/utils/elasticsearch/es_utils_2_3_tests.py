from __future__ import unicode_literals

from copy import deepcopy
import mock
import jmespath
import json
from collections import defaultdict
from django.test import TestCase
from elasticsearch.exceptions import ConnectionTimeout
from sys import maxsize

from seqr.models import Family, Sample, VariantSearch, VariantSearchResults
from seqr.utils.elasticsearch.utils import get_es_variants_for_variant_tuples, get_single_es_variant, get_es_variants, \
    get_es_variant_gene_counts, get_es_variants_for_variant_ids, InvalidIndexException
from seqr.utils.elasticsearch.es_search import EsSearch, _get_family_affected_status, _liftover_grch38_to_grch37, \
    _liftover_grch37_to_grch38

INDEX_NAME = 'test_index'
SECOND_INDEX_NAME = 'test_index_second'
SV_INDEX_NAME = 'test_index_sv'

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
          'gnomad_genomes_FAF_AF': 0.000437,
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
          'cadd_PHRED': None,
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
          'primate_ai_score': 1,
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
          'gnomad_genomes_FAF_AF': None,
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

ES_SV_VARIANT = {
    '_source': {
      'genotypes': [
        {
          'qs': 33,
          'cn': 1,
          'defragged': False,
          'sample_id': 'HG00731',
          'num_exon': 2,
          'start': 49045487,
          'end': 49045899,
        }
      ],
      'xpos': 1049045387,
      'end': 49045898,
      'start': 49045387,
      'xstart': 1049045587,
      'num_exon': 1,
      'pos': 49045487,
      'StrVCTVRE_score': 0.374,
      'svType': 'DEL',
      'xstop': 1049045898,
      'variantId': 'prefix_19107_DEL',
      'samples': ['HG00731'],
      'sc': 7,
      'contig': '1',
      'sortedTranscriptConsequences': [
        {
          'transcript_id': 'ENST00000371839',
          'biotype': 'protein_coding',
          'gene_id': 'ENSG00000228198'
        },
        {
          'transcript_id': 'ENST00000416121',
          'biotype': 'protein_coding',
          'gene_id': 'ENSG00000228198'
        },
      ],
      'geneIds': ['ENSG00000228198'],
      'sf': 0.000693825,
      'sn': 10088
    },
    'matched_queries': {SV_INDEX_NAME: ['F000002_2']},
  }

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
    INDEX_NAME: {
        'ENSG00000135953': EXTRA_FAMILY_ES_VARIANTS,
        'ENSG00000228198': EXTRA_FAMILY_ES_VARIANTS,
        'ENSG00000228199': EXTRA_FAMILY_ES_VARIANTS,
    },
    SECOND_INDEX_NAME: {
        'ENSG00000135953': MFSD9_COMPOUND_HET_ES_VARIANTS, 'ENSG00000228198': OR2M3_COMPOUND_HET_ES_VARIANTS,
    },
    '{},{}'.format(INDEX_NAME, SECOND_INDEX_NAME): {'ENSG00000135953': MISSING_SAMPLE_ES_VARIANTS},
    SV_INDEX_NAME: {'ENSG00000228198': [ES_SV_VARIANT], 'ENSG00000135953': []},
    '{},{}'.format(INDEX_NAME, SV_INDEX_NAME): {'ENSG00000228198': [ES_SV_VARIANT, ES_VARIANTS[1]], 'ENSG00000135953': []},
}

INDEX_ES_VARIANTS = {INDEX_NAME: ES_VARIANTS, SECOND_INDEX_NAME: [BUILD_38_ES_VARIANT], SV_INDEX_NAME: [ES_SV_VARIANT]}

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
            'I000007_na20870': {
                'ab': 1, 'ad': None, 'gq': 99, 'sampleId': 'NA20870', 'numAlt': 2, 'dp': 74, 'pl': None,
                'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
            }
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
            'callset': {'an': 32, 'ac': 2, 'hom': None, 'af': 0.063, 'hemi': None, 'filter_af': None},
            'g1k': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0, 'filter_af': None},
            'gnomad_genomes': {'an': 30946, 'ac': 4, 'hom': 0, 'af': 0.00012925741614425127, 'hemi': 0, 'filter_af': 0.000437},
            'exac': {'an': 121308, 'ac': 8, 'hom': 0, 'af': 0.00006589, 'hemi': 0, 'filter_af': 0.0006726888333653661},
            'gnomad_exomes': {'an': 245930, 'ac': 16, 'hom': 0, 'af': 0.00006505916317651364, 'hemi': 0, 'filter_af': 0.0009151523074911753},
            'topmed': {'an': 125568, 'ac': 21, 'hom': 0, 'af': 0.00016724, 'hemi': 0, 'filter_af': None},
            'sv_callset': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None},
        },
        'pos': 248367227,
        'predictions': {'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None,
                        'polyphen': None, 'dann': None, 'sift': None, 'cadd': 25.9, 'metasvm': None, 'primate_ai': None,
                        'gerp_rs': None, 'mpc': None, 'phastcons_100_vert': None, 'strvctvre': None},
        'ref': 'TC',
        'rsid': None,
        'transcripts': {
            'ENSG00000135953': [TRANSCRIPT_3],
            'ENSG00000228198': [TRANSCRIPT_2],
        },
        'variantId': '1-248367227-TC-T',
        'xpos': 1248367227,
        'end': None,
        'svType': None,
        'numExon': None,
        '_sort': [1248367227],
    },
    {
        'alt': 'G',
        'chrom': '2',
        'clinvar': {'clinicalSignificance': None, 'alleleId': None, 'variationId': None, 'goldStars': None},
        'familyGuids': ['F000002_2', 'F000003_3'],
        'genotypes': {
            'I000004_hg00731': {
                'ab': 0, 'ad': None, 'gq': 99, 'sampleId': 'HG00731', 'numAlt': 0, 'dp': 67, 'pl': None,
                'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
            },
            'I000005_hg00732': {
                'ab': 0, 'ad': None, 'gq': 96, 'sampleId': 'HG00732', 'numAlt': 2, 'dp': 42, 'pl': None,
                'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
            },
            'I000006_hg00733': {
                'ab': 0, 'ad': None, 'gq': 96, 'sampleId': 'HG00733', 'numAlt': 1, 'dp': 42, 'pl': None,
                'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
            },
            'I000007_na20870': {
                'ab': 0.70212764, 'ad': None, 'gq': 46, 'sampleId': 'NA20870', 'numAlt': 1, 'dp': 50, 'pl': None,
                'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
            }
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
            'callset': {'an': 32, 'ac': 1, 'hom': None, 'af': 0.031, 'hemi': None, 'filter_af': None},
            'g1k': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0, 'filter_af': None},
            'gnomad_genomes': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0, 'filter_af': None},
            'exac': {'an': 121336, 'ac': 6, 'hom': 0, 'af': 0.00004942, 'hemi': 0, 'filter_af': 0.000242306760358614},
            'gnomad_exomes': {'an': 245714, 'ac': 6, 'hom': 0, 'af': 0.000024418633044922146, 'hemi': 0, 'filter_af': 0.00016269686320447742},
            'topmed': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0, 'filter_af': None},
            'sv_callset': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None},
        },
        'pos': 103343353,
        'predictions': {
            'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None, 'polyphen': None,
            'dann': None, 'sift': None, 'cadd': None, 'metasvm': None, 'primate_ai': 1, 'gerp_rs': None,
            'mpc': None, 'phastcons_100_vert': None, 'strvctvre': None,
        },
        'ref': 'GAGA',
        'rsid': None,
        'transcripts': {
            'ENSG00000135953': [TRANSCRIPT_1],
            'ENSG00000228198': [TRANSCRIPT_2],
        },
        'variantId': '2-103343353-GAGA-G',
        'xpos': 2103343353,
        'end': None,
        'svType': None,
        'numExon': None,
        '_sort': [2103343353],
    },
]
PARSED_SV_VARIANT = {
    'alt': None,
    'chrom': '1',
    'familyGuids': ['F000002_2'],
    'genotypes': {
        'I000004_hg00731': {
            'ab': None, 'ad': None, 'gq': None, 'sampleId': 'HG00731', 'numAlt': -1, 'dp': None, 'pl': None,
            'cn': 1, 'end': None, 'start': None, 'numExon': 2, 'defragged': False, 'qs': 33,
        },
        'I000005_hg00732': {
            'ab': None, 'ad': None, 'gq': None, 'sampleId': 'HG00732', 'numAlt': -1, 'dp': None, 'pl': None,
            'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None, 'isRef': True,
        },
    },
    'clinvar': {'clinicalSignificance': None, 'alleleId': None, 'variationId': None, 'goldStars': None},
    'hgmd': {'accession': None, 'class': None},
    'genomeVersion': '37',
    'genotypeFilters': [],
    'liftedOverChrom': None,
    'liftedOverGenomeVersion': None,
    'liftedOverPos': None,
    'mainTranscriptId': None,
    'originalAltAlleles': [],
    'populations': {
        'callset': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None},
        'g1k': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None},
        'gnomad_genomes': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None},
        'exac': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None},
        'gnomad_exomes': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None},
        'topmed': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None},
        'sv_callset': {'an': 10088, 'ac': 7, 'hom': None, 'af': 0.000693825, 'hemi': None, 'filter_af': None},
    },
    'pos': 49045487,
    'predictions': {'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None,
                    'polyphen': None, 'dann': None, 'sift': None, 'cadd': None, 'metasvm': None, 'primate_ai': None,
                    'gerp_rs': None, 'mpc': None, 'phastcons_100_vert': None, 'strvctvre': 0.374},
    'ref': None,
    'rsid': None,
    'transcripts': {
        'ENSG00000228198': [
            {
              'transcriptId': 'ENST00000371839',
              'biotype': 'protein_coding',
              'geneId': 'ENSG00000228198'
            },
            {
              'transcriptId': 'ENST00000416121',
              'biotype': 'protein_coding',
              'geneId': 'ENSG00000228198'
            },
        ],
    },
    'variantId': 'prefix_19107_DEL',
    'xpos': 1049045487,
    'end': 49045899,
    'svType': 'DEL',
    'numExon': 2,
    '_sort': [1049045387],
}

PARSED_ANY_AFFECTED_VARIANTS = deepcopy(PARSED_VARIANTS)
PARSED_ANY_AFFECTED_VARIANTS[1]['familyGuids'] = ['F000003_3']
PARSED_ANY_AFFECTED_VARIANTS[1]['genotypes'] = {'I000007_na20870': PARSED_ANY_AFFECTED_VARIANTS[1]['genotypes']['I000007_na20870']}

PARSED_COMPOUND_HET_VARIANTS = deepcopy(PARSED_VARIANTS)
PARSED_COMPOUND_HET_VARIANTS[0]['_sort'] = [1248367327]
PARSED_COMPOUND_HET_VARIANTS[1]['_sort'] = [2103343453]
PARSED_COMPOUND_HET_VARIANTS[1]['familyGuids'] = ['F000003_3']

PARSED_SV_COMPOUND_HET_VARIANTS = [deepcopy(PARSED_SV_VARIANT), deepcopy(PARSED_COMPOUND_HET_VARIANTS[1])]
PARSED_SV_COMPOUND_HET_VARIANTS[0]['_sort'] = [1049045487]
PARSED_SV_COMPOUND_HET_VARIANTS[1]['familyGuids'] = ['F000002_2']

PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT = deepcopy(PARSED_COMPOUND_HET_VARIANTS)
for variant in PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT:
    variant['familyGuids'].append('F000011_11')
    variant['genotypes'].update({
        'I000015_na20885': {
            'ab': 0.631, 'ad': None, 'gq': 99, 'sampleId': 'NA20885', 'numAlt': 1, 'dp': 50, 'pl': None,
            'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
        },
    })
PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT[1]['transcripts']['ENSG00000135953'][0]['majorConsequence'] = 'frameshift_variant'
PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT[1]['mainTranscriptId'] = TRANSCRIPT_2['transcriptId']

PARSED_COMPOUND_HET_VARIANTS_PROJECT_2 = deepcopy(PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT)
for variant in PARSED_COMPOUND_HET_VARIANTS_PROJECT_2:
    variant.update({
        'variantId': '{}-het'.format(variant['variantId']),
        'familyGuids': ['F000011_11'],
        'genotypes': {
            'I000015_na20885': {
                'ab': 0.631, 'ad': None, 'gq': 99, 'sampleId': 'NA20885', 'numAlt': 1, 'dp': 50, 'pl': None,
                'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
            },
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

PARSED_CADD_VARIANTS = deepcopy(PARSED_VARIANTS)
PARSED_CADD_VARIANTS[0]['_sort'][0] = -25.9
PARSED_CADD_VARIANTS[1]['_sort'][0] = maxsize


PARSED_MULTI_INDEX_VARIANT = deepcopy(PARSED_VARIANTS[1])
PARSED_MULTI_INDEX_VARIANT.update({
    'familyGuids': ['F000002_2', 'F000003_3', 'F000011_11'],
    'genotypes': {
        'I000004_hg00731': {
            'ab': 0, 'ad': None, 'gq': 99, 'sampleId': 'HG00731', 'numAlt': 0, 'dp': 67, 'pl': None,
            'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
        },
        'I000005_hg00732': {
            'ab': 0, 'ad': None, 'gq': 96, 'sampleId': 'HG00732', 'numAlt': 2, 'dp': 42, 'pl': None,
            'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
        },
        'I000006_hg00733': {
            'ab': 0, 'ad': None, 'gq': 96, 'sampleId': 'HG00733', 'numAlt': 1, 'dp': 42, 'pl': None,
            'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
        },
        'I000007_na20870': {
            'ab': 0.70212764, 'ad': None, 'gq': 46, 'sampleId': 'NA20870', 'numAlt': 1, 'dp': 50, 'pl': None,
            'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
        },
        'I000015_na20885': {
            'ab': 0.631, 'ad': None, 'gq': 99, 'sampleId': 'NA20885', 'numAlt': 1, 'dp': 50, 'pl': None,
            'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
        },
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

PARSED_ANY_AFFECTED_MULTI_GENOME_VERSION_VARIANT = deepcopy(PARSED_MULTI_GENOME_VERSION_VARIANT)
PARSED_ANY_AFFECTED_MULTI_GENOME_VERSION_VARIANT.update({
    'familyGuids': ['F000003_3', 'F000011_11'],
    'genotypes': {
        'I000007_na20870': {
            'ab': 0.70212764, 'ad': None, 'gq': 46, 'sampleId': 'NA20870', 'numAlt': 1, 'dp': 50, 'pl': None,
            'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
        },
        'I000015_na20885': {
            'ab': 0.631, 'ad': None, 'gq': 99, 'sampleId': 'NA20885', 'numAlt': 1, 'dp': 50, 'pl': None,
            'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
        },
    },
})
MAPPING_FIELDS = [
    'start',
    'end',
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
    'samples_no_call',
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
    'AN',
    'g1k_AC',
    'g1k_Hom',
    'g1k_Hemi',
    'g1k_POPMAX_AF',
    'g1k_AF',
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
    'exac_AC_Hom',
    'exac_AC_Hemi',
    'exac_AF_POPMAX',
    'exac_AF',
    'exac_AN_Adj',
    'topmed_AC',
    'topmed_Hom',
    'topmed_Hemi',
    'topmed_AF',
    'topmed_AN',
    'gnomad_genomes_FAF_AF',
]
SV_MAPPING_FIELDS = [
    'start',
    'end',
    'xpos',
    'contig',
    'variantId',
    'sortedTranscriptConsequences',
    'genotypes',
    'samples',
    'samples_cn_0',
    'samples_cn_1',
    'samples_cn_2',
    'samples_cn_3',
    'samples_cn_gte_4',
    'sf',
    'sc',
    'sn',
    'num_exon',
    'svType',
    'StrVCTVRE_score',
]
SOURCE_FIELDS = {
    'callset_Hom', 'callset_Hemi', 'gnomad_exomes_FAF_AF','sv_callset_Hemi', 'sv_callset_Hom',
}
SOURCE_FIELDS.update(MAPPING_FIELDS)
SOURCE_FIELDS.update(SV_MAPPING_FIELDS)
SOURCE_FIELDS -= {'samples_no_call', 'samples_cn_0', 'samples_cn_1', 'samples_cn_2', 'samples_cn_3', 'samples_cn_gte_4'}

INDEX_METADATA = {
    INDEX_NAME: {'variant': {
        '_meta': {'genomeVersion': '37'},
        'properties': {field: {} for field in MAPPING_FIELDS},
    }},
    SECOND_INDEX_NAME: {'variant': {
        '_meta': {'genomeVersion': '38', 'datasetType': 'VARIANTS'},
        'properties': {field: {} for field in MAPPING_FIELDS},
    }},
    SV_INDEX_NAME: {'structural_variant': {
        '_meta': {'genomeVersion': '37', 'datasetType': 'SV'},
        'properties': {field: {} for field in SV_MAPPING_FIELDS},
    }},
}

ALL_INHERITANCE_QUERY = {
    'bool': {
        'should': [
            {'bool': {
                'must': [
                    {'bool': {'should': [
                        {'terms': {'samples_num_alt_1': ['HG00731', 'HG00732', 'HG00733']}},
                        {'terms': {'samples_num_alt_2': ['HG00731', 'HG00732', 'HG00733']}},
                        {'terms': {'samples': ['HG00731', 'HG00732', 'HG00733']}},
                    ]}}
                ],
                '_name': 'F000002_2'
            }},
            {'bool': {
                'must': [
                    {'bool': {'should': [
                        {'terms': {'samples_num_alt_1': ['NA20870']}},
                        {'terms': {'samples_num_alt_2': ['NA20870']}},
                        {'terms': {'samples': ['NA20870']}},
                    ]}}
                ],
                '_name': 'F000003_3'
            }},
            {'bool': {
                'must': [
                    {'bool': {'should': [
                        {'terms': {'samples_num_alt_1': ['NA20874']}},
                        {'terms': {'samples_num_alt_2': ['NA20874']}},
                        {'terms': {'samples': ['NA20874']}},
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

ANNOTATION_QUERY = {'terms': {'transcriptConsequenceTerms': ['frameshift_variant']}}

REDIS_CACHE = {}
def _set_cache(k, v):
    REDIS_CACHE[k] = v
MOCK_REDIS = mock.MagicMock()
MOCK_REDIS.get.side_effect = REDIS_CACHE.get
MOCK_REDIS.set.side_effect =_set_cache

MOCK_LIFTOVERS = {
    'hg38': mock.MagicMock(),
    'hg19': mock.MagicMock(),
}
MOCK_LIFTOVERS['hg38'].convert_coordinate.side_effect = lambda chrom, pos: [[chrom, pos - 10]]
MOCK_LIFTOVERS['hg19'].convert_coordinate.side_effect = lambda chrom, pos: [[chrom, pos + 10]]


def mock_hits(hits, increment_sort=False, include_matched_queries=True, sort=None, index=INDEX_NAME):
    parsed_hits = deepcopy(hits)
    for hit in parsed_hits:
        hit.update({
            '_index': index,
            '_id': hit['_source']['variantId'],
            '_type': 'structural_variant' if SV_INDEX_NAME in index else 'variant',
        })
        matched_queries = hit.pop('matched_queries')
        if include_matched_queries:
            hit['matched_queries'] = []
            for subindex in index.split(','):
                if subindex in matched_queries:
                    hit['_index'] = subindex
                    hit['matched_queries'] += matched_queries[subindex]

        if sort or increment_sort:
            sort_key = sort[0] if sort else 'xpos'
            if isinstance(sort_key, dict):
                if '_script' in sort_key:
                    sort_key = sort_key['_script']['script']['params'].get('field', 'xpos')
                else:
                    sort_key = next(iter(sort_key.keys()))
            sort_value = jmespath.search(sort_key, hit['_source'])
            if sort_value is None:
                sort_value = 'Infinity'
            if increment_sort:
                sort_value += 100
            hit['_sort'] = [sort_value]
    return parsed_hits


def create_mock_response(search, index=INDEX_NAME):
    indices = index.split(',')
    include_matched_queries = False
    variant_id_filters = None
    if 'query' in search:
        for search_filter in search['query']['bool']['filter']:
            if not variant_id_filters:
                variant_id_filters = search_filter.get('terms', {}).get('variantId')
            possible_inheritance_filters = search_filter.get('bool', {}).get('should', [])
            if any('_name' in possible_filter.get('bool', {}) for possible_filter in possible_inheritance_filters):
                include_matched_queries = True
                break

    response_dict = {
        'took': 1,
        'hits': {'total': 5, 'hits': []}
    }
    for index_name in sorted(indices):
        index_hits = mock_hits(
            INDEX_ES_VARIANTS[index_name], include_matched_queries=include_matched_queries, sort=search.get('sort'),
            index=index_name)
        if variant_id_filters:
            index_hits = [hit for hit in index_hits if hit['_id'] in variant_id_filters]
        response_dict['hits']['hits'] += index_hits

    if search.get('aggs'):
        index_vars = COMPOUND_HET_INDEX_VARIANTS.get(index, {})
        buckets = [{'key': gene_id, 'doc_count': 3} for gene_id in ['ENSG00000135953', 'ENSG00000228198']]
        if search['aggs']['genes']['aggs'].get('vars_by_gene'):
            for bucket in buckets:
                bucket['vars_by_gene'] = {
                    'hits': {
                        'hits': mock_hits(index_vars.get(bucket['key'], ES_VARIANTS), increment_sort=True, index=index)
                    }}
        else:
            for bucket in buckets:
                for sample_field in ['samples', 'samples_num_alt_1', 'samples_num_alt_2']:
                    gene_samples = defaultdict(int)
                    for var in index_vars.get(bucket['key'], ES_VARIANTS):
                        for sample in var['_source'].get(sample_field, []):
                            gene_samples[sample] += 1
                    bucket[sample_field] = {'buckets': [{'key': k, 'doc_count': v} for k, v in gene_samples.items()]}

        response_dict['aggregations'] = {'genes': {'buckets': buckets}}

    return response_dict


@mock.patch('seqr.utils.redis_utils.redis.StrictRedis', lambda **kwargs: MOCK_REDIS)
class EsUtilsTest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data']
    multi_db = True

    def setUp(self):
        Sample.objects.filter(sample_id='NA19678').update(is_active=False)
        self.families = Family.objects.filter(guid__in=['F000003_3', 'F000002_2', 'F000005_5'])

        self.mock_es_client = mock.MagicMock()
        self.mock_es_client.indices.get_mapping.side_effect = lambda index='': {
            k: {'mappings': INDEX_METADATA[k]} for k in index.split(',')}

        self.mock_search = self.mock_es_client.search
        self.mock_search.side_effect = lambda index=None, body=None, **kwargs: create_mock_response(
            deepcopy(body), index=','.join(index))
        self.mock_multi_search = self.mock_es_client.msearch
        self.mock_multi_search.side_effect = lambda body=None, **kwargs: {
            'responses': [
                create_mock_response(exec_search, index=','.join(body[i-1]['index']))
                for i, exec_search in enumerate(deepcopy(body)) if not exec_search.get('index')]}

        patcher = mock.patch('seqr.utils.elasticsearch.utils.elasticsearch.Elasticsearch')
        patcher.start().return_value = self.mock_es_client
        self.addCleanup(patcher.stop)

        self.mock_liftovers = {
            'hg38': mock.MagicMock(),
            'hg19': mock.MagicMock(),
        }
        self.mock_liftovers['hg38'].convert_coordinate.side_effect = lambda chrom, pos: [[chrom, pos - 10]]
        self.mock_liftovers['hg19'].convert_coordinate.side_effect = lambda chrom, pos: [[chrom, pos + 10]]

        liftover_patcher = mock.patch('seqr.utils.elasticsearch.es_search.LiftOver')
        self.mock_liftover = liftover_patcher.start()
        self.mock_liftover.side_effect = lambda v1, v2: MOCK_LIFTOVERS[v1]
        self.addCleanup(liftover_patcher.stop)

    def assertExecutedSearch(self, filters=None, start_index=0, size=2, sort=None, gene_aggs=False, gene_count_aggs=None, index=INDEX_NAME):
        executed_search = self.mock_search.call_args.kwargs['body']
        searched_indices = self.mock_search.call_args.kwargs['index']
        self.assertListEqual(sorted(searched_indices), sorted(index.split(',')))
        self.assertSameSearch(
            executed_search,
            dict(filters=filters, start_index=start_index, size=size, sort=sort, gene_aggs=gene_aggs,
                 gene_count_aggs=gene_count_aggs)
        )

    def assertExecutedSearches(self, searches):
        executed_search = self.mock_multi_search.call_args.kwargs['body']
        self.assertEqual(len(executed_search), len(searches) * 2)
        for i, expected_search in enumerate(searches):
            self.assertDictEqual(executed_search[i * 2], {'index': expected_search.get('index', INDEX_NAME).split(',')})
            self.assertSameSearch(executed_search[(i * 2) + 1], expected_search)

    def assertSameSearch(self, executed_search, expected_search_params):
        expected_search = {
            'from': expected_search_params['start_index'],
            'size': expected_search_params['size']
        }

        if expected_search_params['filters']:
            for i in range(len(expected_search_params['filters'])):
                if 'bool' in expected_search_params['filters'][i] and 'must' in expected_search_params['filters'][i]['bool']:
                    expected_search_params['filters'][i]['bool']['must'] = mock.ANY
                if 'bool' in expected_search_params['filters'][i] and 'should' in expected_search_params['filters'][i]['bool']:
                    expected_search_params['filters'][i]['bool']['should'] = mock.ANY
            expected_search['query'] = {
                'bool': {
                    'filter': expected_search_params['filters']
                }
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
            [(2103343353, 'GAGA', 'G'), (1248367227, 'TC', 'T'), (25138367346, 'A', 'C')]
        )

        self.assertEqual(len(variants), 2)
        self.assertDictEqual(variants[0], PARSED_NO_SORT_VARIANTS[0])
        self.assertDictEqual(variants[1], PARSED_NO_SORT_VARIANTS[1])

        self.assertExecutedSearch(
            filters=[{'terms': {'variantId': ['2-103343353-GAGA-G', '1-248367227-TC-T', 'MT-138367346-A-C']}}], size=3,
        )

    def test_get_es_variants_for_variant_ids(self):
        get_es_variants_for_variant_ids(self.families, ['2-103343353-GAGA-G', '1-248367227-TC-T', 'prefix-938_DEL'])
        self.assertExecutedSearch(
            filters=[{'terms': {'variantId': ['2-103343353-GAGA-G', '1-248367227-TC-T', 'prefix-938_DEL']}}],
            size=6, index=','.join([INDEX_NAME, SV_INDEX_NAME]),
        )

    def test_get_single_es_variant(self):
        variant = get_single_es_variant(self.families, '2-103343353-GAGA-G')
        self.assertDictEqual(variant, PARSED_NO_SORT_VARIANTS[1])
        self.assertExecutedSearch(
            filters=[{'terms': {'variantId': ['2-103343353-GAGA-G']}}],
            size=2, index=','.join([INDEX_NAME, SV_INDEX_NAME]),
        )

        variant = get_single_es_variant(self.families, '1-248367227-TC-T', return_all_queried_families=True)
        all_family_variant = deepcopy(PARSED_NO_SORT_VARIANTS[0])
        all_family_variant['familyGuids'] = ['F000002_2', 'F000003_3', 'F000005_5']
        all_family_variant['genotypes']['I000004_hg00731'] = {
            'ab': 0, 'ad': None, 'gq': 99, 'sampleId': 'HG00731', 'numAlt': 0, 'dp': 88, 'pl': None,
            'cn': 2, 'end': None, 'start': None, 'numExon': None, 'defragged': None, 'qs': None,
        }
        self.assertDictEqual(variant, all_family_variant)
        self.assertExecutedSearch(
            filters=[{'terms': {'variantId': ['1-248367227-TC-T']}}],
            size=2, index=','.join([INDEX_NAME, SV_INDEX_NAME]),
        )

        with self.assertRaises(Exception) as cm:
            get_single_es_variant(self.families, '10-10334333-A-G')
        self.assertEqual(str(cm.exception), 'Variant 10-10334333-A-G not found')

    @mock.patch('seqr.utils.elasticsearch.es_search.LIFTOVER_GRCH38_TO_GRCH37', None)
    @mock.patch('seqr.utils.elasticsearch.es_search.LIFTOVER_GRCH37_TO_GRCH38', None)
    @mock.patch('seqr.utils.elasticsearch.es_search.MAX_COMPOUND_HET_GENES', 1)
    @mock.patch('seqr.utils.elasticsearch.es_gene_agg_search.MAX_COMPOUND_HET_GENES', 1)
    def test_invalid_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(family_id='no_individuals'))

        self.mock_liftover.side_effect = Exception()
        self.assertIsNone(_liftover_grch38_to_grch37())
        self.assertIsNone(_liftover_grch37_to_grch38())

        with self.assertRaises(InvalidIndexException) as cm:
            get_es_variants(results_model)
        self.assertEqual(str(cm.exception), 'No es index found')

        results_model.families.set(self.families)
        with self.assertRaises(Exception) as cm:
            get_es_variants(results_model, page=200)
        self.assertEqual(str(cm.exception), 'Unable to load more than 10000 variants (20000 requested)')

        search_model.search = {'inheritance': {'mode': 'compound_het'}}
        search_model.save()
        with self.assertRaises(Exception) as cm:
            get_es_variants(results_model)
        self.assertEqual(
            str(cm.exception),
            'This search returned too many compound heterozygous variants. Please add stricter filters')

        with self.assertRaises(Exception) as cm:
            get_es_variant_gene_counts(results_model)
        self.assertEqual(str(cm.exception), 'This search returned too many genes')

        search_model.search = {'qualityFilter': {'min_gq': 7}}
        search_model.save()
        with self.assertRaises(Exception) as cm:
            get_es_variants(results_model)
        self.assertEqual(str(cm.exception), 'Invalid gq filter 7')

        search_model.search = {}
        search_model.save()
        self.mock_multi_search.side_effect = ConnectionTimeout()
        self.mock_es_client.tasks.list.return_value = {'tasks': {
            123: {'running_time_in_nanos': 10},
            456: {'running_time_in_nanos': 10 ** 12},
        }}
        with self.assertRaises(ConnectionTimeout):
            get_es_variants(results_model)
        self.assertEqual(self.mock_es_client.tasks.cancel.call_count, 1)
        self.mock_es_client.tasks.cancel.assert_called_with(parent_task_id=456)

        _set_cache('index_metadata__test_index,test_index_sv', None)
        self.mock_es_client.indices.get_mapping.side_effect = Exception('Connection error')
        with self.assertRaises(InvalidIndexException) as cm:
            get_es_variants(results_model)
        self.assertEqual(str(cm.exception), 'Error accessing index "test_index,test_index_sv": Connection error')

        self.mock_es_client.indices.get_mapping.side_effect = lambda **kwargs: {}
        with self.assertRaises(InvalidIndexException) as cm:
            get_es_variants(results_model)
        self.assertEqual(str(cm.exception), 'Could not find expected indices: test_index, test_index_sv')

    def test_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={'annotations': {'frameshift': ['frameshift_variant']}})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, total_results = get_es_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertDictEqual(variants[0], PARSED_VARIANTS[0])
        self.assertDictEqual(variants[1], PARSED_VARIANTS[1])
        self.assertEqual(total_results, 5)

        self.assertCachedResults(results_model, {'all_results': variants, 'total_results': 5})

        self.assertExecutedSearch(filters=[ANNOTATION_QUERY, ALL_INHERITANCE_QUERY], sort=['xpos'])

        # does not save non-consecutive pages
        variants, total_results = get_es_variants(results_model, page=3, num_results=2)
        self.assertEqual(total_results, 5)
        self.assertCachedResults(results_model, {'all_results': variants, 'total_results': 5})
        self.assertExecutedSearch(filters=[ANNOTATION_QUERY, ALL_INHERITANCE_QUERY], sort=['xpos'], start_index=4, size=2)

        # test pagination
        variants, total_results = get_es_variants(results_model, page=2, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertEqual(total_results, 5)
        self.assertCachedResults(results_model, {'all_results': PARSED_VARIANTS + PARSED_VARIANTS, 'total_results': 5})
        self.assertExecutedSearch(filters=[ANNOTATION_QUERY, ALL_INHERITANCE_QUERY], sort=['xpos'], start_index=2, size=2)

        # test does not re-fetch page
        self.mock_search.reset_mock()
        variants, total_results = get_es_variants(results_model, page=1, num_results=3)
        self.mock_search.assert_not_called()
        self.assertEqual(len(variants), 3)
        self.assertListEqual(variants, PARSED_VARIANTS + PARSED_VARIANTS[:1])
        self.assertEqual(total_results, 5)

        # test load_all
        variants, _ = get_es_variants(results_model, page=1, num_results=2, load_all=True)
        self.assertExecutedSearch(filters=[ANNOTATION_QUERY, ALL_INHERITANCE_QUERY], sort=['xpos'], start_index=4, size=1)
        self.assertEqual(len(variants), 5)
        self.assertListEqual(variants, PARSED_VARIANTS + PARSED_VARIANTS + PARSED_VARIANTS[:1])

    def test_filtered_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
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
                'gnomad_exomes': {'af': 0.01, 'ac': 3, 'hh': 3},
                'gnomad_genomes': {'af': 0.01, 'hh': 3},
                'topmed': {'ac': 2, 'af': None},
            },
            'qualityFilter': {'min_ab': 10, 'min_gq': 15, 'vcf_filter': 'pass'},
            'inheritance': {'mode': 'de_novo'},
            'customQuery': {'term': {'customFlag': 'flagVal'}},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)

        # Test invalid locations
        search_model.search['locus'] = {'rawItems': 'chr27:1234-5678', 'rawVariantItems': 'chr2-A-C'}
        with self.assertRaises(Exception) as cm:
            get_es_variants(results_model, sort='cadd', num_results=2)
        self.assertEqual(str(cm.exception), 'Invalid genes/intervals: chr27:1234-5678')

        search_model.search['locus']['rawItems'] = 'DDX11L1, chr2:1234-5678'
        with self.assertRaises(Exception) as cm:
            get_es_variants(results_model, sort='cadd', num_results=2)
        self.assertEqual(str(cm.exception), 'Invalid variants: chr2-A-C')
        search_model.search['locus']['rawVariantItems'] = 'rs9876,chr2-1234-A-C'

        # Test edge case where searching by inheritance with no affected individuals

        results_model.families.set([family for family in self.families if family.guid == 'F000005_5'])
        with self.assertRaises(Exception) as cm:
            get_es_variants(results_model, num_results=2)
        self.assertEqual(
            str(cm.exception), 'Inheritance based search is disabled in families with no affected individuals',
        )

        # Test successful search
        search_model.search['locus']['excludeLocations'] = True
        results_model.families.set(self.families)
        variants, total_results = get_es_variants(results_model, sort='cadd', num_results=2)

        self.assertListEqual(variants, PARSED_CADD_VARIANTS)
        self.assertEqual(total_results, 5)

        self.assertExecutedSearch(filters=[
            {'term': {'customFlag': 'flagVal'}},
            {
                'bool': {
                    'must_not': [
                        {'range': {'xpos': {'gte': 2000001234, 'lte': 2000005678}}},
                        {'range': {'xstop': {'gte': 2000001234, 'lte': 2000005678}}},
                        {'bool': {'must': [
                            {'range': {'xpos': {'lte': 2000001234}}},
                            {'range': {'xstop': {'gte': 2000005678}}}]}},
                        {'terms': {'geneIds': ['ENSG00000223972']}},
                        {'terms': {'rsid': ['rs9876']}},
                        {'terms': {'variantId': ['2-1234-A-C']}},
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
                                {'bool': {'must_not': [{'exists': {'field': 'gnomad_genomes_FAF_AF'}}]}},
                                {'range': {'gnomad_genomes_FAF_AF': {'lte': 0.01}}}
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
                                {'bool': {'must_not': [{'exists': {'field': 'gnomad_exomes_AF_POPMAX_OR_GLOBAL'}}]}},
                                {'range': {'gnomad_exomes_AF_POPMAX_OR_GLOBAL': {'lte': 0.01}}}
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
                        {'bool': {'must_not': [{'exists': {'field': 'transcriptConsequenceTerms'}}]}},
                        {'terms': {
                            'transcriptConsequenceTerms': [
                                '5_prime_UTR_variant',
                                'inframe_deletion',
                                'inframe_insertion',
                                'intergenic_variant',
                            ]
                        }},
                        {'terms': {
                            'clinvar_clinical_significance': [
                                'Likely_pathogenic', 'Pathogenic', 'Pathogenic/Likely_pathogenic'
                            ]
                        }},
                        {'terms': {'hgmd_class': ['DM', 'DM?']}},
                    ]
                }
            },
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
        ], sort=[{'cadd_PHRED': {'order': 'desc', 'unmapped_type': 'float'}}, 'xpos'])

    def test_sv_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'structural': ['DEL']},
            'freqs': {'sv_callset': {'af': 0.1}},
            'qualityFilter': {'min_qs': 20},
            'inheritance': {'mode': 'de_novo'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, _ = get_es_variants(results_model, num_results=2)
        self.assertListEqual(variants, [PARSED_SV_VARIANT])

        self.assertExecutedSearch(filters=[
            {'bool': {
                'should': [
                    {'bool': {'must_not': [{'exists': {'field': 'sf'}}]}},
                    {'range': {'sf': {'lte': 0.1}}}
                ]
            }},
            {'terms': {'transcriptConsequenceTerms': ['DEL']}},
            {'bool': {
                'must': [
                    {'bool': {
                        'must_not': [{'term': {'samples': 'HG00732'}}],
                        'must': [{'term': {'samples': 'HG00731'}}],
                    }},
                    {'bool': {
                        'must_not': [
                            {'term': {'samples_qs_0_to_10': 'HG00731'}},
                            {'term': {'samples_qs_10_to_20': 'HG00731'}},
                            {'term': {'samples_qs_0_to_10': 'HG00732'}},
                            {'term': {'samples_qs_10_to_20': 'HG00732'}},
                        ],
                    }}
                ],
                '_name': 'F000002_2'
            }}
        ], sort=['xpos'], index=SV_INDEX_NAME)

    def test_multi_dataset_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={'pathogenicity': {
            'clinvar': ['pathogenic'],
        }})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, _ = get_es_variants(results_model, num_results=5)
        self.assertListEqual(variants, [PARSED_SV_VARIANT] + PARSED_VARIANTS)
        path_filter = {'terms': {
            'clinvar_clinical_significance': [
                'Pathogenic', 'Pathogenic/Likely_pathogenic'
            ]
        }}
        self.assertExecutedSearches([
            dict(filters=[path_filter], start_index=0, size=5, sort=['xpos'], index=SV_INDEX_NAME),
            dict(filters=[path_filter, ALL_INHERITANCE_QUERY], start_index=0, size=5, sort=['xpos'], index=INDEX_NAME),
        ])

    def test_compound_het_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'qualityFilter': {'min_gq': 10},
            'annotations': {'frameshift': ['frameshift_variant']},
            'inheritance': {'mode': 'compound_het'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, total_results = get_es_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 1)
        self.assertListEqual(variants, [PARSED_COMPOUND_HET_VARIANTS])
        self.assertEqual(total_results, 1)

        self.assertCachedResults(results_model, {
            'grouped_results': [{'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS}],
            'total_results': 1,
        })

        self.assertExecutedSearch(
            filters=[ANNOTATION_QUERY, COMPOUND_HET_INHERITANCE_QUERY],
            gene_aggs=True,
            sort=['xpos'],
            start_index=0,
            size=1
        )

        # test pagination does not fetch
        self.mock_search.reset_mock()
        get_es_variants(results_model, page=2, num_results=2)
        self.mock_search.assert_not_called()

    def test_compound_het_get_es_variants_secondary_annotation(self):
        search_model = VariantSearch.objects.create(search={
            'qualityFilter': {'min_gq': 10},
            'annotations': {'frameshift': ['frameshift_variant']},
            'inheritance': {'mode': 'compound_het'},
            'annotations_secondary': {'frameshift': ['frameshift_variant'], 'other': ['intron']},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, total_results = get_es_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 1)
        self.assertListEqual(variants, [PARSED_COMPOUND_HET_VARIANTS])
        self.assertEqual(total_results, 1)

        self.assertCachedResults(results_model, {
            'grouped_results': [{'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS}],
            'total_results': 1,
        })

        annotation_query = {'bool': {'should': [
            {'terms': {'transcriptConsequenceTerms': ['frameshift_variant']}},
            {'terms': {'transcriptConsequenceTerms': ['frameshift_variant', 'intron']}}]}}

        self.assertExecutedSearch(
            filters=[annotation_query, COMPOUND_HET_INHERITANCE_QUERY],
            gene_aggs=True,
            sort=['xpos'],
            start_index=0,
            size=1
        )

        # test pagination does not fetch
        self.mock_search.reset_mock()
        get_es_variants(results_model, page=2, num_results=2)
        self.mock_search.assert_not_called()

        # variants require both primary and secondary annotations
        search_model.search = {
            'qualityFilter': {'min_gq': 10},
            'annotations': {'frameshift': ['frameshift_variant']},
            'inheritance': {'mode': 'compound_het'},
            'annotations_secondary': {'other': ['intron']},
        }
        search_model.save()
        _set_cache('search_results__{}__xpos'.format(results_model.guid), None)

        variants, total_results = get_es_variants(results_model, num_results=2)
        self.assertIsNone(variants)
        self.assertEqual(total_results, 0)

        annotation_query = {'bool': {'should': [
            {'terms': {'transcriptConsequenceTerms': ['frameshift_variant']}},
            {'terms': {'transcriptConsequenceTerms': ['intron']}}]}}

        self.assertExecutedSearch(
            filters=[annotation_query, COMPOUND_HET_INHERITANCE_QUERY],
            gene_aggs=True,
            sort=['xpos'],
            start_index=0,
            size=1
        )

    def test_recessive_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'qualityFilter': {'min_gq': 10, 'vcf_filter': 'pass'},
            'inheritance': {'mode': 'recessive'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, total_results = get_es_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertDictEqual(variants[0], PARSED_VARIANTS[0])
        self.assertDictEqual(variants[1][0], PARSED_COMPOUND_HET_VARIANTS[0])
        self.assertDictEqual(variants[1][1], PARSED_COMPOUND_HET_VARIANTS[1])
        self.assertEqual(total_results, 6)

        self.assertCachedResults(results_model, {
            'compound_het_results': [],
            'variant_results': [PARSED_VARIANTS[1]],
            'grouped_results': [{'null': [PARSED_VARIANTS[0]]}, {'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS}],
            'duplicate_doc_count': 0,
            'loaded_variant_counts': {'test_index_compound_het': {'total': 1, 'loaded': 1}, INDEX_NAME: {'loaded': 2, 'total': 5}},
            'total_results': 6,
        })

        pass_filter_query = {'bool': {'must_not': [{'exists': {'field': 'filters'}}]}}

        self.assertExecutedSearches([
            dict(
                filters=[pass_filter_query, ANNOTATION_QUERY, COMPOUND_HET_INHERITANCE_QUERY],
                gene_aggs=True,
                sort=['xpos'],
                start_index=0,
                size=1
            ),
            dict(
                filters=[pass_filter_query, ANNOTATION_QUERY, RECESSIVE_INHERITANCE_QUERY], start_index=0, size=2, sort=['xpos'],
            ),
        ])

        # test pagination

        variants, total_results = get_es_variants(results_model, page=3, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertListEqual(variants, PARSED_VARIANTS)
        self.assertEqual(total_results, 5)

        self.assertCachedResults(results_model, {
            'compound_het_results': [],
            'variant_results': [],
            'grouped_results': [
                {'null': [PARSED_VARIANTS[0]]}, {'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS},
                {'null': [PARSED_VARIANTS[0]]}, {'null': [PARSED_VARIANTS[1]]}],
            'duplicate_doc_count': 1,
            'loaded_variant_counts': {'test_index_compound_het': {'total': 1, 'loaded': 1}, INDEX_NAME: {'loaded': 4, 'total': 5}},
            'total_results': 5,
        })

        self.assertExecutedSearches([dict(filters=[pass_filter_query, ANNOTATION_QUERY, RECESSIVE_INHERITANCE_QUERY], start_index=2, size=4, sort=['xpos'])])

        self.mock_multi_search.reset_mock()
        get_es_variants(results_model, page=2, num_results=2)
        self.mock_multi_search.assert_not_called()

    def test_multi_datatype_recessive_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant'], 'structural': ['DEL']},
            'inheritance': {'mode': 'recessive'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, _ = get_es_variants(results_model, num_results=10)
        self.assertEqual(len(variants), 5)
        self.assertDictEqual(variants[0], PARSED_SV_VARIANT)
        self.assertDictEqual(variants[1][0], PARSED_SV_COMPOUND_HET_VARIANTS[0])
        self.assertDictEqual(variants[1][1], PARSED_SV_COMPOUND_HET_VARIANTS[1])
        self.assertDictEqual(variants[2], PARSED_VARIANTS[0])
        self.assertDictEqual(variants[3][0], PARSED_COMPOUND_HET_VARIANTS[0])
        self.assertDictEqual(variants[3][1], PARSED_COMPOUND_HET_VARIANTS[1])
        self.assertDictEqual(variants[4], PARSED_VARIANTS[1])

        annotation_query = {'terms': {'transcriptConsequenceTerms': ['DEL', 'frameshift_variant']}}

        self.assertExecutedSearches([
            dict(
                filters=[
                    annotation_query,
                    {'bool': {
                        '_name': 'F000002_2',
                        'must': [{
                            'bool': {
                                'should': [
                                    {'bool': {
                                        'minimum_should_match': 1,
                                        'should': [
                                            {'term': {'samples_cn_0': 'HG00731'}},
                                            {'term': {'samples_cn_2': 'HG00731'}},
                                            {'term': {'samples_cn_gte_4': 'HG00731'}},
                                        ],
                                        'must': [{
                                            'bool': {
                                                'minimum_should_match': 1,
                                                'should': [
                                                    {'term': {'samples_cn_1': 'HG00732'}},
                                                    {'term': {'samples_cn_3': 'HG00732'}},
                                                ]}
                                        }]
                                    }},
                                    {'bool': {
                                        'minimum_should_match': 1,
                                        'should': [
                                            {'term': {'samples_cn_0': 'HG00731'}},
                                            {'term': {'samples_cn_2': 'HG00731'}},
                                            {'term': {'samples_cn_gte_4': 'HG00731'}},
                                        ],
                                        'must_not': [{'term': {'samples': 'HG00732'}}],
                                        'must': [{'match': {'contig': 'X'}}],
                                    }}
                                ]
                            }
                        }]
                    }}
                ], start_index=0, size=10, sort=['xpos'], index=SV_INDEX_NAME,
            ),
            dict(
                filters=[annotation_query, {'bool': {
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
                                    'must': [{'term': {'samples_num_alt_1': 'HG00731'}}]
                                }},
                                {'term': {'samples': 'HG00731'}},
                            ]
                        }},
                    ]
                    }},
                 ],
                gene_aggs=True,
                sort=['xpos'],
                start_index=0,
                size=1,
                index=','.join([INDEX_NAME, SV_INDEX_NAME]),
            ),
            dict(
                filters=[
                    annotation_query,
                    {'bool': {'_name': 'F000003_3', 'must': [{'term': {'samples_num_alt_1': 'NA20870'}}]}},
                ],
                gene_aggs=True,
                sort=['xpos'],
                start_index=0,
                size=1
            ),
            dict(
                filters=[
                    annotation_query,
                    {
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
                                                    'must': [
                                                        {'match': {'contig': 'X'}},
                                                        {'term': {'samples_num_alt_2': 'HG00731'}}
                                                    ]
                                                }}
                                            ]
                                        }},
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
                                        }}
                                    ]
                                }},
                            ]
                        }
                    }
                ], start_index=0, size=10, sort=['xpos'],
            ),
        ])

    def test_all_samples_all_inheritance_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']}
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(project__guid='R0001_1kg'))

        variants, total_results = get_es_variants(results_model, num_results=2)
        self.assertListEqual(variants, PARSED_VARIANTS)
        self.assertEqual(total_results, 5)

        self.assertExecutedSearch(filters=[ANNOTATION_QUERY], sort=['xpos'])

    def test_all_samples_any_affected_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']}, 'inheritance': {'mode': 'any_affected'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(project__guid='R0001_1kg'))

        variants, total_results = get_es_variants(results_model, num_results=2)
        self.assertListEqual(variants, PARSED_ANY_AFFECTED_VARIANTS)
        self.assertEqual(total_results, 5)

        self.assertExecutedSearch(filters=[
            ANNOTATION_QUERY,
            {'bool': {
                'should': [
                    {'terms': {'samples_num_alt_1': ['HG00731', 'NA19675', 'NA20870']}},
                    {'terms': {'samples_num_alt_2': ['HG00731', 'NA19675', 'NA20870']}},
                    {'terms': {'samples': ['HG00731', 'NA19675', 'NA20870']}},
                ]
            }}
        ], sort=['xpos'])

    def test_multi_project_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'qualityFilter': {'min_gq': 10},
            'inheritance': {'mode': 'recessive'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(guid__in=['F000011_11', 'F000003_3', 'F000002_2']))

        variants, total_results = get_es_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertDictEqual(variants[0], PARSED_VARIANTS[0])
        self.assertDictEqual(variants[1][0], PARSED_COMPOUND_HET_VARIANTS_PROJECT_2[0])
        self.assertDictEqual(variants[1][1], PARSED_COMPOUND_HET_VARIANTS_PROJECT_2[1])
        self.assertEqual(total_results, 11)
        self.assertCachedResults(results_model, {
            'compound_het_results': [{'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS_MULTI_GENOME_VERSION}],
            'variant_results': [PARSED_MULTI_GENOME_VERSION_VARIANT],
            'grouped_results': [{'null': [PARSED_VARIANTS[0]]}, {'ENSG00000135953': PARSED_COMPOUND_HET_VARIANTS_PROJECT_2}],
            'duplicate_doc_count': 2,
            'loaded_variant_counts': {
                SECOND_INDEX_NAME: {'loaded': 1, 'total': 5},
                '{}_compound_het'.format(SECOND_INDEX_NAME): {'total': 2, 'loaded': 2},
                INDEX_NAME: {'loaded': 2, 'total': 5},
                '{}_compound_het'.format(INDEX_NAME): {'total': 1, 'loaded': 1},
            },
            'total_results': 11,
        })

        project_2_search = dict(
            filters=[
                ANNOTATION_QUERY,
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
                ANNOTATION_QUERY,
                RECESSIVE_INHERITANCE_QUERY,
            ], start_index=0, size=2, sort=['xpos'], index=INDEX_NAME)
        self.assertExecutedSearches([
            dict(
                filters=[
                    ANNOTATION_QUERY,
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
            project_2_search,
            dict(
                filters=[ANNOTATION_QUERY, COMPOUND_HET_INHERITANCE_QUERY],
                gene_aggs=True, sort=['xpos'], start_index=0, size=1, index=INDEX_NAME,
            ),
            project_1_search,
        ])

        # test pagination
        variants, total_results = get_es_variants(results_model, num_results=2, page=2)
        self.assertEqual(len(variants), 2)
        self.assertListEqual(variants, [PARSED_VARIANTS[0], PARSED_COMPOUND_HET_VARIANTS_MULTI_GENOME_VERSION])
        self.assertEqual(total_results, 9)

        cache_results = {
            'compound_het_results': [],
            'variant_results': [PARSED_MULTI_GENOME_VERSION_VARIANT],
            'grouped_results': [
                {'null': [PARSED_VARIANTS[0]]},
                {'ENSG00000135953': PARSED_COMPOUND_HET_VARIANTS_PROJECT_2},
                {'null': [PARSED_VARIANTS[0]]},
                {'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS_MULTI_GENOME_VERSION}
            ],
            'duplicate_doc_count': 4,
            'loaded_variant_counts': {
                SECOND_INDEX_NAME: {'loaded': 2, 'total': 5},
                '{}_compound_het'.format(SECOND_INDEX_NAME): {'total': 2, 'loaded': 2},
                INDEX_NAME: {'loaded': 4, 'total': 5},
                '{}_compound_het'.format(INDEX_NAME): {'total': 1, 'loaded': 1},
            },
            'total_results': 9,
        }
        self.assertCachedResults(results_model, cache_results)

        project_2_search['start_index'] = 1
        project_2_search['size'] = 3
        project_1_search['start_index'] = 2
        self.assertExecutedSearches([project_2_search, project_1_search])

        # If one project is fully loaded, only query the second project
        cache_results['loaded_variant_counts'][INDEX_NAME]['total'] = 4
        _set_cache('search_results__{}__xpos'.format(results_model.guid), json.dumps(cache_results))
        get_es_variants(results_model, num_results=2, page=3)
        project_2_search['start_index'] = 2
        project_2_search['size'] = 4
        self.assertExecutedSearches([project_2_search])

    def test_multi_project_all_samples_all_inheritance_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
        })
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
            index='{},{}'.format(INDEX_NAME, SECOND_INDEX_NAME),
            filters=[ANNOTATION_QUERY],
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
            index='{},{}'.format(INDEX_NAME, SECOND_INDEX_NAME),
            filters=[ANNOTATION_QUERY],
            sort=['xpos'],
            size=5,
            start_index=3,
        )

        # test skipping page fetches all consecutively
        _set_cache('search_results__{}__xpos'.format(results_model.guid), None)
        get_es_variants(results_model, num_results=2, page=2)
        self.assertExecutedSearch(
            index='{},{}'.format(INDEX_NAME, SECOND_INDEX_NAME),
            filters=[ANNOTATION_QUERY],
            sort=['xpos'],
            size=8,
        )

    def test_multi_project_all_samples_any_affected_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']}, 'inheritance': {'mode': 'any_affected'},
        },
        )
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.all())

        variants, total_results = get_es_variants(results_model, num_results=2)
        expected_variants = [PARSED_VARIANTS[0], PARSED_ANY_AFFECTED_MULTI_GENOME_VERSION_VARIANT]
        self.assertListEqual(variants, expected_variants)
        self.assertEqual(total_results, 9)

        self.assertExecutedSearches([
            dict(
                filters=[
                    ANNOTATION_QUERY,
                    {'bool': {
                        'should': [
                            {'terms': {'samples_num_alt_1': ['NA20885']}},
                            {'terms': {'samples_num_alt_2': ['NA20885']}},
                            {'terms': {'samples': ['NA20885']}},
                        ]
                    }}
                ], start_index=0, size=2, sort=['xpos'], index=SECOND_INDEX_NAME),
            dict(
                filters=[
                    ANNOTATION_QUERY,
                    {'bool': {
                        'should': [
                            {'terms': {'samples_num_alt_1': ['HG00731', 'NA19675', 'NA20870']}},
                            {'terms': {'samples_num_alt_2': ['HG00731', 'NA19675', 'NA20870']}},
                            {'terms': {'samples': ['HG00731', 'NA19675', 'NA20870']}},
                        ]
                    }},
                ], start_index=0, size=2, sort=['xpos'], index=INDEX_NAME)
        ])

    @mock.patch('seqr.utils.elasticsearch.es_search.MAX_VARIANTS', 3)
    def test_multi_project_get_variants_by_id(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'locus': {'rawVariantItems': '2-103343363-GAGA-G', 'genomeVersion': '38'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.all())

        variants, _ = get_es_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 1)
        self.assertDictEqual(variants[0], PARSED_MULTI_GENOME_VERSION_VARIANT)

        self.assertCachedResults(results_model, {
            'all_results': [PARSED_MULTI_GENOME_VERSION_VARIANT],
            'duplicate_doc_count': 1,
            'total_results': 4,
        })
        self.assertExecutedSearch(
            index='{},{}'.format(INDEX_NAME, SECOND_INDEX_NAME),
            filters=[
                {'terms': {'variantId': ['2-103343363-GAGA-G', '2-103343353-GAGA-G']}},
                ANNOTATION_QUERY,
            ],
            sort=['xpos'],
            size=3,
        )

        # Test liftover variant to hg38
        search_model.search['locus']['genomeVersion'] = '37'
        search_model.save()
        _set_cache('search_results__{}__xpos'.format(results_model.guid), None)
        get_es_variants(results_model, num_results=2)
        self.assertExecutedSearch(
            index='{},{}'.format(INDEX_NAME, SECOND_INDEX_NAME),
            filters=[
                {'terms': {'variantId': ['2-103343363-GAGA-G', '2-103343373-GAGA-G']}},
                ANNOTATION_QUERY,
            ],
            sort=['xpos'],
            size=3,
        )

    @mock.patch('seqr.utils.elasticsearch.es_search.MAX_INDEX_NAME_LENGTH', 30)
    @mock.patch('seqr.utils.elasticsearch.es_search.hashlib.md5')
    def test_get_es_variants_index_alias(self, mock_hashlib):
        search_model = VariantSearch.objects.create(search={})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.all())

        mock_hashlib.return_value.hexdigest.return_value = INDEX_NAME
        self.mock_es_client.indices.get_mapping.side_effect = lambda index='': {
            k: {'mappings': v} for k, v in INDEX_METADATA.items()}

        get_es_variants(results_model, num_results=2)

        self.assertExecutedSearch(index=INDEX_NAME, sort=['xpos'], size=6)
        self.mock_es_client.indices.update_aliases.assert_called_with(body={
            'actions': [{'add': {'indices': [SV_INDEX_NAME, SECOND_INDEX_NAME, INDEX_NAME], 'alias': INDEX_NAME}}]})

    def test_get_es_variant_gene_counts(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'qualityFilter': {'min_gq': 10},
            'inheritance': {'mode': 'recessive'},
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
            filters=[ANNOTATION_QUERY, RECESSIVE_INHERITANCE_QUERY],
            size=1, index=INDEX_NAME, gene_count_aggs={'vars_by_gene': {'top_hits': {'_source': 'none', 'size': 100}}})

        expected_cached_results = {'gene_aggs': gene_counts}
        expected_cached_results.update(initial_cached_results)
        self.assertCachedResults(results_model, expected_cached_results)

    def test_multi_project_get_es_variant_gene_counts(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'qualityFilter': {'min_gq': 10},
            'inheritance': {'mode': 'recessive'},
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

        expected_search = dict(size=1, start_index=0, gene_count_aggs={'vars_by_gene': {'top_hits': {'_source': 'none', 'size': 100}}})
        self.assertExecutedSearches([
            dict(filters=[
                ANNOTATION_QUERY,
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
            dict(filters=[ANNOTATION_QUERY, RECESSIVE_INHERITANCE_QUERY], index=INDEX_NAME, **expected_search),
        ])

        expected_cached_results = {'gene_aggs': gene_counts}
        expected_cached_results.update(initial_cached_results)
        self.assertCachedResults(results_model, expected_cached_results)

    def test_multi_project_all_samples_all_inheritance_get_es_variant_gene_counts(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.all())
        _set_cache('search_results__{}__xpos'.format(results_model.guid), json.dumps({'total_results': 5}))
        gene_counts = get_es_variant_gene_counts(results_model)

        self.assertDictEqual(gene_counts, {
            'ENSG00000135953': {'total': 3, 'families': {'F000003_3': 1, 'F000002_2': 1, 'F000011_11': 1}},
            'ENSG00000228198': {'total': 3, 'families': {'F000003_3': 2, 'F000002_2': 2, 'F000011_11': 2}}
        })

        self.assertExecutedSearch(
            index='{},{}'.format(INDEX_NAME, SECOND_INDEX_NAME),
            filters=[ANNOTATION_QUERY],
            size=1,
            gene_count_aggs={
                'samples': {'terms': {'field': 'samples', 'size': 10000}},
                'samples_num_alt_1': {'terms': {'field': 'samples_num_alt_1', 'size': 10000}},
                'samples_num_alt_2': {'terms': {'field': 'samples_num_alt_2', 'size': 10000}}
            }
        )

        self.assertCachedResults(results_model, {'gene_aggs': gene_counts, 'total_results': 5})

    def test_cached_get_es_variant_gene_counts(self):
        search_model = VariantSearch.objects.create(search={})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        cache_key = 'search_results__{}__xpos'.format(results_model.guid)
        self.mock_search.reset()

        cached_gene_counts = {
            'ENSG00000135953': {'total': 5, 'families': {'F000003_3': 2, 'F000002_2': 1, 'F000011_11': 4}},
            'ENSG00000228198': {'total': 5, 'families': {'F000003_3': 4, 'F000002_2': 1, 'F000011_11': 4}}
        }
        _set_cache(cache_key, json.dumps({'total_results': 5, 'gene_aggs': cached_gene_counts}))
        gene_counts = get_es_variant_gene_counts(results_model)
        self.assertDictEqual(gene_counts, cached_gene_counts)
        self.mock_search.assert_not_called()

        _set_cache(cache_key, json.dumps({'all_results': PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT, 'total_results': 2}))
        gene_counts = get_es_variant_gene_counts(results_model)
        self.assertDictEqual(gene_counts, {
            'ENSG00000135953': {'total': 1, 'families': {'F000003_3': 1, 'F000011_11': 1}},
            'ENSG00000228198': {'total': 1, 'families': {'F000003_3': 1, 'F000011_11': 1}}
        })
        self.mock_search.assert_not_called()

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
        self.mock_search.assert_not_called()

    def test_get_family_affected_status(self):
        samples_by_id = {'F000002_2': {
            sample_id: Sample.objects.get(sample_id=sample_id, dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS)
            for sample_id in ['HG00731', 'HG00732', 'HG00733']
        }}
        custom_affected = {'I000004_hg00731': 'N', 'I000005_hg00732': 'A'}
        custom_multi_affected = {'I000005_hg00732': 'A'}

        self.assertDictEqual(_get_family_affected_status(samples_by_id, {}), {
            'F000002_2': {'I000004_hg00731': 'A', 'I000005_hg00732': 'N', 'I000006_hg00733': 'N'}})

        custom_affected_status = _get_family_affected_status(samples_by_id, {'affected': custom_affected})
        self.assertDictEqual(custom_affected_status, {
            'F000002_2': {'I000004_hg00731': 'N', 'I000005_hg00732': 'A', 'I000006_hg00733': 'N'}})

        custom_affected_status = _get_family_affected_status(samples_by_id, {'affected': custom_multi_affected})
        self.assertDictEqual(custom_affected_status, {
            'F000002_2': {'I000004_hg00731': 'A', 'I000005_hg00732': 'A', 'I000006_hg00733': 'N'}})

    def test_sort(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(project__guid='R0001_1kg'))

        variants, _ = get_es_variants(results_model, sort='primate_ai', num_results=2)
        self.assertExecutedSearch(filters=[ANNOTATION_QUERY], sort=[
            {'primate_ai_score': {'order': 'desc', 'unmapped_type': 'float'}}, 'xpos'])
        self.assertEqual(variants[0]['_sort'][0], maxsize)
        self.assertEqual(variants[1]['_sort'][0], -1)

        variants, _ = get_es_variants(results_model, sort='gnomad', num_results=2)
        self.assertExecutedSearch(filters=[ANNOTATION_QUERY], sort=[
            {
                '_script': {
                    'type': 'number',
                    'script': {
                        'params': {'field': 'gnomad_genomes_AF'},
                        'source': mock.ANY,
                    }
                }
            }, 'xpos'])
        self.assertEqual(variants[0]['_sort'][0], 0.00012925741614425127)
        self.assertEqual(variants[1]['_sort'][0], maxsize)

        variants, _ = get_es_variants(results_model, sort='in_omim', num_results=2)
        self.assertExecutedSearch(filters=[ANNOTATION_QUERY], sort=[
            {
                '_script': {
                    'type': 'number',
                    'order': 'desc',
                    'script': {
                        'params': {
                            'omim_gene_ids': ['ENSG00000223972', 'ENSG00000243485', 'ENSG00000268020']
                        },
                        'source': mock.ANY,
                    }
                }
            }, 'xpos'])

    def test_deduplicate_variants(self):
        # Test deduplication works when first variants are build 37 and when they are build 38
        self.assertListEqual(EsSearch._deduplicate_multi_genome_variant_results(
            [PARSED_VARIANTS[1],  PARSED_VARIANTS[1], PARSED_MULTI_GENOME_VERSION_VARIANT]
        ), [PARSED_MULTI_GENOME_VERSION_VARIANT])

        self.assertListEqual(EsSearch._deduplicate_multi_genome_variant_results(
            [PARSED_MULTI_GENOME_VERSION_VARIANT, PARSED_MULTI_GENOME_VERSION_VARIANT, PARSED_VARIANTS[1]]
        ), [PARSED_MULTI_GENOME_VERSION_VARIANT])

    def test_genotype_inheritance_filter(self):
        custom_affected = {'I000004_hg00731': 'N', 'I000005_hg00732': 'A'}
        custom_multi_affected = {'I000005_hg00732': 'A'}

        search_model = VariantSearch.objects.create(search={})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(guid='F000002_2'))
        cache_key = 'search_results__{}__xpos'.format(results_model.guid)

        def _execute_inheritance_search(
                mode=None, inheritance_filter=None, expected_filter=None, expected_comp_het_filter=None,
                dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS, **kwargs):
            _set_cache(cache_key, None)
            annotations = {'frameshift': ['frameshift_variant']} if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS \
                else {'structural': ['DEL']}
            search_model.search = {
                'inheritance': {'mode': mode, 'filter': inheritance_filter},
                'annotations': annotations,
            }
            search_model.save()
            get_es_variants(results_model, num_results=2)

            index = INDEX_NAME if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS else SV_INDEX_NAME
            annotation_query = {'terms': {'transcriptConsequenceTerms': [next(iter(annotations.values()))[0]]}}
            if expected_comp_het_filter:
                self.assertExecutedSearches([
                    dict(sort=['xpos'], gene_aggs=True, start_index=0, size=1, index=index, filters=[
                        annotation_query, {'bool': {'_name': 'F000002_2', 'must': [expected_comp_het_filter]}}
                    ]),
                    dict(sort=['xpos'], start_index=0, size=2, index=index, filters=[
                        annotation_query,  {'bool': {'_name': 'F000002_2', 'must': [expected_filter]}}])
                ])
            else:
                self.assertExecutedSearch(sort=['xpos'], index=index, filters=[
                    annotation_query, {'bool': {'_name': 'F000002_2', 'must': [expected_filter]}}], **kwargs)

        # custom genotype
        _execute_inheritance_search(
            inheritance_filter={'genotype': {'I000004_hg00731': 'ref_ref', 'I000005_hg00732': 'ref_alt'}},
            expected_filter={
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
            })

        # de novo
        _execute_inheritance_search(mode='de_novo', expected_filter={
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
        })

        _execute_inheritance_search(mode='de_novo', dataset_type='SV', expected_filter={'bool': {
                'must_not': [{'term': {'samples': 'HG00732'}}],
                'must': [{'term': {'samples': 'HG00731'}}],
            }
        })

        _execute_inheritance_search(mode='de_novo', inheritance_filter={'affected': custom_affected}, expected_filter={
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
        })

        _execute_inheritance_search(
            mode='de_novo', inheritance_filter={'affected': custom_multi_affected}, expected_filter={'bool': {
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
        })

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
        sv_recessive_filter = {
            'bool': {
                'minimum_should_match': 1,
                'should': [
                    {'term': {'samples_cn_0': 'HG00731'}},
                    {'term': {'samples_cn_2': 'HG00731'}},
                    {'term': {'samples_cn_gte_4': 'HG00731'}},
                ],
                'must': [{
                    'bool': {
                        'minimum_should_match': 1,
                        'should': [
                            {'term': {'samples_cn_1': 'HG00732'}},
                            {'term': {'samples_cn_3': 'HG00732'}},
                    ]}
                }]
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
        _execute_inheritance_search(mode='homozygous_recessive', expected_filter=recessive_filter)

        _execute_inheritance_search(mode='homozygous_recessive', dataset_type='SV', expected_filter=sv_recessive_filter)

        _execute_inheritance_search(
            mode='homozygous_recessive', inheritance_filter={'affected': custom_affected},
            expected_filter=custom_affected_recessive_filter)

        # compound het
        com_het_filter = {
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
        }

        sv_com_het_filter = {'term': {'samples': 'HG00731'}}

        custom_affected_comp_het_filter = {
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
        }

        _execute_inheritance_search(mode='compound_het', expected_filter=com_het_filter, gene_aggs=True, size=1)
        _execute_inheritance_search(
            mode='compound_het', dataset_type='SV', gene_aggs=True, size=1, expected_filter=sv_com_het_filter)
        _execute_inheritance_search(
            mode='compound_het', inheritance_filter={'affected': custom_affected},
            expected_filter=custom_affected_comp_het_filter, gene_aggs=True, size=1)

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

        sv_x_linked_filter = {
            'bool': {
                'minimum_should_match': 1,
                'should': [
                    {'term': {'samples_cn_0': 'HG00731'}},
                    {'term': {'samples_cn_2': 'HG00731'}},
                    {'term': {'samples_cn_gte_4': 'HG00731'}},
                ],
                'must_not': [{'term': {'samples': 'HG00732'}}],
                'must': [{'match': {'contig': 'X'}}],
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

        _execute_inheritance_search(mode='x_linked_recessive', expected_filter=x_linked_filter)

        _execute_inheritance_search(mode='x_linked_recessive', dataset_type='SV', expected_filter=sv_x_linked_filter)

        _execute_inheritance_search(
            mode='x_linked_recessive', inheritance_filter={'affected': custom_affected},
            expected_filter=custom_affected_x_linked_filter)

        # recessive
        _execute_inheritance_search(mode='recessive', expected_comp_het_filter=com_het_filter, expected_filter={
            'bool': {'should': [recessive_filter, x_linked_filter]}
        })

        _execute_inheritance_search(
            mode='recessive', dataset_type='SV', expected_comp_het_filter=sv_com_het_filter, expected_filter={
                'bool': {'should': [sv_recessive_filter, sv_x_linked_filter]}})

        _execute_inheritance_search(
            mode='recessive', inheritance_filter={'affected': custom_affected},
            expected_comp_het_filter=custom_affected_comp_het_filter, expected_filter={
                'bool': {'should': [custom_affected_recessive_filter, custom_affected_x_linked_filter]}})

        # any affected
        _execute_inheritance_search(mode='any_affected', expected_filter={
            'bool': {
                'should': [
                    {'terms': {'samples_num_alt_1': ['HG00731']}},
                    {'terms': {'samples_num_alt_2': ['HG00731']}},
                    {'terms': {'samples': ['HG00731']}},
                ]
            }
        })

        _execute_inheritance_search(
            mode='any_affected', inheritance_filter={'affected': custom_multi_affected}, expected_filter={'bool': {
                'should': [
                    {'terms': {'samples_num_alt_1': ['HG00731', 'HG00732']}},
                    {'terms': {'samples_num_alt_2': ['HG00731', 'HG00732']}},
                    {'terms': {'samples': ['HG00731', 'HG00732']}},
                ]
            }
        })

        # Affected specified with no other inheritance
        with self.assertRaises(Exception) as cm:
            _execute_inheritance_search(inheritance_filter={'affected': custom_affected})
        self.assertEqual(str(cm.exception), 'Inheritance must be specified if custom affected status is set')
