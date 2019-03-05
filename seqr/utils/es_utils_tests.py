from copy import deepcopy
import mock

from django.test import TestCase
from elasticsearch_dsl import Search

from seqr.models import Family
from seqr.utils.es_utils import get_es_variants_for_variant_tuples, get_single_es_variant, get_es_variants


ES_VARIANTS = [
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
                'sample_id': 'NA19675',
            },
            {
                'num_alt': 0,
                'ab': 0,
                'dp': 67,
                'gq': 99,
                'sample_id': 'HG00731',
            }
          ]
        },
        'matched_queries': ['F000001_1', 'F000002_2'],
      },
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
              'major_consequence': 'inframe_deletion',
              'consequence_terms': [
                'inframe_deletion',
                'NMD_transcript_variant'
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
              'sample_id': 'NA19675',
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
        'matched_queries': ['F000001_1'],
      }
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
  'majorConsequence': 'inframe_deletion',
  'consequenceTerms': [
    'inframe_deletion',
    'NMD_transcript_variant'
  ]
}

PARSED_VARIANTS = [
    {
        'alt': 'G',
        'chrom': '2',
        'clinvar': {'clinicalSignificance': None, 'alleleId': None, 'variationId': None, 'goldStars': None},
        'familyGuids': ['F000001_1', 'F000002_2'],
        'genotypes': {
            'I000004_hg00731': {'ab': 0, 'ad': None, 'gq': 99, 'sampleId': 'HG00731', 'numAlt': 0, 'dp': 67, 'pl': None},
            'I000001_na19675': {'ab': 0.70212764, 'ad': None, 'gq': 46, 'sampleId': 'NA19675', 'numAlt': 1, 'dp': 50, 'pl': None}
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
        '_sort': [],
    }, 
    {
        'alt': 'T',
        'chrom': '1',
        'clinvar': {'clinicalSignificance': None, 'alleleId': None, 'variationId': None, 'goldStars': None},
        'familyGuids': ['F000001_1'],
        'genotypes': {
            'I000001_na19675': {'ab': 1, 'ad': None, 'gq': 99, 'sampleId': 'NA19675', 'numAlt': 2, 'dp': 74, 'pl': None}
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
        'predictions': {'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None, 'polyphen': None, 'dann': None, 'sift': None, 'cadd': 25.9, 'metasvm': None, 'primate_ai': None, 'gerp_rs': None, 'mpc': None, 'phastcons_100_vert': None},
        'projectGuid': 'R0001_1kg',
        'ref': 'TC',
        'rsid': None,
        'transcripts': {
            'ENSG00000135953': [TRANSCRIPT_3]
        },
        'variantId': '1-248367227-TC-T',
        'xpos': 1248367227,
        '_sort': [],
    }
]

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
            {
                "bool": {
                    "must": [
                        {
                            "bool": {
                                "should": [
                                    {
                                        "terms": {
                                            "samples_num_alt_1": [
                                                "HG00731"
                                            ]
                                        }
                                    },
                                    {
                                        "terms": {
                                            "samples_num_alt_2": [
                                                "HG00731"
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    "_name": "F000002_2"
                }
            },
            {
                "bool": {
                    "must": [
                        {
                            "bool": {
                                "should": [
                                    {
                                        "terms": {
                                            "samples_num_alt_1": [
                                                "NA19675"
                                            ]
                                        }
                                    },
                                    {
                                        "terms": {
                                            "samples_num_alt_2": [
                                                "NA19675"
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    "_name": "F000001_1"
                }
            }
        ]
    }
}


class MockHit:

    def __init__(self, matched_queries=[], _source={}):
        self.meta = mock.MagicMock()
        self.meta.matched_queries = matched_queries
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
MOCK_ES_RESPONSE.__iter__.return_value = [MockHit(**var) for var in ES_VARIANTS]


@mock.patch('seqr.utils.es_utils.is_nested_genotype_index', lambda *args: True)
class EsUtilsTest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data']

    def setUp(self):
        self.families = Family.objects.filter(guid__in=['F000001_1', 'F000002_2'])

        # Mock the execute search method without changing the rest of the Search DSL
        self.executed_search = None

        class MockSearch(Search):

            def execute(_self):
                self.executed_search = deepcopy(_self.to_dict())
                return MOCK_ES_RESPONSE

        self.mock_search = MockSearch()

        patcher = mock.patch('seqr.utils.es_utils.Search')
        self.mock_create_search = patcher.start()
        self.mock_create_search.return_value = self.mock_search

        self.addCleanup(patcher.stop)

    def assertExecutedSearch(self, filters=[], size=100):
        self.mock_create_search.assert_called_with(using=mock.ANY, index='test_index')
        self.assertDictEqual(self.executed_search, {
            'query': {
                'bool': {
                    'filter': filters
                }
            },
            '_source': mock.ANY,
            'from': 0,
            'size': size
        })
        self.assertSetEqual(SOURCE_FIELDS, set(self.executed_search['_source']))

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
            size=2
        )

    def test_get_single_es_variant(self):
        variant = get_single_es_variant(self.families, '2-103343353-GAGA-G')

        self.assertDictEqual(variant, PARSED_VARIANTS[0])

        self.assertExecutedSearch(
            filters=[{'term': {'variantId': '2-103343353-GAGA-G'}}, ALL_INHERITANCE_QUERY], size=1
        )
