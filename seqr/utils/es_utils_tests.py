from copy import deepcopy
import mock

from django.test import TestCase
from elasticsearch_dsl import Search

from seqr.models import Family, VariantSearch, VariantSearchResults
from seqr.utils.es_utils import get_es_variants_for_variant_tuples, get_single_es_variant, get_es_variants


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

            }
          ]
        },
        'matched_queries': ['F000003_3'],
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
          ]
        },
        'matched_queries': ['F000003_3', 'F000002_2'],
      },
]

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
        'mainTranscript': TRANSCRIPT_3,
        'originalAltAlleles': ['T'],
        'populations': {
            'callset': {'an': 32, 'ac': 2, 'hom': 0, 'af': 0.063, 'hemi': 0},
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
        'projectGuid': 'R0001_1kg',
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
        'familyGuids': ['F000003_3', 'F000002_2'],
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
        'mainTranscript': TRANSCRIPT_1,
        'originalAltAlleles': ['G'],
        'populations': {
            'callset': {'an': 32, 'ac': 1, 'hom': 0, 'af': 0.031, 'hemi': 0}, 
            'g1k': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0}, 
            'gnomad_genomes': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0}, 
            'exac': {'an': 121336, 'ac': 6, 'hom': 0, 'af': 0.000242306760358614, 'hemi': 0}, 
            'gnomad_exomes': {'an': 245714, 'ac': 6, 'hom': 0, 'af': 0.00016269686320447742, 'hemi': 0}, 
            'topmed': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0}
        }, 
        'pos': 103343353, 
        'predictions': {'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None, 'polyphen': None, 'dann': None, 'sift': None, 'cadd': 17.26, 'metasvm': None, 'primate_ai': None, 'gerp_rs': None, 'mpc': None, 'phastcons_100_vert': None}, 
        'projectGuid': 'R0001_1kg',
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


SOURCE_FIELDS = {
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
    'clinvar_clinical_significance',
    'clinvar_allele_id',
    'clinvar_variation_id',
    'clinvar_gold_stars',
    'hgmd_accession',
    'hgmd_class',
    'AC',
    'callset_AC',
    'callset_Hom',
    'callset_Hemi',
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
    'topmed_AN'
}

ALL_INHERITANCE_QUERY = {
    "bool": {
        "should": [
            {"bool": {
                "must": [
                    {"bool": {"should": [
                        {"terms": {"samples_num_alt_1": ["NA20870"]}},
                        {"terms": {"samples_num_alt_2": ["NA20870"]}}
                    ]}}
                ],
                "_name": "F000003_3"
            }},
            {"bool": {
                "must": [
                    {"bool": {"should": [
                        {"terms": {"samples_num_alt_1": ["HG00731", "HG00732", "HG00733"]}},
                        {"terms": {"samples_num_alt_2": ["HG00731", "HG00732", "HG00733"]}}
                    ]}}
                ],
                "_name": "F000002_2"
            }},
        ]
    }
}


class MockHit:

    def __init__(self, matched_queries=[], _source={}, increment_sort=False):
        self.meta = mock.MagicMock()
        self.meta.matched_queries = matched_queries
        sort = _source['xpos']
        if increment_sort:
            sort += 100
        self.meta.sort = [sort]
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


MOCK_ES_RESPONSE = mock.MagicMock()
MOCK_ES_RESPONSE.__iter__.return_value = [MockHit(**var) for var in deepcopy(ES_VARIANTS)]
MOCK_ES_RESPONSE.hits.total = 5
MOCK_ES_RESPONSE.aggregations.genes.buckets = [
    {'key': 'ENSG00000135953', 'vars_by_gene': [MockHit(increment_sort=True, **var) for var in deepcopy(ES_VARIANTS)]},
    {'key': 'ENSG00000228198', 'vars_by_gene': [MockHit(increment_sort=True, **var) for var in deepcopy(ES_VARIANTS)]}
]


@mock.patch('seqr.utils.es_utils.is_nested_genotype_index', lambda *args: True)
class EsUtilsTest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data']

    def setUp(self):
        self.families = Family.objects.filter(guid__in=['F000003_3', 'F000002_2'])

        # Mock the execute search method without changing the rest of the Search DSL
        self.executed_searches = []

        class MockSearch(Search):

            def execute(_self):
                self.executed_searches.append(deepcopy(_self.to_dict()))
                return MOCK_ES_RESPONSE

        self.mock_search = MockSearch()

        patcher = mock.patch('seqr.utils.es_utils.Search')
        self.mock_create_search = patcher.start()
        self.mock_create_search.return_value = self.mock_search

        self.addCleanup(patcher.stop)

    def assertExecutedSearches(self, searches):
        self.mock_create_search.assert_called_with(using=mock.ANY, index='test_index')
        self.assertEqual(len(self.executed_searches), len(searches))
        for i, executed_search in enumerate(self.executed_searches):
            expected_search = {
                'query': {
                    'bool': {
                        'filter': searches[i]['filters']
                    }
                },
                'from': searches[i]['start_index'],
                'size': searches[i]['size']
            }

            if searches[i].get('aggs'):
                aggs = searches[i]['aggs']
                expected_search['aggs'] = {
                    aggs['name']: {'terms': aggs['terms'], 'aggs': {
                        aggs['nested_name']: {
                            'top_hits': {'sort': searches[i]['sort'], '_source': mock.ANY, 'size': aggs['nested_size']}
                        }
                    }}}
            else:
                expected_search['_source'] = mock.ANY
                if searches[i].get('sort'):
                    expected_search['sort'] = searches[i]['sort']
            self.assertDictEqual(executed_search, expected_search)
            source = executed_search['aggs'][aggs['name']]['aggs'][aggs['nested_name']]['top_hits']['_source'] \
                if searches[i].get('aggs') else executed_search['_source']
            self.assertSetEqual(SOURCE_FIELDS, set(source))

        self.executed_searches = []

    def assertExecutedSearch(self, filters=[], start_index=0, size=2, sort=None):
        self.assertExecutedSearches([dict(filters=filters, start_index=start_index, size=size, sort=sort)])

    def test_get_es_variants_for_variant_tuples(self):
        variants = get_es_variants_for_variant_tuples(
            self.families,
            [(2103343353, 'GAGA', 'G'), (1248367227, 'TC', 'T')]
        )

        self.assertEqual(len(variants), 2)
        self.assertDictEqual(variants[0], PARSED_VARIANTS[0])
        self.assertDictEqual(variants[1], PARSED_VARIANTS[1])

        self.assertExecutedSearch(
            filters=[{'terms': {'variantId': ['2-103343353-GAGA-G', '1-248367227-TC-T']}}, ALL_INHERITANCE_QUERY],
        )

    def test_get_single_es_variant(self):
        variant = get_single_es_variant(self.families, '2-103343353-GAGA-G')
        self.assertDictEqual(variant, PARSED_VARIANTS[0])
        self.assertExecutedSearch(
            filters=[{'term': {'variantId': '2-103343353-GAGA-G'}}, ALL_INHERITANCE_QUERY], size=1
        )

    def test_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={})
        results_model = VariantSearchResults.objects.create(variant_search=search_model, sort='xpos')
        results_model.families = self.families
        results_model.save()

        variants = get_es_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertDictEqual(variants[0], PARSED_VARIANTS[0])
        self.assertDictEqual(variants[1], PARSED_VARIANTS[1])

        self.assertDictEqual(results_model.results, {'all_results': variants})
        self.assertEqual(results_model.es_index, 'test_index')
        self.assertEqual(results_model.total_results, 5)

        self.assertExecutedSearch(filters=[ALL_INHERITANCE_QUERY], sort=['xpos'])

        # test pagination
        variants = get_es_variants(results_model, page=2, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertDictEqual(results_model.results, {'all_results':  PARSED_VARIANTS + PARSED_VARIANTS})
        self.assertExecutedSearch(filters=[ALL_INHERITANCE_QUERY], sort=['xpos'], start_index=2, size=2)

        # test fetch partial page
        get_es_variants(results_model, page=2, num_results=3)
        self.assertExecutedSearch(filters=[ALL_INHERITANCE_QUERY], sort=['xpos'], start_index=4, size=1)

        # test does not re-fetch page
        variants = get_es_variants(results_model, page=1, num_results=3)
        self.assertEqual(len(self.executed_searches), 0)
        self.assertEqual(len(variants), 3)
        self.assertListEqual(variants, results_model.results['all_results'][0:3])

    def test_filtered_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'locus': {'rawItems': 'DDX11L1, chr2:1234-5678'},
            'pathogenicity': {
                'clinvar': ["pathogenic", "likely_pathogenic"],
                'hgmd': ["disease_causing", 'likely_disease_causing'],
            },
            'annotations': {
                'in_frame': ["inframe_insertion", "inframe_deletion"],
                'other': ["5_prime_UTR_variant", 'intergenic_variant'],
            },
            'freqs': {
                'callset': {'af': 0.1},
                'exac': {'ac': 2},
                'g1k': {'ac': None, 'af': 0.001},
                'gnomad_exomes': {'ac': 3, 'hh': 3},
                'gnomad_genomes': {'af': 0.01, 'hh': 3},
                'topmed': {'ac': 2, 'af': None},
            },
            "qualityFilter": {"min_ab": 10, "min_gq": 15, "vcf_filter": "pass"},
            "inheritance": {"mode": "de_novo"}
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model, sort='in_omim')
        results_model.families = self.families
        results_model.save()

        variants = get_es_variants(results_model, num_results=2)
        self.assertListEqual(variants, PARSED_VARIANTS)

        self.assertExecutedSearch(filters=[
            {
                "bool": {
                    "should": [
                        {"range": {"xpos": {"gte": 2000001234, "lte": 2000005678}}},
                        {"terms": {"geneIds": ["ENSG00000223972"]}}
                    ]
                }
            },
            {
                "bool": {
                    "should": [
                        {"terms": {
                            "clinvar_clinical_significance": [
                                "Pathogenic", "Likely_pathogenic", "Pathogenic/Likely_pathogenic"
                            ]
                        }},
                        {"terms": {"hgmd_class": ["DM", "DM?"]}},
                        {"bool": {"must_not": [{"exists": {"field": "transcriptConsequenceTerms"}}]}},
                        {"terms": {
                            "transcriptConsequenceTerms": [
                                "5_prime_UTR_variant",
                                "intergenic_variant",
                                "inframe_insertion",
                                "inframe_deletion",
                            ]
                        }}
                    ]
                }
            },
            {
                "bool": {
                    "minimum_should_match": 1,
                    "should": [
                        {"bool": {"must_not": [{"exists": {"field": "AF"}}]}},
                        {"range": {"AF": {"lte": 0.1}}}
                    ],
                    "must": [
                        {"bool": {
                            "minimum_should_match": 1,
                            "should": [
                                {"bool": {"must_not": [{"exists": {"field": "g1k_POPMAX_AF"}}]}},
                                {"range": {"g1k_POPMAX_AF": {"lte": 0.001}}}
                            ]
                        }},
                        {"bool": {
                            "minimum_should_match": 1,
                            "should": [
                                {"bool": {"must_not": [{"exists": {"field": "gnomad_genomes_AF_POPMAX_OR_GLOBAL"}}]}},
                                {"range": {"gnomad_genomes_AF_POPMAX_OR_GLOBAL": {"lte": 0.01}}}
                            ]
                        }},
                        {"bool": {
                            "minimum_should_match": 1,
                            "should": [
                                {"bool": {"must_not": [{"exists": {"field": "gnomad_genomes_Hom"}}]}},
                                {"range": {"gnomad_genomes_Hom": {"lte": 3}}}
                            ]
                        }},
                        {"bool": {
                            "minimum_should_match": 1,
                            "should": [
                                {"bool": {"must_not": [{"exists": {"field": "gnomad_genomes_Hemi"}}]}},
                                {"range": {"gnomad_genomes_Hemi": {"lte": 3}}}
                            ]}
                        },
                        {"bool": {
                            "minimum_should_match": 1,
                            "should": [
                                {"bool": {"must_not": [{"exists": {"field": "gnomad_exomes_AC"}}]}},
                                {"range": {"gnomad_exomes_AC": {"lte": 3}}}
                            ]
                        }},
                        {"bool": {
                            "minimum_should_match": 1,
                            "should": [
                                {"bool": {"must_not": [{"exists": {"field": "gnomad_exomes_Hom"}}]}},
                                {"range": {"gnomad_exomes_Hom": {"lte": 3}}}
                            ]
                        }},
                        {"bool": {
                            "minimum_should_match": 1,
                            "should": [
                                {"bool": {"must_not": [{"exists": {"field": "gnomad_exomes_Hemi"}}]}},
                                {"range": {"gnomad_exomes_Hemi": {"lte": 3}}}
                            ]}
                        },
                        {"bool": {
                            "minimum_should_match": 1,
                            "should": [
                                {"bool": {"must_not": [{"exists": {"field": "exac_AC_Adj"}}]}},
                                {"range": {"exac_AC_Adj": {"lte": 2}}}
                            ]}
                        },
                        {"bool": {
                            "minimum_should_match": 1,
                            "should": [
                                {"bool": {"must_not": [{"exists": {"field": "topmed_AC"}}]}},
                                {"range": {"topmed_AC": {"lte": 2}}}
                            ]}
                        }
                    ]
                }
            },
            {"bool": {
                "minimum_should_match": 1,
                "must_not": [{"exists": {"field": "filters"}}],
                "should": [
                    {"bool": {
                        "must": [
                            {"bool": {"should": [
                                {"term": {"samples_num_alt_1": "NA20870"}},
                                {"term": {"samples_num_alt_2": "NA20870"}}
                            ]}},
                            {"bool": {
                                "minimum_should_match": 1,
                                "should": [
                                    {"bool": {
                                        "must_not": [
                                            {"term": {"samples_ab_0_to_5": "NA20870"}},
                                            {"term": {"samples_ab_5_to_10": "NA20870"}},
                                        ]
                                    }},
                                    {"bool": {"must_not": [{"term": {"samples_num_alt_1": "NA20870"}}]}}
                                ],
                                "must_not": [
                                    {"term": {"samples_gq_0_to_5": "NA20870"}},
                                    {"term": {"samples_gq_5_to_10": "NA20870"}},
                                    {"term": {"samples_gq_10_to_15": "NA20870"}},
                                ]
                            }}
                        ],
                        "_name": "F000003_3"
                    }},
                    {"bool": {
                        "must": [
                            {"bool": {
                                "minimum_should_match": 1,
                                "must_not": [
                                    {"term": {"samples_no_call": "HG00732"}},
                                    {"term": {"samples_num_alt_1": "HG00732"}},
                                    {"term": {"samples_num_alt_2": "HG00732"}},
                                    {"term": {"samples_no_call": "HG00733"}},
                                    {"term": {"samples_num_alt_1": "HG00733"}},
                                    {"term": {"samples_num_alt_2": "HG00733"}}
                                ],
                                "should": [
                                    {"term": {"samples_num_alt_1": "HG00731"}},
                                    {"term": {"samples_num_alt_2": "HG00731"}}
                                ]
                            }},
                            {"bool": {
                                "minimum_should_match": 1,
                                "should": [
                                    {"bool": {
                                        "must_not": [
                                            {"term": {"samples_ab_0_to_5": "HG00731"}},
                                            {"term": {"samples_ab_5_to_10": "HG00731"}},
                                        ]
                                    }},
                                    {"bool": {"must_not": [{"term": {"samples_num_alt_1": "HG00731"}}]}}
                                ],
                                "must_not": [
                                    {"term": {"samples_gq_0_to_5": "HG00731"}},
                                    {"term": {"samples_gq_5_to_10": "HG00731"}},
                                    {"term": {"samples_gq_10_to_15": "HG00731"}},
                                    {"term": {"samples_gq_0_to_5": "HG00732"}},
                                    {"term": {"samples_gq_5_to_10": "HG00732"}},
                                    {"term": {"samples_gq_10_to_15": "HG00732"}},
                                    {"term": {"samples_gq_0_to_5": "HG00733"}},
                                    {"term": {"samples_gq_5_to_10": "HG00733"}},
                                    {"term": {"samples_gq_10_to_15": "HG00733"}},
                                ],
                                "must": [
                                    {"bool": {
                                        "minimum_should_match": 1,
                                        "should": [
                                            {"bool": {
                                                "must_not": [
                                                    {"term": {"samples_ab_0_to_5": "HG00732"}},
                                                    {"term": {"samples_ab_5_to_10": "HG00732"}},
                                                ]
                                            }},
                                            {"bool": {"must_not": [{"term": {"samples_num_alt_1": "HG00732"}}]}}
                                        ]
                                    }},
                                    {"bool": {
                                        "minimum_should_match": 1,
                                        "should": [
                                            {"bool": {
                                                "must_not": [
                                                    {"term": {"samples_ab_0_to_5": "HG00733"}},
                                                    {"term": {"samples_ab_5_to_10": "HG00733"}},
                                                ]
                                            }},
                                            {"bool": {"must_not": [{"term": {"samples_num_alt_1": "HG00733"}}]}}
                                        ]
                                    }},
                                ]
                            }}
                        ],
                        "_name": "F000002_2"
                    }},
                ]
            }}
        ], sort=[{
            '_script': {
                'type': 'number',
                'script': {
                    'params': {
                        'omim_gene_ids': ['ENSG00000223972', 'ENSG00000243485', 'ENSG00000268020']
                    },
                    'source': "params.omim_gene_ids.contains(doc['mainTranscript_gene_id'].value) ? 0 : 1"
                }
            }
        }, 'xpos'])

    def test_recessive_get_es_variants(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {"frameshift": ["frameshift_variant"]},
            "inheritance": {"mode": "recessive"}
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model, sort='xpos')
        results_model.families = self.families
        results_model.save()

        variants = get_es_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 3)
        self.assertDictEqual(variants[0], PARSED_VARIANTS[0])
        self.assertDictEqual(variants[1], PARSED_COMPOUND_HET_VARIANTS[0])
        self.assertDictEqual(variants[2], PARSED_COMPOUND_HET_VARIANTS[1])

        self.assertDictEqual(results_model.results, {
            'compound_het_results': [PARSED_COMPOUND_HET_VARIANTS],
            'variant_results': PARSED_VARIANTS,
            'all_results': [PARSED_VARIANTS[0]] + PARSED_COMPOUND_HET_VARIANTS
        })
        self.assertEqual(results_model.total_results, 7)

        annotation_query = {"terms": {"transcriptConsequenceTerms": ["frameshift_variant"]}}
        recessive_inheritance_query = {
            'bool': {
                'should': [
                    {'bool': {
                        '_name': 'F000003_3',
                        'must': [
                            {'bool': {
                                'should': [
                                    {'bool': {
                                        'must': [{'match': {'contig': 'X'}}, {'term': {'samples_num_alt_2': 'NA20870'}}]
                                    }},
                                    {'term': {'samples_num_alt_2': 'NA20870'}}
                                ]
                            }}
                        ]
                    }},
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
                                            {'term': {'samples_num_alt_2': 'HG00732'}},
                                            {'term': {'samples_no_call': 'HG00733'}},
                                            {'term': {'samples_num_alt_1': 'HG00733'}},
                                            {'term': {'samples_num_alt_2': 'HG00733'}}
                                        ],
                                        'must': [{'match': {'contig': 'X'}}, {'term': {'samples_num_alt_2': 'HG00731'}}]
                                    }}
                                ]
                            }}
                        ]
                    }}
                ]
            }
        }

        compound_het_inheritance_query = {
            'bool': {
                'should': [
                    {'bool': {
                        '_name': 'F000003_3',
                        'must': [{'term': {'samples_num_alt_1': 'NA20870'}}]
                    }},
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
                            }}
                        ]
                    }}
                ]
            }
        }

        self.assertExecutedSearches([
            dict(filters=[annotation_query, recessive_inheritance_query], start_index=0, size=2, sort=['xpos']),
            dict(
                filters=[annotation_query, compound_het_inheritance_query],
                aggs={
                    'name': 'genes', 'terms': {'field': 'geneIds', 'min_doc_count': 2, 'size': 10000},
                    'nested_name': 'vars_by_gene', 'nested_size': 100,
                },
                sort=['xpos'],
                start_index=0,
                size=0
            )
        ])

        # test pagination (skip page)

    def test_genotype_filter(self):
        # TODO test custom genotype filters
        pass
