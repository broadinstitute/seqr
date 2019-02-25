import json
import mock
from copy import deepcopy

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
                'hmmpanther:PTHR24003',
                'hmmpanther:PTHR24003',
                'Pfam_domain:PF07690',
                'Gene3D:1',
                'Superfamily_domains:SSF103473',
                'Prints_domain:PR01035'
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
                'Superfamily_domains:SSF103473',
                'Pfam_domain:PF07690',
                'hmmpanther:PTHR24003',
                'hmmpanther:PTHR24003',
                'PROSITE_profiles:PS50850'
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
            },
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
          'gnomad_genomes_AC': None
        },
        'inner_hits': {
          'F000001_1': {
            'hits': {
              'total': 1,
              'max_score': 1,
              'hits': [
                {
                  '_index': '1kg-test--nested-vep--named-parent-child-genotypes',
                  '_type': 'variant',
                  '_id': 'eUVSUWcBABSXPvgQOpHb',
                  '_score': 1,
                  '_routing': '2-103343353-GAGA-G',
                  '_source': {
                    'num_alt': 1,
                    'ab': 0.70212764,
                    'dp': 50,
                    'gq': 46,
                    'sample_id': 'NA19675',
                    'join_field': {
                      'name': 'genotype',
                      'parent': '2-103343353-GAGA-G'
                    }
                  }
                }
              ]
            }
          },
          'F000002_2': {
            'hits': {
              'total': 1,
              'max_score': 0,
              'hits': [
                {
                  '_index': '1kg-test--nested-vep--named-parent-child-genotypes',
                  '_type': 'variant',
                  '_id': 'dkVSUWcBABSXPvgQOpHb',
                  '_score': 0,
                  '_routing': '2-103343353-GAGA-G',
                  '_source': {
                    'num_alt': 0,
                    'ab': 0,
                    'dp': 67,
                    'gq': 99,
                    'sample_id': 'HG00731',
                    'join_field': {
                      'name': 'genotype',
                      'parent': '2-103343353-GAGA-G'
                    }
                  }
                }
              ]
            }
          }
        }
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
                'Prints_domain:PR00245',
                'Superfamily_domains:SSF81321',
                'Gene3D:1',
                'hmmpanther:PTHR26453',
                'hmmpanther:PTHR26453',
                'PROSITE_profiles:PS50262'
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
          'gnomad_genomes_AC': 4
        },
        'inner_hits': {
          'F000001_1': {
            'hits': {
              'total': 1,
              'max_score': 2,
              'hits': [
                {
                  '_index': '1kg-test--nested-vep--named-parent-child-genotypes',
                  '_type': 'variant',
                  '_id': 'kWdSUWcB6VBPRCrIgviP',
                  '_score': 2,
                  '_routing': '1-248367227-TC-T',
                  '_source': {
                    'num_alt': 2,
                    'ab': 1,
                    'dp': 74,
                    'gq': 99,
                    'sample_id': 'NA19675',
                    'join_field': {
                      'name': 'genotype',
                      'parent': '1-248367227-TC-T'
                    }
                  }
                }
              ]
            }
          },
          'F000002_2': {
            'hits': {
              'total': 1,
              'max_score': 0,
              'hits': [
                {
                  '_index': '1kg-test--nested-vep--named-parent-child-genotypes',
                  '_type': 'variant',
                  '_id': 'jmdSUWcB6VBPRCrIgviP',
                  '_score': 0,
                  '_routing': '1-248367227-TC-T',
                  '_source': {
                    'num_alt': 0,
                    'ab': 0,
                    'dp': 88,
                    'gq': 99,
                    'sample_id': 'HG00731',
                    'join_field': {
                      'name': 'genotype',
                      'parent': '1-248367227-TC-T'
                    }
                  }
                }
              ]
            }
          }
        }
      }
    ]


class MockSearch(Search):

    def execute(self):
        return MOCK_ES_RESPONSE


class MockHit:

    def __init__(self, inner_hits={}, _source={}):
        self.meta = mock.MagicMock()
        self.meta.inner_hits = {}
        for key, hit in inner_hits.items():
            self.meta.inner_hits[key] = mock.MagicMock()
            for k, v in hit['hits'].items():
                setattr(self.meta.inner_hits[key].hits, k, v)
            self.meta.inner_hits[key].__iter__.return_value = [hit['_source'] for hit in self.meta.inner_hits[key].hits.hits]
        self._dict = _source

    def __getitem__(self, key):
        return self._dict[key]

    def __iter__(self):
        return self._dict.__iter__()


MOCK_ES_RESPONSE = mock.MagicMock()
MOCK_ES_RESPONSE.__iter__.return_value = [MockHit(**var) for var in ES_VARIANTS]


class EsUtilsTest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data']

    @mock.patch('seqr.utils.es_utils.is_nested_genotype_index', lambda *args: True)
    @mock.patch('seqr.utils.es_utils.Search')
    def test_get_es_variants_for_variant_tuples(self, mock_create_search):
        # Mock the execute search method without changing the rest of the Search DSL
        stubbed_search = MockSearch()
        mock_create_search.return_value = stubbed_search

        variants = get_es_variants_for_variant_tuples(
            Family.objects.filter(guid__in=['F000001_1', 'F000002_2']),
            [(2103343353, 'GAGA', 'G'), (1248367227, 'TC', 'T')]
        )
        import pdb; pdb.set_trace()

        mock_create_search.assert_called_with(using=mock.ANY, index='test_index')
        self.assertDictEqual(stubbed_search.to_dict(), {
            'query': {
                'bool': {
                    'filter': [
                        {
                            'terms': {
                                'variantId': [
                                    '2-103343353-GAGA-G',
                                    '1-248367227-TC-T'
                                ]
                            }
                        },
                        {
                            'bool': {
                                'minimum_should_match': 1,
                                'should': [
                                    {
                                        'has_child': {
                                            'query': {
                                                'function_score': {
                                                    'query': {
                                                        'terms': {
                                                            'sample_id': [
                                                                'HG00731'
                                                            ]
                                                        }
                                                    },
                                                    'functions': [
                                                        {
                                                            'field_value_factor': {
                                                                'field': 'num_alt'
                                                            }
                                                        }
                                                    ]
                                                }
                                            },
                                            'inner_hits': {
                                                'name': 'F000002_2'
                                            },
                                            'type': 'genotype',
                                            'min_children': 1
                                        }
                                    },
                                    {
                                        'has_child': {
                                            'query': {
                                                'function_score': {
                                                    'query': {
                                                        'terms': {
                                                            'sample_id': [
                                                                'NA19675'
                                                            ]
                                                        }
                                                    },
                                                    'functions': [
                                                        {
                                                            'field_value_factor': {
                                                                'field': 'num_alt'
                                                            }
                                                        }
                                                    ]
                                                }
                                            },
                                            'inner_hits': {
                                                'name': 'F000001_1'
                                            },
                                            'type': 'genotype',
                                            'min_children': 1
                                        }
                                    }
                                ],
                                'must': [
                                    {
                                        'has_child': {
                                            'query': {
                                                'bool': {
                                                    'must': [
                                                        {
                                                            'range': {
                                                                'num_alt': {
                                                                    'gte': 1
                                                                }
                                                            }
                                                        },
                                                        {
                                                            'terms': {
                                                                'sample_id': [
                                                                    'HG00731',
                                                                    'NA19675'
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            },
                                            'type': 'genotype'
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            },
            '_source': mock.ANY,
            'from': 0,
            'size': 2
        })

