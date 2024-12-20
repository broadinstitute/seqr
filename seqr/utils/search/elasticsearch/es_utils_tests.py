from copy import deepcopy
import mock
import jmespath
import json
import re
from collections import defaultdict
from datetime import timedelta
from django.test import TestCase
from elasticsearch.exceptions import ConnectionTimeout, TransportError
from sys import maxsize
from urllib3.exceptions import ReadTimeoutError
from urllib3_mock import Responses

from seqr.models import Project, Family, Sample, VariantSearch, VariantSearchResults
from seqr.utils.search.utils import get_single_variant, query_variants, \
    get_variant_query_gene_counts, get_variants_for_variant_ids, InvalidSearchException
from seqr.utils.search.elasticsearch.es_search import _get_family_affected_status, _liftover_grch38_to_grch37
from seqr.utils.search.elasticsearch.es_utils import InvalidIndexException
from seqr.views.utils.test_utils import PARSED_VARIANTS, PARSED_SV_VARIANT, PARSED_SV_WGS_VARIANT,\
    PARSED_MITO_VARIANT, TRANSCRIPT_2, PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT


# The responses library for mocking requests does not work with urllib3 (which is used by elasticsearch)
# The urllib3_mock library works for those requests, but it has limited functionality, so this extension adds helper
# methods for easier usage
class Urllib3Responses(Responses):
    def add_json(self, url, json_response, method=None, match_querystring=True, **kwargs):
        if not method:
            method = self.GET
        body = json.dumps(json_response)
        self.add(method, url, match_querystring=match_querystring, content_type='application/json', body=body, **kwargs)

    def replace_json(self, url, *args, **kwargs):
        existing_index = next(i for i, match in enumerate(self._urls) if match['url'] == url)
        self.add_json(url, *args, **kwargs)
        self._urls[existing_index] = self._urls.pop()

    def call_request_json(self, index=-1):
        return json.loads(self.calls[index].request.body)


urllib3_responses = Urllib3Responses()


INDEX_NAME = 'test_index'
SECOND_INDEX_NAME = 'test_index_second'
HG38_INDEX_NAME = 'test_index_hg38'
SV_INDEX_NAME = 'test_index_sv'
SV_WGS_INDEX_NAME = 'test_index_sv_wgs'
MITO_WGS_INDEX_NAME = 'test_index_mito_wgs'
INDEX_ALIAS = '377e97bd791cf92a78296bc184e0976a'
ALIAS_MAP = {INDEX_ALIAS: ','.join([INDEX_NAME, SECOND_INDEX_NAME, SV_INDEX_NAME, MITO_WGS_INDEX_NAME])}
SUB_INDICES = ['sub_index_1', 'sub_index_2']
SECOND_SUB_INDICES = ['sub_index_a', 'sub_index_b']

ES_VARIANTS = [
    {
        '_source': {
          'homozygote_count': 3,
          'gnomad_exomes_Hemi': None,
          'originalAltAlleles': [
            '1-248367227-TC-T'
          ],
          'hgmd_accession': None,
          'g1k_AF': None,
          'gnomad_genomes_Hom': 0,
          'cadd_PHRED': '25.9',
          'splice_ai_delta_score': 0.75,
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
          'dbnsfp_VEST4_score': '0.335;0.341;0.38',
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
          'screen_region_type' : [
            'dELS',
            'CTCF-bound'
          ],
          'gnomad_non_coding_constraint_z_score': 1.01272,
          'hgmd_class': 'DM',
          'AC': 2,
          'exac_AN_Adj': 121308,
          'mpc_MPC': None,
          'AF': 0.063,
          'alt': 'T',
          'clinvar_clinical_significance': 'Pathogenic/Likely_pathogenic',
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
          'dbnsfp_FATHMM_pred': 'T',
          'dbnsfp_fathmm_MKL_coding_pred': 'D',
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
          'dbnsfp_VEST4_score': '.;.;.;.',
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
                'num_alt': 2,
                'ab': 0,
                'dp': 67,
                'gq': 99,
                'sample_id': 'HG00731',
            },
            {
                'num_alt': 1,
                'ab': 0,
                'dp': 42,
                'gq': 96,
                'sample_id': 'HG00732',
            },
            {
                'num_alt': 0,
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
BUILD_38_NO_LIFTOVER_ES_VARIANT = deepcopy(ES_VARIANTS[1])
BUILD_38_NO_LIFTOVER_ES_VARIANT['_source'].update({
    'start': 103343363,
    'xpos': 2103343363,
    'variantId': '2-103343363-GAGA-G'
})
BUILD_38_ES_VARIANT = deepcopy(BUILD_38_NO_LIFTOVER_ES_VARIANT)
BUILD_38_ES_VARIANT['_source']['rg37_locus'] = {'contig': '2', 'position': 103343353}

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
          'geneIds': ['ENSG00000228198'],
          'prev_call': False,
          'prev_overlap': False,
          'new_call': True,
        },
        {
          'qs': 80,
          'cn': 2,
          'defragged': False,
          'sample_id': 'HG00733',
          'num_exon': 1,
          'start': 49045987,
          'end': 49045890,
          'geneIds': ['ENSG00000228198', 'ENSG00000135953'],
          'prev_call': False,
          'prev_overlap': True,
          'new_call': False,
        }
      ],
      'xpos': 1049045387,
      'end': 49045898,
      'start': 49045387,
      'xstart': 1049045587,
      'num_exon': 1,
      'pos': 49045487,
      'StrVCTVRE_score': 0.374,
      'svType': 'INS',
      'xstop': 9049045898,
      'variantId': 'prefix_19107_DEL',
      'samples': ['HG00731'],
      'sc': 7,
      'contig': '1',
      'bothsides_support': True,
      'sortedTranscriptConsequences': [
        {
          'gene_id': 'ENSG00000228198'
        },
        {
          'gene_id': 'ENSG00000135953'
        },
        {
          'gene_id': 'ENSG00000186092'
        },
      ],
      'geneIds': ['ENSG00000228198'],
      'sf': 0.000693825,
      'sn': 10088
    },
    'matched_queries': {SV_INDEX_NAME: ['F000002_2']},
  }

ES_SV_WGS_VARIANT = {
    '_source': {
      'genotypes': [
        {
          'gq': 33,
          'sample_id': 'NA21234',
          'num_alt': 1,
          'prev_num_alt': 2,
        }
      ],
      'xpos': 2049045387,
      'end': 49045898,
      'start': 49045387,
      'xstart': 2049045387,
      'pos': 49045387,
      'svType': 'CPX',
      'xstop': 20012345678,
      'variantId': 'prefix_19107_CPX',
      'algorithms': ['wham', 'manta'],
      'sc': 7,
      'contig': '2',
      'rg37_locus': {'contig': '2', 'position': 49272526},
      'rg37_locus_end': {'contig': '20', 'position': 12326326},
      'sortedTranscriptConsequences': [
        {
          'gene_symbol': 'OR4F5',
          'major_consequence': 'DUP_PARTIAL',
          'gene_id': 'ENSG00000228198'
        },
        {
            'gene_symbol': 'FBXO28',
            'major_consequence': 'MSV_EXON_OVR',
            'gene_id': 'ENSG00000228199'
        },
        {
            'gene_symbol': 'FAM131C',
            'major_consequence': 'DUP_LOF',
            'gene_id': 'ENSG00000228201'
        },
        {
            "gene_symbol": "H3-2",
            "gene_id": None,
            "major_consequence": "NEAREST_TSS"
        },
      ],
      'cpx_intervals': [{'type': 'DUP', 'chrom': '2', 'start': 1000, 'end': 3000},
                        {'type': 'INV', 'chrom': '20', 'start': 11000, 'end': 13000}],
      'sv_type_detail': 'dupINV',
      'gnomad_svs_ID': 'gnomAD-SV_v2.1_BND_1_1',
      'gnomad_svs_AF': 0.00679,
      'gnomad_svs_AC': 22,
      'gnomad_svs_AN': 3240,
      'geneIds': ['ENSG00000228198'],
      'sf': 0.000693825,
      'sn': 10088
    },
    'matched_queries': {SV_WGS_INDEX_NAME: ['F000014_14']},
  }

ES_MITO_WGS_VARIANT = {
    "_source" : {
      "genotypes" : [
        {
          "num_alt": 2,
          "gq": 60.0,
          "hl": 1.0,
          "mito_cn": 319.03225806451616,
          "contamination": 0.0,
          "dp": 5139.0,
          "sample_id": "HG00731"
        },
      ],
      "samples_gq_60_to_65" : [
        "HG00731"
      ],
      "samples_num_alt_2" : [ "HG00731" ],
      "AC" : 0,
      "AC_het" : 1,
      "AF" : 0.0,
      "AF_het" : 3.968253968253968E-4,
      "alt" : "A",
      "AN" : 2520,
      "clinvar_allele_id" : None,
      "clinvar_clinical_significance" : "Likely_pathogenic",
      "clinvar_gold_stars" : None,
      "codingGeneIds" : [
        "ENSG00000198840"
      ],
      "common_low_heteroplasmy" : False,
      "contig" : "M",
      "dbnsfp_SIFT_pred" : "D",
      "dbnsfp_MutationTaster_pred" : "N",
      "dbnsfp_FATHMM_pred" : "T",
      "dbnsfp_GERP_RS" : "5.07",
      "dbnsfp_phastCons100way_vertebrate" : "0.958000",
      "docId" : "M-10195-C-A",
      "domains" : [
        "ENSP_mappings:5xtc",
        "ENSP_mappings:5xtd",
        "Gene3D:1",
        "PANTHER:PTHR11058",
        "Pfam:PF00507"
      ],
      "end" : 10195,
      "filters" : [ ],
      "geneIds" : [
        "ENSG00000198840"
      ],
      "gnomad_mito_AN": 56421,
      "gnomad_mito_AC": 1368,
      "gnomad_mito_AC_het": 3,
      "gnomad_mito_AF": 0.024246292,
      "gnomad_mito_AF_het": 5.317169E-5,
      "gnomad_mito_max_hl": 1.0,
      "hap_defining_variant" : False,
      "helix_AC": 1312,
      "helix_AC_het": 5,
      "helix_AF": 0.0033268193,
      "helix_AF_het": 4.081987E-5,
      "helix_max_hl": 0.90441,
      "high_constraint_region" : True,
      "hmtvar_hmtVar" : 0.71,
      "mainTranscript_biotype" : "protein_coding",
      "mainTranscript_canonical" : 1,
      "mainTranscript_category" : "missense",
      "mainTranscript_cdna_start" : 137,
      "mainTranscript_cdna_end" : 137,
      "mainTranscript_codons" : "cCc/cAc",
      "mainTranscript_gene_id" : "ENSG00000198840",
      "mainTranscript_gene_symbol" : "MT-ND3",
      "mainTranscript_hgvs" : "p.Pro46His",
      "mainTranscript_hgvsc" : "ENST00000361227.2:c.137C>A",
      "mainTranscript_major_consequence" : "missense_variant",
      "mainTranscript_major_consequence_rank" : 11,
      "mainTranscript_transcript_id" : "ENST00000361227",
      "mainTranscript_amino_acids" : "P/H",
      "mainTranscript_domains" : "Gene3D:1,ENSP_mappings:5xtc,PANTHER:PTHR11058,ENSP_mappings:5xtd,Pfam:PF00507",
      "mainTranscript_hgvsp" : "ENSP00000355206.2:p.Pro46His",
      "mainTranscript_polyphen_prediction" : "probably_damaging",
      "mainTranscript_protein_id" : "ENSP00000355206",
      "mainTranscript_sift_prediction" : "deleterious_low_confidence",
      "mitimpact_apogee" : 0.42,
      "mitomap_pathogenic" : True,
      "pos" : 10195,
      "ref" : "C",
      "rg37_locus" : {
        "contig" : "MT",
        "position" : 10195
      },
      "rsid" : None,
      "sortedTranscriptConsequences" : [
        {
          "biotype" : "protein_coding",
          "canonical" : 1,
          "cdna_start" : 137,
          "cdna_end" : 137,
          "codons" : "cCc/cAc",
          "gene_id" : "ENSG00000198840",
          "gene_symbol" : "MT-ND3",
          "hgvsc" : "ENST00000361227.2:c.137C>A",
          "hgvsp" : "ENSP00000355206.2:p.Pro46His",
          "transcript_id" : "ENST00000361227",
          "amino_acids" : "P/H",
          "polyphen_prediction" : "probably_damaging",
          "protein_id" : "ENSP00000355206",
          "protein_start" : 46,
          "sift_prediction" : "deleterious_low_confidence",
          "consequence_terms" : [
            "missense_variant"
          ],
          "domains" : [
            "Gene3D:1",
            "ENSP_mappings:5xtc",
            "ENSP_mappings:5xtd",
            "Pfam:PF00507",
            "PANTHER:PTHR11058",
            "PANTHER:PTHR11058"
          ],
          "major_consequence" : "missense_variant",
          "category" : "missense",
          "hgvs" : "p.Pro46His",
          "major_consequence_rank" : 11,
          "transcript_rank" : 0
        }
      ],
      "start" : 10195,
      "transcriptConsequenceTerms" : [
        "missense_variant"
      ],
      "transcriptIds" : [
        "ENST00000361227"
      ],
      "variantId" : "M-10195-C-A",
      "xpos" : 25000010195,
      "xstart" : 25000010195,
      "xstop" : 25000010195
    },
    'matched_queries': {MITO_WGS_INDEX_NAME: ['F000002_2']},
}

OR2M3_COMPOUND_HET_ES_VARIANTS = deepcopy(ES_VARIANTS)
transcripts = OR2M3_COMPOUND_HET_ES_VARIANTS[1]['_source']['sortedTranscriptConsequences']
transcripts[0]['major_consequence'] = 'frameshift_variant'
OR2M3_COMPOUND_HET_ES_VARIANTS[1]['_source']['sortedTranscriptConsequences'] = [transcripts[1], transcripts[0]]
OR2M3_COMPOUND_HET_ES_VARIANTS[0]['_source']['rg37_locus'] = {'contig': '1', 'position': 248367217}
OR2M3_COMPOUND_HET_ES_VARIANTS[1]['_source']['rg37_locus'] = {'contig': '2', 'position': 103343343}
MFSD9_COMPOUND_HET_ES_VARIANTS = deepcopy(OR2M3_COMPOUND_HET_ES_VARIANTS)
for var in MFSD9_COMPOUND_HET_ES_VARIANTS:
    var['_source']['variantId'] = '{}-het'.format(var['_source']['variantId'])
EXTRA_FAMILY_ES_VARIANTS = deepcopy(ES_VARIANTS) + [deepcopy(ES_VARIANTS[0])]
EXTRA_FAMILY_ES_VARIANTS[2]['matched_queries'][INDEX_NAME] = ['F000005_5']
MISSING_SAMPLE_ES_VARIANTS = deepcopy(ES_VARIANTS)
MISSING_SAMPLE_ES_VARIANTS[1]['_source']['samples_num_alt_1'] = []

ES_SV_COMP_HET_VARIANT = deepcopy(ES_SV_VARIANT)
ES_SV_COMP_HET_VARIANT['_source']['xpos'] = 2101343374
ES_SV_COMP_HET_VARIANT['_source']['start'] = 101343374
ES_SV_COMP_HET_VARIANT['_source']['xstop'] = 1104943628
ES_SV_COMP_HET_VARIANT['_source']['end'] = 104943628
ES_SV_COMP_HET_VARIANT['_source']['num_exon'] = 2
ES_SV_COMP_HET_VARIANT['_source']['variantId'] = 'prefix_191011_DEL'
ES_SV_COMP_HET_VARIANT['_source']['svType'] = 'DEL'
for gen in ES_SV_COMP_HET_VARIANT['_source']['genotypes']:
    gen.update({'start': None, 'end': None, 'num_exon': None})
    gen.pop('geneIds')

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
    '{},{}'.format(INDEX_NAME, SV_INDEX_NAME): {'ENSG00000228198': [ES_SV_VARIANT, ES_SV_COMP_HET_VARIANT, ES_VARIANTS[1]], 'ENSG00000135953': []},
}

INDEX_ES_VARIANTS = {
    INDEX_NAME: ES_VARIANTS,
    SECOND_INDEX_NAME: [ES_VARIANTS[1]],
    SV_INDEX_NAME: [ES_SV_VARIANT],
    SV_WGS_INDEX_NAME: [ES_SV_WGS_VARIANT],
    HG38_INDEX_NAME: [BUILD_38_ES_VARIANT, BUILD_38_NO_LIFTOVER_ES_VARIANT],
    MITO_WGS_INDEX_NAME: [ES_MITO_WGS_VARIANT],
}
INDEX_ES_VARIANTS.update({k: ES_VARIANTS for k in SUB_INDICES + SECOND_SUB_INDICES})

PARSED_ANY_AFFECTED_VARIANTS = deepcopy(PARSED_VARIANTS)
PARSED_ANY_AFFECTED_VARIANTS[1]['familyGuids'] = ['F000003_3']
PARSED_ANY_AFFECTED_VARIANTS[1]['genotypes'] = {'I000007_na20870': PARSED_ANY_AFFECTED_VARIANTS[1]['genotypes']['I000007_na20870']}

PARSED_COMPOUND_HET_VARIANTS = deepcopy(PARSED_VARIANTS)
PARSED_COMPOUND_HET_VARIANTS[0]['_sort'] = [1248367327]
PARSED_COMPOUND_HET_VARIANTS[1]['_sort'] = [2103343453]
PARSED_COMPOUND_HET_VARIANTS[1]['familyGuids'] = ['F000003_3']

PARSED_SV_COMPOUND_HET_VARIANTS = [deepcopy(PARSED_SV_VARIANT), deepcopy(PARSED_COMPOUND_HET_VARIANTS[1])]
PARSED_SV_COMPOUND_HET_VARIANTS[0].update({
    '_sort': [2101343474],
    'xpos': 2101343374,
    'pos': 101343374,
    'end': 104943628,
    'variantId': 'prefix_191011_DEL',
    'svType': 'DEL',
})
del PARSED_SV_COMPOUND_HET_VARIANTS[0]['svSourceDetail']
PARSED_SV_COMPOUND_HET_VARIANTS[0]['transcripts']['ENSG00000186092'] = [{'geneId': 'ENSG00000186092'}]
for gen in PARSED_SV_COMPOUND_HET_VARIANTS[0]['genotypes'].values():
    gen.update({'start': None, 'end': None, 'numExon': None, 'geneIds': None})
PARSED_SV_COMPOUND_HET_VARIANTS[1]['familyGuids'] = ['F000002_2']

PARSED_COMPOUND_HET_VARIANTS_PROJECT_2 = deepcopy(PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT)
for variant in PARSED_COMPOUND_HET_VARIANTS_PROJECT_2:
    variant.update({
        'variantId': '{}-het'.format(variant['variantId']),
        'familyGuids': ['F000011_11'],
        'genotypes': {
            'I000015_na20885': variant['genotypes']['I000015_na20885'],
        },
        'genomeVersion': '37',
        'selectedMainTranscriptId': None,
    })
    variant['clinvar']['version'] = None

PARSED_NO_CONSEQUENCE_FILTER_VARIANTS = deepcopy(PARSED_VARIANTS)
PARSED_NO_CONSEQUENCE_FILTER_VARIANTS[1]['selectedMainTranscriptId'] = None

PARSED_CADD_VARIANTS = deepcopy(PARSED_NO_CONSEQUENCE_FILTER_VARIANTS)
PARSED_CADD_VARIANTS[0]['_sort'][0] = -25.9
PARSED_CADD_VARIANTS[1]['_sort'][0] = maxsize


PARSED_MULTI_INDEX_VARIANT = deepcopy(PARSED_VARIANTS[1])
PARSED_MULTI_INDEX_VARIANT['familyGuids'].append('F000011_11')
PARSED_MULTI_INDEX_VARIANT['genotypes']['I000015_na20885'] = {
    'ab': 0.631, 'ad': None, 'gq': 99, 'sampleId': 'NA20885', 'numAlt': 1, 'dp': 50, 'pl': None, 'sampleType': 'WES',
}

PARSED_HG38_VARIANT = deepcopy(PARSED_VARIANTS[1])
PARSED_HG38_VARIANT.update({
    'familyGuids': ['F000011_11'],
    'genotypes': {
        'I000015_na20885': PARSED_MULTI_INDEX_VARIANT['genotypes']['I000015_na20885'],
    },
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
PARSED_HG38_VARIANT['clinvar']['version'] = None

PARSED_MULTI_SAMPLE_MULTI_INDEX_VARIANT = deepcopy(PARSED_MULTI_INDEX_VARIANT)
for guid, genotype in PARSED_MULTI_SAMPLE_MULTI_INDEX_VARIANT['genotypes'].items():
    PARSED_MULTI_SAMPLE_MULTI_INDEX_VARIANT['genotypes'][guid] = dict(otherSample=genotype, **genotype)

PARSED_MULTI_SAMPLE_VARIANT = deepcopy(PARSED_VARIANTS[1])
for guid, genotype in PARSED_MULTI_SAMPLE_VARIANT['genotypes'].items():
    PARSED_MULTI_SAMPLE_VARIANT['genotypes'][guid] = dict(otherSample=genotype, **genotype)

PARSED_MULTI_SAMPLE_VARIANT_0 = deepcopy(PARSED_VARIANTS[0])
for guid, genotype in PARSED_MULTI_SAMPLE_VARIANT_0['genotypes'].items():
    PARSED_MULTI_SAMPLE_VARIANT_0['genotypes'][guid] = dict(otherSample=genotype, **genotype)

PARSED_MULTI_SAMPLE_COMPOUND_HET_VARIANTS = deepcopy(PARSED_COMPOUND_HET_VARIANTS)
for variant in PARSED_MULTI_SAMPLE_COMPOUND_HET_VARIANTS:
    for guid, genotype in variant['genotypes'].items():
        variant['genotypes'][guid] = dict(otherSample=genotype, **genotype)


PARSED_ANY_AFFECTED_MULTI_INDEX_VERSION_VARIANT = deepcopy(PARSED_MULTI_INDEX_VARIANT)
PARSED_ANY_AFFECTED_MULTI_INDEX_VERSION_VARIANT.update({
    'familyGuids': ['F000003_3', 'F000011_11'],
    'genotypes': {
        ind_guid: PARSED_MULTI_INDEX_VARIANT['genotypes'][ind_guid]
        for ind_guid in ['I000007_na20870', 'I000015_na20885']
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
    'mpc_MPC',
    'dbnsfp_DANN_score',
    'eigen_Eigen_phred',
    'dbnsfp_REVEL_score',
    'splice_ai_delta_score',
    'splice_ai_splice_consequence',
    'dbnsfp_FATHMM_pred',
    'dbnsfp_fathmm_MKL_coding_pred',
    'dbnsfp_MutPred_score',
    'dbnsfp_VEST4_score',
    'primate_ai_score',
    'dbnsfp_SIFT_pred',
    'dbnsfp_Polyphen2_HVAR_pred',
    'cadd_PHRED',
    'gnomad_non_coding_constraint_z_score',
    'sortedTranscriptConsequences',
    'screen_region_type',
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
    'gnomad_genomes_AC',
    'gnomad_genomes_Hom',
    'gnomad_genomes_Hemi',
    'gnomad_genomes_AF',
    'gnomad_genomes_AF_POPMAX_OR_GLOBAL',
    'gnomad_genomes_AN',
    'gnomad_genomes_Het',
    'gnomad_genomes_ID',
    'gnomad_exomes_AC',
    'gnomad_exomes_Hom',
    'gnomad_exomes_Hemi',
    'gnomad_exomes_AF',
    'gnomad_exomes_AF_POPMAX_OR_GLOBAL',
    'gnomad_exomes_AN',
    'gnomad_exomes_Het',
    'gnomad_exomes_ID',
    'exac_AC_Adj',
    'exac_AC_Hom',
    'exac_AC_Hemi',
    'exac_AF_POPMAX',
    'exac_AF',
    'exac_AN_Adj',
    'exac_Het',
    'exac_ID',
    'topmed_AC',
    'topmed_Hom',
    'topmed_Hemi',
    'topmed_Het',
    'topmed_AF',
    'topmed_AN',
    'topmed_ID',
    'gnomad_genomes_FAF_AF',
    'rg37_locus',
    'rg37_locus_end',
    'xstop',
    'bothsides_support',
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
    'sv_type_detail',
    'cpx_intervals',
    'gnomad_svs_AC',
    'gnomad_svs_Hom',
    'gnomad_svs_Hemi',
    'gnomad_svs_AF',
    'gnomad_svs_AN',
    'gnomad_svs_filter_AF',
    'gnomad_svs_Het',
    'gnomad_svs_ID',
    'bothsides_support',
]

MITO_MAPPING_FIELDS = [
    "AC",
    "AC_het",
    "AF",
    "AF_het",
    "AN",
    "alt",
    "clinvar_allele_id",
    "clinvar_clinical_significance",
    "clinvar_gold_stars",
    "common_low_heteroplasmy",
    "contig",
    "dbnsfp_FATHMM_pred",
    "dbnsfp_MutationTaster_pred",
    "dbnsfp_Polyphen2_HVAR_pred",
    "dbnsfp_REVEL_score",
    "dbnsfp_SIFT_pred",
    "end",
    "filters",
    "genotypes",
    "gnomad_mito_AC",
    "gnomad_mito_AC_het",
    "gnomad_mito_AF",
    "gnomad_mito_AF_het",
    "gnomad_mito_AN",
    "gnomad_mito_max_hl",
    "hap_defining_variant",
    "helix_AC",
    "helix_AC_het",
    "helix_AF",
    "helix_AF_het",
    "helix_max_hl",
    "high_constraint_region",
    "hmtvar_hmtVar",
    "mitimpact_apogee",
    "mitomap_pathogenic",
    "mitotip_mitoTIP",
    "ref",
    "rg37_locus",
    "rsid",
    "samples_num_alt_1",
    "samples_num_alt_2",
    "sortedTranscriptConsequences",
    "start",
    "variantId",
    "xpos",
    "xstop",
]

MITO_SOURCE_ONLY_FIELDS = [
    'callset_max_hl',
    'exac_max_hl',
    'gnomad_exomes_max_hl',
    'gnomad_genomes_max_hl',
    'gnomad_svs_max_hl',
    'sv_callset_max_hl',
    'topmed_max_hl',
    'helix_ID',
    'helix_Hemi',
    'helix_AN',
    'helix_filter_AF',
    'helix_Het',
    'helix_Hom',
    'gnomad_mito_filter_AF',
    'gnomad_mito_Hom',
    'gnomad_mito_ID',
    'gnomad_mito_Het',
    'gnomad_mito_Hemi',
    'callset_heteroplasmy_Het',
    'callset_heteroplasmy_ID',
    'callset_heteroplasmy_Hemi',
    'callset_heteroplasmy_filter_AF',
    'callset_heteroplasmy_Hom',
    'callset_heteroplasmy_max_hl',
    'gnomad_mito_heteroplasmy_filter_AF',
    'gnomad_mito_heteroplasmy_Hemi',
    'gnomad_mito_heteroplasmy_Hom',
    'gnomad_mito_heteroplasmy_ID',
    'gnomad_mito_heteroplasmy_Het',
    'helix_heteroplasmy_Het',
    'helix_heteroplasmy_ID',
    'helix_heteroplasmy_Hemi',
    'helix_heteroplasmy_filter_AF',
    'helix_heteroplasmy_Hom',
]

SOURCE_FIELDS = {
    'homozygote_count', 'callset_Hemi', 'callset_Het', 'callset_ID', 'sv_callset_Hemi',
    'sv_callset_Hom', 'sv_callset_Het', 'sv_callset_ID', 'algorithms',
}
SOURCE_FIELDS.update(MAPPING_FIELDS)
SOURCE_FIELDS.update(SV_MAPPING_FIELDS)
SOURCE_FIELDS.update(MITO_MAPPING_FIELDS)
SOURCE_FIELDS.update(MITO_SOURCE_ONLY_FIELDS)
SOURCE_FIELDS -= {
    'samples_no_call', 'samples_cn_0', 'samples_cn_1', 'samples_cn_2', 'samples_cn_3', 'samples_cn_gte_4', 'topmed_Het',
    'gnomad_genomes_FAF_AF',
}

FIELD_TYPE_MAP = {
    'cadd_PHRED': {'type': 'keyword'},
    'primate_ai_score': {'type': 'float'},
    'rg37_locus': {'properties': {'contig': {'type': 'keyword'}, 'position': {'type': 'integer'}}},
    'rg37_locus_end': {'properties': {'contig': {'type': 'keyword'}, 'position': {'type': 'integer'}}}
}
MAPPING_PROPERTIES = {field: FIELD_TYPE_MAP.get(field, {'type': 'keyword'}) for field in MAPPING_FIELDS}

CORE_INDEX_METADATA = {
    INDEX_NAME: {
        '_meta': {'genomeVersion': '37', 'clinvar_version': '2023-03-05'},
        'properties': MAPPING_PROPERTIES,
    },
    SECOND_INDEX_NAME: {
        '_meta': {'genomeVersion': '37', 'datasetType': 'VARIANTS'},
        'properties': MAPPING_PROPERTIES,
    },
    SV_INDEX_NAME: {
        '_meta': {'genomeVersion': '37', 'datasetType': 'SV'},
        'properties': {field: {'type': 'keyword'} for field in SV_MAPPING_FIELDS},
    },
    MITO_WGS_INDEX_NAME: {
        '_meta': {'genomeVersion': '37', 'datasetType': 'MITO'},
        'properties': {field: {'type': 'keyword'} for field in MITO_MAPPING_FIELDS},
    },
}
INDEX_METADATA = {
    HG38_INDEX_NAME: deepcopy(CORE_INDEX_METADATA[SECOND_INDEX_NAME]),
    SV_WGS_INDEX_NAME: deepcopy(CORE_INDEX_METADATA[SV_INDEX_NAME]),
}
for meta in INDEX_METADATA.values():
    meta['_meta']['genomeVersion'] = '38'
INDEX_METADATA.update(CORE_INDEX_METADATA)

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

COMPOUND_HET_PATH_INHERITANCE_QUERY = deepcopy(COMPOUND_HET_INHERITANCE_QUERY)
for fam_q in COMPOUND_HET_PATH_INHERITANCE_QUERY['bool']['should']:
    fam_quality_q = fam_q['bool']['must'][1]
    fam_quality_q['bool'] = {'should': [
        deepcopy(fam_quality_q),
        {'regexp': {'clinvar_clinical_significance': '.*Pathogenic.*'}}
    ]}

RECESSIVE_INHERITANCE_QUERY = {
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
                        'must': [{'term': {'samples_num_alt_2': 'HG00731'}}]
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
                    {'term': {'samples_num_alt_2': 'NA20870'}},
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

def mock_hits(hits, increment_sort=False, include_matched_queries=True, sort=None, index=INDEX_NAME):
    parsed_hits = deepcopy(hits)
    for hit in parsed_hits:
        hit.update({
            '_index': index,
            '_id': hit['_source']['variantId'],
            '_type': 'structural_variant' if SV_INDEX_NAME in index or SV_WGS_INDEX_NAME in index else 'variant',
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
                    sort_key = sort_key['_script']['script']['params'].get('field', 'xpos') # pylint: disable=invalid-sequence-index
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
    index = ALIAS_MAP.get(index, index)
    indices = index.split(',')
    include_matched_queries = False
    variant_id_filters = None
    gene_ids_filters = set()
    if 'query' in search:
        for search_filter in search['query']['bool']['filter']:
            if not variant_id_filters:
                variant_id_filters = search_filter.get('terms', {}).get('variantId')
            if not gene_ids_filters and not search.get('aggs'):
                gene_ids_filters.update(search_filter.get('terms', {}).get('geneIds') or [])
            possible_inheritance_filters = search_filter.get('bool', {}).get('should', []) + [search_filter]
            if any('_name' in possible_filter.get('bool', {}) for possible_filter in possible_inheritance_filters):
                include_matched_queries = True
                break

    response_dict = {
        'took': 1,
        'hits': {'total': {'value': 5}, 'hits': []}
    }
    for index_name in sorted(indices):
        index_hits = mock_hits(
            INDEX_ES_VARIANTS[index_name], include_matched_queries=include_matched_queries, sort=search.get('sort'),
            index=index_name)
        if variant_id_filters:
            index_hits = [hit for hit in index_hits if hit['_id'] in variant_id_filters]
        elif gene_ids_filters:
            index_hits = [hit for hit in index_hits if any(
                gene_ids_filters.intersection({t['gene_id'] for t in hit['_source']['sortedTranscriptConsequences']})
            )]
        response_dict['hits']['hits'] += index_hits

    try:
        response_dict['hits']['hits'] = sorted(response_dict['hits']['hits'], key=lambda v: v['_sort'])
    except (KeyError, TypeError):
        pass

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
                doc_count = 0
                for sample_field in ['samples', 'samples_num_alt_1', 'samples_num_alt_2']:
                    gene_samples = defaultdict(int)
                    for var in index_vars.get(bucket['key'], ES_VARIANTS):
                        for sample in var['_source'].get(sample_field, []):
                            gene_samples[sample] += 1
                    bucket[sample_field] = {'buckets': [{'key': k, 'doc_count': v} for k, v in gene_samples.items()]}
                    doc_count += sum(gene_samples.values())
                bucket['doc_count'] = doc_count

        response_dict['aggregations'] = {'genes': {'buckets': buckets}}

    if len(response_dict['hits']['hits']) == 0:
        response_dict['hits']['total']['value'] = 0
    elif gene_ids_filters == {'ENSG00000186092'}:
        response_dict['hits']['total']['value'] = 1


    return response_dict

def get_indices_from_url(url):
    return url.split('/')[1]

def get_metadata_callback(request):
    indices = get_indices_from_url(request.url).split(',')
    response = {index: {'mappings': INDEX_METADATA[index]} for index in indices}
    return 200, {}, json.dumps(response)

def get_search_callback(request):
    body = json.loads(request.body)
    response = create_mock_response(body, get_indices_from_url(request.url))
    return 200, {}, json.dumps(response)

def parse_msearch_body(body):
    return [json.loads(row) for row in body.decode().split('\n') if row]

def get_msearch_callback(request):
    body = parse_msearch_body(request.body)
    response = {
        'responses': [
            create_mock_response(exec_search, index=','.join(body[i-1]['index']))
            for i, exec_search in enumerate(body) if not exec_search.get('index')]
    }
    return 200, {}, json.dumps(response)

def setup_search_responses():
    urllib3_responses.add_callback(
        urllib3_responses.POST, '/_msearch', callback=get_msearch_callback,
        content_type='application/json', match_querystring=True)
    urllib3_responses.add_callback(
        urllib3_responses.POST, re.compile('^/[,\w]+/_search$'), callback=get_search_callback,
        content_type='application/json', match_querystring=True)

def setup_responses():
    urllib3_responses.add_callback(
        urllib3_responses.GET, re.compile('^/[,\w]+/_mapping$'), callback=get_metadata_callback,
        content_type='application/json', match_querystring=True)
    setup_search_responses()


@mock.patch('seqr.utils.search.elasticsearch.es_utils.ELASTICSEARCH_SERVICE_HOSTNAME', 'testhost')
@mock.patch('seqr.utils.redis_utils.redis.StrictRedis', lambda **kwargs: MOCK_REDIS)
class EsUtilsTest(TestCase):
    databases = '__all__'
    fixtures = ['users', '1kg_project', 'reference_data']

    def setUp(self):
        Sample.objects.filter(sample_id='NA19678').update(is_active=False)
        self.families = Family.objects.filter(guid__in=['F000003_3', 'F000002_2', 'F000005_5'])

    def assertExecutedSearch(self, filters=None, start_index=0, size=2, index=INDEX_NAME, expected_source_fields=SOURCE_FIELDS, call_index=-1, **kwargs):
        executed_search = urllib3_responses.call_request_json(index=call_index)
        searched_indices = get_indices_from_url(urllib3_responses.calls[call_index].request.url)
        self.assertListEqual(sorted(searched_indices.split(',')), sorted(index.split(',')))
        self.assertSameSearch(
            executed_search,
            dict(filters=filters, start_index=start_index, size=size, **kwargs),
            expected_source_fields=expected_source_fields,
        )

    def assertExecutedSearches(self, searches):
        executed_search = parse_msearch_body(urllib3_responses.calls[-1].request.body)
        self.assertEqual(len(executed_search), len(searches) * 2)
        for i, expected_search in enumerate(searches):
            self.assertDictEqual(executed_search[i * 2], {'index': expected_search.get('index', INDEX_NAME).split(',')})
            self.assertSameSearch(executed_search[(i * 2) + 1], expected_search)

    def assertSameSearch(self, executed_search, expected_search_params, expected_source_fields=SOURCE_FIELDS):
        expected_search = {
            'from': expected_search_params['start_index'],
            'size': expected_search_params['size']
        }

        if expected_search_params['filters']:
            expected_search['query'] = {
                'bool': {
                    'filter': expected_search_params['filters']
                }
            }

        if expected_search_params.get('query'):
            expected_search['query']['bool']['must'] = expected_search_params['query']

        if not expected_search_params.get('unsorted'):
            expected_search['sort'] = expected_search_params.get('sort') or ['xpos', 'variantId']

        if expected_search_params.get('gene_aggs'):
            expected_search['aggs'] = {
                'genes': {'terms': {'field': 'geneIds', 'min_doc_count': 2, 'size': 1001}, 'aggs': {
                    'vars_by_gene': {
                        'top_hits': {'sort': expected_search['sort'], '_source': mock.ANY, 'size': 100}
                    }
                }}}
        elif expected_search_params.get('gene_count_aggs'):
            expected_search['aggs'] = {'genes': {
                'terms': {'field': 'mainTranscript_gene_id', 'size': 1001},
                'aggs': expected_search_params['gene_count_aggs']
            }}
            del expected_search['sort']
        else:
            expected_search['_source'] = mock.ANY
        self.assertDictEqual(executed_search, expected_search)

        if not expected_search_params.get('gene_count_aggs'):
            source = executed_search['aggs']['genes']['aggs']['vars_by_gene']['top_hits']['_source'] \
                if expected_search_params.get('gene_aggs')  else executed_search['_source']
            self.assertSetEqual(expected_source_fields, set(source))

    def assertCachedResults(self, results_model, expected_results, sort='xpos'):
        cache_key = 'search_results__{}__{}'.format(results_model.guid, sort)
        self.assertIn(cache_key, REDIS_CACHE.keys())
        self.assertDictEqual(json.loads(REDIS_CACHE[cache_key]), expected_results)
        MOCK_REDIS.expire.assert_called_with(cache_key, timedelta(weeks=2))

    @urllib3_responses.activate
    def test_get_es_variants_for_variant_ids(self):
        setup_responses()
        get_variants_for_variant_ids(self.families, ['2-103343353-GAGA-G', '1-248367227-TC-T', 'prefix-938_DEL'])
        self.assertExecutedSearch(
            filters=[{'terms': {'variantId': ['2-103343353-GAGA-G', '1-248367227-TC-T', 'prefix-938_DEL']}}],
            size=6, index=','.join([INDEX_NAME, SV_INDEX_NAME]),
        )

    @urllib3_responses.activate
    def test_get_single_es_variant(self):
        setup_responses()
        variant = get_single_variant(self.families, '2-103343353-GAGA-G')
        self.assertDictEqual(variant, PARSED_NO_CONSEQUENCE_FILTER_VARIANTS[1])
        self.assertExecutedSearch(
            filters=[{'terms': {'variantId': ['2-103343353-GAGA-G']}}],
            size=1, index=INDEX_NAME
        )

        variant = get_single_variant(self.families, 'prefix_19107_DEL')
        self.assertDictEqual(variant, PARSED_SV_VARIANT)
        self.assertExecutedSearch(
            filters=[{'terms': {'variantId': ['prefix_19107_DEL']}}], size=1, index=SV_INDEX_NAME,
        )

        variant = get_single_variant(self.families, 'M-10195-C-A')
        self.assertDictEqual(variant, PARSED_MITO_VARIANT)
        self.assertExecutedSearch(
            filters=[{'terms': {'variantId': ['M-10195-C-A']}}], size=1, index=MITO_WGS_INDEX_NAME,
        )

        variant = get_single_variant(self.families, '1-248367227-TC-T', return_all_queried_families=True)
        all_family_variant = deepcopy(PARSED_NO_CONSEQUENCE_FILTER_VARIANTS[0])
        all_family_variant['familyGuids'] = ['F000002_2', 'F000003_3', 'F000005_5']
        all_family_variant['genotypes']['I000004_hg00731'] = {
            'ab': 0, 'ad': None, 'gq': 99, 'sampleId': 'HG00731', 'numAlt': 0, 'dp': 88, 'pl': None, 'sampleType': 'WES',
        }
        self.assertDictEqual(variant, all_family_variant)
        self.assertExecutedSearch(
            filters=[{'terms': {'variantId': ['1-248367227-TC-T']}}],
            size=1, index=INDEX_NAME,
        )

        with self.assertRaises(InvalidSearchException) as cm:
            get_single_variant(self.families, '10-10334333-A-G')
        self.assertEqual(str(cm.exception), 'Variant 10-10334333-A-G not found')

    @mock.patch('seqr.utils.search.elasticsearch.es_search.MAX_COMPOUND_HET_GENES', 1)
    @mock.patch('seqr.utils.search.elasticsearch.es_gene_agg_search.MAX_COMPOUND_HET_GENES', 1)
    @mock.patch('seqr.utils.search.elasticsearch.es_search.logger')
    @urllib3_responses.activate
    def test_invalid_get_es_variants(self, mock_logger):
        setup_responses()
        mito_sample = Sample.objects.get(elasticsearch_index=MITO_WGS_INDEX_NAME)
        mito_sample.individual_id = 6
        mito_sample.save()
        search_model = VariantSearch.objects.create(search={})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)

        results_model.families.set(self.families)
        Sample.objects.filter(elasticsearch_index=INDEX_NAME).update(elasticsearch_index=HG38_INDEX_NAME)
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(results_model)
        self.assertEqual(
            str(cm.exception), 'The following indices do not have the expected genome version 37: test_index_hg38 (38)',
        )
        Sample.objects.filter(elasticsearch_index=HG38_INDEX_NAME).update(elasticsearch_index=INDEX_NAME)

        results_model.families.set(self.families)
        search_model.search = {
            'inheritance': {'mode': 'compound_het'},
            'locus': {'rawItems': 'WASH7P'},
            'annotations': {'frameshift': ['frameshift_variant']},
        }
        search_model.save()
        with self.assertRaises(InvalidSearchException) as cm:
            query_variants(results_model)
        self.assertEqual(
            str(cm.exception),
            'This search returned too many compound heterozygous variants. Please add stricter filters')

        with self.assertRaises(InvalidSearchException) as cm:
            get_variant_query_gene_counts(results_model, None)
        self.assertEqual(str(cm.exception), 'This search returned too many genes')

        search_model.search = {'qualityFilter': {'min_gq': 7}}
        search_model.save()
        with self.assertRaises(Exception) as cm:
            query_variants(results_model)
        self.assertEqual(str(cm.exception), 'Invalid gq filter 7')

        search_model.search = {}
        search_model.save()
        urllib3_responses.reset()
        urllib3_responses.add(
            urllib3_responses.POST, '/_msearch', body=ReadTimeoutError('', '', 'timeout'))
        urllib3_responses.add_json('/_tasks?actions=*search&group_by=parents', {'tasks': {
            123: {'running_time_in_nanos': 10},
            456: {'running_time_in_nanos': 10 ** 12},
        }})
        with self.assertRaises(ConnectionTimeout):
            query_variants(results_model)
        self.assertListEqual(
            [call.request.url for call in urllib3_responses.calls],
            ['/_msearch', '/_tasks?actions=%2Asearch&group_by=parents'])
        mock_logger.error.assert_called_with('ES Query Timeout: Found 1 long running searches', None, detail=[
            {'task': {'running_time_in_nanos': 10 ** 12}, 'parent_task_id': '456'},
        ])

        urllib3_responses.reset()
        urllib3_responses.add_json('/_msearch', {'responses': [
            {'error': {'type': 'search_phase_execution_exception', 'root_cause': [{'type': 'too_many_clauses'}]}}
        ]}, method=urllib3_responses.POST)

        with self.assertRaises(TransportError) as cm:
            query_variants(results_model)
        self.assertDictEqual(
            cm.exception.info,
            {'type': 'search_phase_execution_exception', 'root_cause': [{'type': 'too_many_clauses'}]})

        _set_cache(f'index_metadata__{INDEX_NAME},{MITO_WGS_INDEX_NAME},{SV_INDEX_NAME}', None)
        urllib3_responses.add(
            urllib3_responses.GET, f'/{INDEX_NAME},{MITO_WGS_INDEX_NAME},{SV_INDEX_NAME}/_mapping', body=Exception('Connection error'))
        with self.assertRaises(InvalidIndexException) as cm:
            query_variants(results_model)
        self.assertEqual(str(cm.exception), 'test_index,test_index_mito_wgs,test_index_sv - Error accessing index: Connection error')

        urllib3_responses.replace_json(f'/{INDEX_NAME},{MITO_WGS_INDEX_NAME},{SV_INDEX_NAME}/_mapping', {})
        with self.assertRaises(InvalidIndexException) as cm:
            query_variants(results_model)
        self.assertEqual(str(cm.exception), 'Could not find expected indices: test_index_sv, test_index_mito_wgs, test_index')

    @urllib3_responses.activate
    def test_get_es_variants(self):
        setup_responses()
        # Testing mito indices is done in other tests, it is helpful to have a strightforward single datatype test
        Sample.objects.get(elasticsearch_index=MITO_WGS_INDEX_NAME).delete()
        search_model = VariantSearch.objects.create(search={'annotations': {'frameshift': ['frameshift_variant']}})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, total_results = query_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertDictEqual(variants[0], PARSED_VARIANTS[0])
        self.assertDictEqual(variants[1], PARSED_VARIANTS[1])
        self.assertEqual(total_results, 5)

        self.assertCachedResults(results_model, {'all_results': variants, 'total_results': 5})

        self.assertExecutedSearch(filters=[ANNOTATION_QUERY, ALL_INHERITANCE_QUERY])

        # does not save non-consecutive pages
        variants, total_results = query_variants(results_model, page=3, num_results=2)
        self.assertEqual(total_results, 5)
        self.assertCachedResults(results_model, {'all_results': variants, 'total_results': 5})
        self.assertExecutedSearch(filters=[ANNOTATION_QUERY, ALL_INHERITANCE_QUERY], start_index=4, size=2)

        # test pagination
        variants, total_results = query_variants(results_model, page=2, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertEqual(total_results, 5)
        self.assertCachedResults(results_model, {'all_results': PARSED_VARIANTS + PARSED_VARIANTS, 'total_results': 5})
        self.assertExecutedSearch(filters=[ANNOTATION_QUERY, ALL_INHERITANCE_QUERY], start_index=2, size=2)

        # test does not re-fetch page
        urllib3_responses.reset()
        variants, total_results = query_variants(results_model, page=1, num_results=3)
        self.assertEqual(len(variants), 3)
        self.assertListEqual(variants, PARSED_VARIANTS + PARSED_VARIANTS[:1])
        self.assertEqual(total_results, 5)

        # test load_all
        setup_responses()
        with mock.patch('seqr.utils.search.utils.MAX_VARIANTS', 100):
            variants, _ = query_variants(results_model, page=1, num_results=2, load_all=True)
        self.assertExecutedSearch(filters=[ANNOTATION_QUERY, ALL_INHERITANCE_QUERY], start_index=4, size=1)
        self.assertEqual(len(variants), 5)
        self.assertListEqual(variants, PARSED_VARIANTS + PARSED_VARIANTS + PARSED_VARIANTS[:1])

        # test does not re-fetch once all loaded
        urllib3_responses.reset()
        with mock.patch('seqr.utils.search.utils.MAX_VARIANTS', 1):
            variants, _ = query_variants(results_model, page=1, num_results=2, load_all=True)
        self.assertEqual(len(variants), 5)
        self.assertListEqual(variants, PARSED_VARIANTS + PARSED_VARIANTS + PARSED_VARIANTS[:1])

    @urllib3_responses.activate
    def test_filtered_get_es_variants(self):
        setup_responses()
        # Testing mito indices is done in other tests, it is helpful to have a strightforward single datatype test
        Sample.objects.get(elasticsearch_index=MITO_WGS_INDEX_NAME).delete()
        search_model = VariantSearch.objects.create(search={
            'pathogenicity': {
                'clinvar': ['pathogenic', 'likely_pathogenic', 'vus_or_conflicting'],
                'hgmd': ['disease_causing', 'likely_disease_causing'],
            },
            'annotations': {
                'in_frame': ['inframe_insertion', 'inframe_deletion'],
                'other': ['5_prime_UTR_variant', 'intergenic_variant'],
                'SCREEN': ['dELS', 'DNase-only'],
                'splice_ai': '0.8',
            },
            'freqs': {
                'callset': {'af': 0.1},
                'exac': {'ac': 2, 'af': None},
                'g1k': {'ac': None, 'af': 0.001},
                'gnomad_exomes': {'af': 0.01, 'ac': 3, 'hh': 3},
                'gnomad_genomes': {'af': 0.01, 'hh': 3},
                'topmed': {'ac': 2, 'af': None},
            },
            'qualityFilter': {'min_ab': 10, 'min_gq': 15, 'vcf_filter': 'pass', 'affected_only': True},
            'in_silico': {'cadd': '11.5', 'sift': 'D', 'fathmm': 'D'},
            'inheritance': {'mode': 'de_novo'},
            'customQuery': {'term': {'customFlag': 'flagVal'}},
            'locus': {'rawItems': 'WASH7P, chr2:1234-5678, chr7:100-10100%10', 'excludeLocations': True},
        })

        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)
        variants, total_results = query_variants(results_model, sort='cadd', num_results=2)

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
                            {'range': {'xstop': {'gte': 2000005678}}},
                            {'range': {'xpos': {'gte': 2000000001}}},
                            {'range': {'xstop': {'lte': 2300000000}}},
                        ]}},
                        {'terms': {'geneIds': ['ENSG00000227232']}},
                        {'bool': {'must': [
                            {'range': {'xpos': {'gte': 7000000001, 'lte': 7000001100}}},
                            {'range': {'xstop': {'gte': 7000009100, 'lte': 7000011100}}}]}},
                    ]
                }
            },
            {'bool': {'should': [
                {'bool': {
                    'minimum_should_match': 1,
                    'should': [
                        {'bool': {'must_not': [{'exists': {'field': 'AF'}}]}},
                        {'range': {'AF': {'lte': 0.1}}}
                    ],
                    'must': [
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
                                {'bool': {'must_not': [{'exists': {'field': 'topmed_AC'}}]}},
                                {'range': {'topmed_AC': {'lte': 2}}}
                            ]}
                        }
                    ]
                }},
                {'bool': {
                    'minimum_should_match': 1,
                    'should': [
                        {'bool': {'must_not': [{'exists': {'field': 'AF'}}]}},
                        {'range': {'AF': {'lte': 0.1}}}
                    ],
                    'must': [
                        {'bool': {
                            'minimum_should_match': 1,
                            'should': [
                                {'bool': {'must_not': [{'exists': {'field': 'gnomad_exomes_AF_POPMAX_OR_GLOBAL'}}]}},
                                {'range': {'gnomad_exomes_AF_POPMAX_OR_GLOBAL': {'lte': 0.05}}}
                            ]
                        }},
                        {'bool': {
                            'minimum_should_match': 1,
                            'should': [
                                {'bool': {'must_not': [{'exists': {'field': 'gnomad_genomes_AF_POPMAX_OR_GLOBAL'}}]}},
                                {'range': {'gnomad_genomes_AF_POPMAX_OR_GLOBAL': {'lte': 0.05}}}
                            ]
                        }},
                        {'regexp': {
                            'clinvar_clinical_significance': '.*Likely_pathogenic.*|.*Pathogenic.*',
                        }}
                    ]
                }},

            ]}},
            {'bool': {'should': [
                {'bool': {'must_not': [{'exists': {'field': 'cadd_PHRED'}}]}},
                {'range': {'cadd_PHRED': {'gte': 11.5}}},
                {'bool': {'must_not': [{'exists': {'field': 'dbnsfp_SIFT_pred'}}]}},
                {'prefix': {'dbnsfp_SIFT_pred': 'D'}},
                {'bool': {'must_not': [{'exists': {'field': 'dbnsfp_fathmm_MKL_coding_pred'}}]}},
                {'prefix': {'dbnsfp_fathmm_MKL_coding_pred': 'D'}},
            ]}},
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
                        {'regexp': {
                            'clinvar_clinical_significance': '.*Likely_pathogenic.*|.*Pathogenic.*|Conflicting_interpretations_of_pathogenicity.*|~((.*[Bb]enign.*)|(.*[Pp]athogenic.*))',
                        }},
                        {'terms': {'hgmd_class': ['DM', 'DM?']}},
                        {'range': {'splice_ai_delta_score': {'gte': 0.8}}},
                        {'terms': {'screen_region_type': ['dELS', 'DNase-only']}},
                    ]
                }
            },
            {'bool': {
                'should': [
                    {'bool': {
                        '_name': 'F000002_2',
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
                            {'bool': {'should': [{'bool': {
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
                                ],
                            }}, {'regexp': {
                                'clinvar_clinical_significance': '.*Likely_pathogenic.*|.*Pathogenic.*'
                            }}]}}
                        ],
                    }},
                    {'bool': {
                        'must': [
                            {'bool': {'should': [
                                {'term': {'samples_num_alt_1': 'NA20870'}},
                                {'term': {'samples_num_alt_2': 'NA20870'}}
                            ]}},
                            {'bool': {'should': [{'bool': {
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
                            }}, {'regexp': {
                                'clinvar_clinical_significance': '.*Likely_pathogenic.*|.*Pathogenic.*',
                            }}]}}
                        ],
                        '_name': 'F000003_3'
                    }},
                ]
            }}
        ], sort=[{'cadd_PHRED': {'order': 'desc', 'unmapped_type': 'keyword'}}, 'xpos', 'variantId'])

        # Test sort does not error on pagination
        query_variants(results_model, sort='cadd', num_results=2, page=2)

    @urllib3_responses.activate
    def test_sv_get_es_variants(self):
        setup_responses()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'new_structural_variants': ['NEW']},
            'freqs': {'sv_callset': {'af': 0.1}},
            'in_silico': {'strvctvre': '3.1', 'requireScore': True},
            'qualityFilter': {'min_qs': 20},
            'inheritance': {'mode': 'de_novo'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, _ = query_variants(results_model, num_results=2)

        self.assertListEqual(variants, [PARSED_SV_VARIANT])
        self.assertExecutedSearch(filters=[
            {'bool': {
                'should': [
                    {'bool': {'must_not': [{'exists': {'field': 'sf'}}]}},
                    {'range': {'sf': {'lte': 0.1}}}
                ]
            }},
            {'range': {'StrVCTVRE_score': {'gte': 3.1}}},
            {'bool': {
                'must': [
                    {'bool': {
                        'must_not': [{'term': {'samples': 'HG00732'}}, {'term': {'samples': 'HG00733'}}],
                        'must': [{'term': {'samples': 'HG00731'}}],
                    }},
                    {'bool': {
                        'must_not': [
                            {'term': {'samples_qs_0_to_10': 'HG00731'}},
                            {'term': {'samples_qs_10_to_20': 'HG00731'}},
                            {'term': {'samples_qs_0_to_10': 'HG00732'}},
                            {'term': {'samples_qs_10_to_20': 'HG00732'}},
                            {'term': {'samples_qs_0_to_10': 'HG00733'}},
                            {'term': {'samples_qs_10_to_20': 'HG00733'}},
                        ],
                        'must': [{'terms': {'samples_new_call': ['HG00731', 'HG00732', 'HG00733']}}],
                    }},
                ],
                '_name': 'F000002_2'
            }}
        ], index=SV_INDEX_NAME)

    @urllib3_responses.activate
    def test_sv_wgs_get_es_variants(self):
        self.families = Family.objects.filter(guid='F000014_14')
        setup_responses()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'structural': ['DUP', 'CPX']},
            'qualityFilter': {'min_gq_sv': 20},
            'inheritance': {'mode': 'de_novo'},
            'locus': {'rawVariantItems': 'rs9876'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, _ = query_variants(results_model, num_results=2)
        self.assertListEqual(variants, [PARSED_SV_WGS_VARIANT])

        self.assertExecutedSearch(filters=[
            {'terms': {'rsid': ['rs9876']}},
            {'terms': {'transcriptConsequenceTerms': ['CPX', 'DUP']}},
            {'bool': {
                'must': [{'term': {'samples': 'NA21234'}},
                    {'bool': {
                        'must_not': [
                            {'term': {'samples_gq_sv_0_to_5': 'NA21234'}},
                            {'term': {'samples_gq_sv_5_to_10': 'NA21234'}},
                            {'term': {'samples_gq_sv_10_to_15': 'NA21234'}},
                            {'term': {'samples_gq_sv_15_to_20': 'NA21234'}},
                        ],
                    }}
                ],
                '_name': 'F000014_14'
            }}
        ], index=SV_WGS_INDEX_NAME)

    @urllib3_responses.activate
    def test_multi_dataset_get_es_variants(self):
        setup_responses()

        search_model = VariantSearch.objects.create(search={})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, _ = query_variants(results_model, num_results=5)
        self.assertListEqual(variants, [PARSED_SV_VARIANT] + PARSED_NO_CONSEQUENCE_FILTER_VARIANTS + [PARSED_MITO_VARIANT])
        self.assertExecutedSearches([
            dict(filters=[], start_index=0, size=5, index=SV_INDEX_NAME),
            dict(filters=[], start_index=0, size=5, index=MITO_WGS_INDEX_NAME),
            dict(filters=[ALL_INHERITANCE_QUERY], start_index=0, size=5, index=INDEX_NAME),
        ])

        search_model.search['pathogenicity'] = {'clinvar': ['pathogenic']}
        search_model.save()
        _set_cache('search_results__{}__xpos'.format(results_model.guid), None)
        variants, _ = query_variants(results_model, num_results=5)
        self.assertListEqual(variants, PARSED_NO_CONSEQUENCE_FILTER_VARIANTS + [PARSED_MITO_VARIANT])
        path_filter = {'regexp': {
            'clinvar_clinical_significance': '.*Pathogenic.*'
        }}
        self.assertExecutedSearches([
            dict(filters=[path_filter], start_index=0, size=5, index=MITO_WGS_INDEX_NAME),
            dict(filters=[path_filter, ALL_INHERITANCE_QUERY], start_index=0, size=5, index=INDEX_NAME),
        ])

        # test with dataset filtering applied
        search_model.search['annotations'] = {'frameshift': ['frameshift_variant']}
        search_model.save()
        _set_cache('search_results__{}__xpos'.format(results_model.guid), None)

        query_variants(results_model, num_results=5)
        filter = {'bool': {'should': [{'terms': {'transcriptConsequenceTerms': ['frameshift_variant']}}, path_filter]}}
        self.assertExecutedSearches([
            dict(filters=[filter], start_index=0, size=5, index=MITO_WGS_INDEX_NAME),
            dict(filters=[filter, ALL_INHERITANCE_QUERY], start_index=0, size=5, index=INDEX_NAME),
        ])

        search_model.search['annotations'] = {
            'structural': ['DEL'], 'structural_consequence': ['MSV_EXON_OVERLAP', 'INTRAGENIC_EXON_DUP']}
        search_model.save()
        _set_cache('search_results__{}__xpos'.format(results_model.guid), None)

        query_variants(results_model, num_results=5)
        self.assertExecutedSearch(
            filters=[{'bool': {'should': [{'terms': {
                'transcriptConsequenceTerms': ['DEL', 'DUP_LOF', 'INTRAGENIC_EXON_DUP', 'MSV_EXON_OVERLAP', 'MSV_EXON_OVR']
            }}, path_filter]}}],
            start_index=0, size=5, index=SV_INDEX_NAME)

    @urllib3_responses.activate
    def test_multi_dataset_no_affected_inheritance_get_es_variants(self):
        setup_responses()
        # The family has multiple data types loaded but only one loaded in an affected individual
        Sample.objects.get(individual_id=4, elasticsearch_index=SV_INDEX_NAME).delete()
        Sample.objects.get(elasticsearch_index=MITO_WGS_INDEX_NAME).delete()

        search_model = VariantSearch.objects.create(search={'inheritance': {'mode': 'de_novo'}})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(guid='F000002_2'))

        query_variants(results_model, num_results=2)
        self.assertExecutedSearch(filters=[{'bool': {
            'must': [{'bool': {
                'minimum_should_match': 1,
                'should': [
                    {'term': {'samples_num_alt_1': 'HG00731'}},
                    {'term': {'samples_num_alt_2': 'HG00731'}},
                ],
                'must_not': [
                    {'term': {'samples_no_call': 'HG00732'}},
                    {'term': {'samples_num_alt_1': 'HG00732'}},
                    {'term': {'samples_num_alt_2': 'HG00732'}},
                    {'term': {'samples_no_call': 'HG00733'}},
                    {'term': {'samples_num_alt_1': 'HG00733'}},
                    {'term': {'samples_num_alt_2': 'HG00733'}},
                ],
            }}], '_name': 'F000002_2',
        }}])

    @urllib3_responses.activate
    def test_compound_het_get_es_variants(self):
        setup_responses()
        # Testing mito indices is done in other tests, it is helpful to have a strightforward single datatype test
        Sample.objects.get(elasticsearch_index=MITO_WGS_INDEX_NAME).delete()
        search_model = VariantSearch.objects.create(search={
            'qualityFilter': {'min_gq': 10},
            'annotations': {'frameshift': ['frameshift_variant']},
            'inheritance': {'mode': 'compound_het'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, total_results = query_variants(results_model, num_results=2)
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
            start_index=0,
            size=1
        )

        # test pagination does not fetch
        urllib3_responses.reset()
        query_variants(results_model, page=2, num_results=2)

    @urllib3_responses.activate
    def test_compound_het_get_es_variants_secondary_annotation(self):
        setup_responses()
        # Testing mito indices is done in other tests, it is helpful to have a strightforward single datatype test
        Sample.objects.get(elasticsearch_index=MITO_WGS_INDEX_NAME).delete()
        search_model = VariantSearch.objects.create(search={
            'qualityFilter': {'min_gq': 10},
            'annotations': {'frameshift': ['frameshift_variant'], 'splice_ai': '0.5'},
            'inheritance': {'mode': 'compound_het'},
            'annotations_secondary': {'other': ['intron']},
            'pathogenicity': {'clinvar': ['pathogenic'], 'hgmd': ['disease_causing']},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, total_results = query_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 1)
        self.assertListEqual(variants, [PARSED_COMPOUND_HET_VARIANTS])
        self.assertEqual(total_results, 1)

        self.assertCachedResults(results_model, {
            'grouped_results': [{'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS}],
            'total_results': 1,
        })

        annotation_query = {'bool': {'should': [
            {'regexp': {'clinvar_clinical_significance': '.*Pathogenic.*'}},
            {'terms': {'hgmd_class': ['DM']}},
            {'range': {'splice_ai_delta_score': {'gte': 0.5}}},
            {'terms': {'transcriptConsequenceTerms': ['frameshift_variant', 'intron']}},
        ]}}

        self.assertExecutedSearch(
            filters=[annotation_query, COMPOUND_HET_PATH_INHERITANCE_QUERY],
            gene_aggs=True,
            start_index=0,
            size=1
        )

        # test pagination does not fetch
        urllib3_responses.reset()
        query_variants(results_model, page=2, num_results=2)

        # variants require both primary and secondary annotations
        setup_responses()
        del search_model.search['pathogenicity']
        del search_model.search['annotations']['splice_ai']
        search_model.save()
        _set_cache('search_results__{}__xpos'.format(results_model.guid), None)

        variants, total_results = query_variants(results_model, num_results=2)
        self.assertIsNone(variants)
        self.assertEqual(total_results, 0)

        annotation_query = {'terms': {'transcriptConsequenceTerms': ['frameshift_variant', 'intron']}}

        self.assertExecutedSearch(
            filters=[annotation_query, COMPOUND_HET_INHERITANCE_QUERY],
            gene_aggs=True,
            start_index=0,
            size=1
        )

    @urllib3_responses.activate
    def test_recessive_get_es_variants(self):
        setup_responses()
        # Testing mito indices is done in other tests, it is helpful to have a strightforward single datatype test
        Sample.objects.get(elasticsearch_index=MITO_WGS_INDEX_NAME).delete()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'qualityFilter': {'min_gq': 10, 'vcf_filter': 'pass'},
            'inheritance': {'mode': 'recessive'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, total_results = query_variants(results_model, num_results=2)
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
                start_index=0,
                size=1
            ),
            dict(
                filters=[pass_filter_query, ANNOTATION_QUERY, RECESSIVE_INHERITANCE_QUERY], start_index=0, size=2,
            ),
        ])

        # test pagination

        variants, total_results = query_variants(results_model, page=3, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertDictEqual(variants[0], PARSED_VARIANTS[0])
        self.assertDictEqual(variants[1], PARSED_MULTI_SAMPLE_VARIANT)
        self.assertEqual(total_results, 5)

        self.assertCachedResults(results_model, {
            'compound_het_results': [],
            'variant_results': [],
            'grouped_results': [
                {'null': [PARSED_VARIANTS[0]]}, {'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS},
                {'null': [PARSED_VARIANTS[0]]}, {'null': [PARSED_MULTI_SAMPLE_VARIANT]}],
            'duplicate_doc_count': 1,
            'loaded_variant_counts': {'test_index_compound_het': {'total': 1, 'loaded': 1}, INDEX_NAME: {'loaded': 4, 'total': 5}},
            'total_results': 5,
        })

        self.assertExecutedSearches([dict(filters=[pass_filter_query, ANNOTATION_QUERY, RECESSIVE_INHERITANCE_QUERY], start_index=2, size=4)])

        urllib3_responses.reset()
        query_variants(results_model, page=2, num_results=2)

    @urllib3_responses.activate
    def test_multi_datatype_recessive_get_es_variants(self):
        setup_responses()
        # Testing mito indices is done in other tests, it is helpful to have a strightforward single datatype test
        Sample.objects.get(elasticsearch_index=MITO_WGS_INDEX_NAME).delete()
        search_model = VariantSearch.objects.create(search={
            'inheritance': {'mode': 'recessive'},
            'annotations': {'frameshift': ['frameshift_variant'], 'structural': ['DEL']}
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, _ = query_variants(results_model, num_results=10)
        self.assertEqual(len(variants), 4)
        self.assertDictEqual(variants[0], PARSED_SV_VARIANT)
        self.assertDictEqual(variants[1], PARSED_VARIANTS[0])
        self.assertDictEqual(variants[2][0], PARSED_SV_COMPOUND_HET_VARIANTS[0])
        self.assertDictEqual(variants[2][1], PARSED_SV_COMPOUND_HET_VARIANTS[1])
        self.assertDictEqual(variants[3], PARSED_VARIANTS[1])

        annotations_q = {'terms': {'transcriptConsequenceTerms': ['DEL', 'frameshift_variant']}}
        self.assertExecutedSearches([
            dict(
                filters=[
                    annotations_q,
                    {'bool': {
                        '_name': 'F000002_2',
                        'must': [{
                            'bool': {
                                'minimum_should_match': 1,
                                'should': [
                                    {'term': {'samples_cn_0': 'HG00731'}},
                                    {'term': {'samples_cn_2': 'HG00731'}},
                                    {'term': {'samples_cn_gte_4': 'HG00731'}},
                                ],
                                'must_not': [
                                    {'term': {'samples_cn_0': 'HG00732'}},
                                    {'term': {'samples_cn_gte_4': 'HG00732'}},
                                    {'term': {'samples_cn_0': 'HG00733'}},
                                    {'term': {'samples_cn_gte_4': 'HG00733'}},
                                ]
                            }
                        }]
                    }}
                ], start_index=0, size=10, index=SV_INDEX_NAME,
            ),
            dict(
                filters=[
                    annotations_q,
                    {'bool': {
                    '_name': 'F000002_2',
                    'must': [
                        {'bool': {
                            'should': [
                                {'bool': {
                                    'minimum_should_match': 1,
                                    'must_not': [
                                        {'term': {'samples_no_call': 'HG00732'}},
                                        {'term': {'samples_num_alt_2': 'HG00732'}},
                                        {'term': {'samples_no_call': 'HG00733'}},
                                        {'term': {'samples_num_alt_2': 'HG00733'}}
                                    ],
                                    'should': [
                                        {'term': {'samples_num_alt_1': 'HG00731'}},
                                        {'term': {'samples_num_alt_2': 'HG00731'}},
                                    ]

                                }},
                                {'term': {'samples': 'HG00731'}},
                            ]
                        }},
                    ]
                    }},
                 ],
                gene_aggs=True,
                start_index=0,
                size=1,
                index=','.join([INDEX_NAME, SV_INDEX_NAME]),
            ),
            dict(
                filters=[
                    annotations_q,
                    {'bool': {'_name': 'F000003_3', 'must': [{'term': {'samples_num_alt_1': 'NA20870'}}]}},
                ],
                gene_aggs=True,
                start_index=0,
                size=1
            ),
            dict(
                filters=[
                    annotations_q,
                    {
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
                                            'must': [{'term': {'samples_num_alt_2': 'HG00731'}}]
                                        }},
                                    ]
                                }},
                                {'bool': {
                                    '_name': 'F000003_3',
                                    'must': [
                                        {'term': {'samples_num_alt_2': 'NA20870'}},
                                    ]
                                }},
                            ]
                        }
                    }
                ], start_index=0, size=10,
            ),
        ])

    @urllib3_responses.activate
    def test_multi_datatype_secondary_annotations_recessive_get_es_variants(self):
        setup_responses()
        # Testing mito indices is done in other tests, it is helpful to have a strightforward single datatype test
        Sample.objects.get(elasticsearch_index=MITO_WGS_INDEX_NAME).delete()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'structural': ['DEL']},
            'annotations_secondary': {'frameshift': ['frameshift_variant']},
            'inheritance': {'mode': 'recessive'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, _ = query_variants(results_model, num_results=10)
        self.assertEqual(len(variants), 2)
        self.assertDictEqual(variants[0], PARSED_SV_VARIANT)
        self.assertDictEqual(variants[1][0], PARSED_SV_COMPOUND_HET_VARIANTS[0])
        self.assertDictEqual(variants[1][1], PARSED_SV_COMPOUND_HET_VARIANTS[1])

        annotation_secondary_query = {'terms': {'transcriptConsequenceTerms': ['DEL', 'frameshift_variant']}}

        self.assertExecutedSearches([
            dict(
                filters=[
                    {'terms': {'transcriptConsequenceTerms': ['DEL']}},
                    {'bool': {
                        '_name': 'F000002_2',
                        'must': [{
                            'bool': {
                                'minimum_should_match': 1,
                                'should': [
                                    {'term': {'samples_cn_0': 'HG00731'}},
                                    {'term': {'samples_cn_2': 'HG00731'}},
                                    {'term': {'samples_cn_gte_4': 'HG00731'}},
                                ],
                                'must_not': [
                                    {'term': {'samples_cn_0': 'HG00732'}},
                                    {'term': {'samples_cn_gte_4': 'HG00732'}},
                                    {'term': {'samples_cn_0': 'HG00733'}},
                                    {'term': {'samples_cn_gte_4': 'HG00733'}},
                                ]
                            }
                        }]
                    }}
                ], start_index=0, size=10, index=SV_INDEX_NAME,
            ),
            dict(
                filters=[annotation_secondary_query, {'bool': {
                    '_name': 'F000002_2',
                    'must': [
                        {'bool': {
                            'should': [
                                {'bool': {
                                    'minimum_should_match': 1,
                                    'must_not': [
                                        {'term': {'samples_no_call': 'HG00732'}},
                                        {'term': {'samples_num_alt_2': 'HG00732'}},
                                        {'term': {'samples_no_call': 'HG00733'}},
                                        {'term': {'samples_num_alt_2': 'HG00733'}}
                                    ],
                                    'should': [
                                        {'term': {'samples_num_alt_1': 'HG00731'}},
                                        {'term': {'samples_num_alt_2': 'HG00731'}},
                                    ]
                                }},
                                {'term': {'samples': 'HG00731'}},
                            ]
                        }},
                    ]
                }},
                         ],
                gene_aggs=True,
                start_index=0,
                size=1,
                index=','.join([INDEX_NAME, SV_INDEX_NAME]),
            ),
            dict(
                filters=[
                    annotation_secondary_query,
                    {'bool': {'_name': 'F000003_3', 'must': [{'term': {'samples_num_alt_1': 'NA20870'}}]}},
                ],
                gene_aggs=True,
                start_index=0,
                size=1
            ),
        ])

    @urllib3_responses.activate
    def test_multi_datatype_secondary_annotations_comp_het_get_es_variants(self):
        setup_responses()
        # Testing mito indices is done in other tests, it is helpful to have a strightforward single datatype test
        Sample.objects.get(elasticsearch_index=MITO_WGS_INDEX_NAME).delete()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'structural': ['DEL'], 'SCREEN': ['dELS']},
            'annotations_secondary': {'structural_consequence': ['LOF']},
            'inheritance': {'mode': 'compound_het'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        query_variants(results_model, num_results=10)

        annotation_secondary_query = {'bool': {'should': [
            {'terms': {'transcriptConsequenceTerms': ['DEL', 'LOF']}},
            {'terms': {'screen_region_type': ['dELS']}}]}}

        self.assertExecutedSearches([
            dict(
                filters=[annotation_secondary_query, {'bool': {
                    '_name': 'F000002_2',
                    'must': [
                        {'bool': {
                            'should': [
                                {'bool': {
                                    'minimum_should_match': 1,
                                    'must_not': [
                                        {'term': {'samples_no_call': 'HG00732'}},
                                        {'term': {'samples_num_alt_2': 'HG00732'}},
                                        {'term': {'samples_no_call': 'HG00733'}},
                                        {'term': {'samples_num_alt_2': 'HG00733'}}
                                    ],
                                    'should': [
                                        {'term': {'samples_num_alt_1': 'HG00731'}},
                                        {'term': {'samples_num_alt_2': 'HG00731'}},
                                    ]
                                }},
                                {'term': {'samples': 'HG00731'}},
                            ]
                        }},
                    ]
                }},
                         ],
                gene_aggs=True,
                start_index=0,
                size=1,
                index=','.join([INDEX_NAME, SV_INDEX_NAME]),
            ),
            dict(
                filters=[
                    annotation_secondary_query,
                    {'bool': {'_name': 'F000003_3', 'must': [{'term': {'samples_num_alt_1': 'NA20870'}}]}},
                ],
                gene_aggs=True,
                start_index=0,
                size=1
            ),
        ])

    @urllib3_responses.activate
    def test_all_samples_all_inheritance_get_es_variants(self):
        setup_responses()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'locus': {'rawVariantItems': '1-248367227-TC-T,2-103343353-GAGA-G'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(project__guid='R0001_1kg'))

        variants, total_results = query_variants(results_model, num_results=2)
        self.assertListEqual(variants, PARSED_VARIANTS)
        self.assertEqual(total_results, 5)

        self.assertExecutedSearch(index=INDEX_NAME, size=2, filters=[
            {'terms': {'variantId': ['1-248367227-TC-T', '2-103343353-GAGA-G']}}, ANNOTATION_QUERY])

    @urllib3_responses.activate
    def test_all_samples_any_affected_get_es_variants(self):
        setup_responses()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']}, 'inheritance': {'mode': 'any_affected'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(project__guid='R0001_1kg'))

        variants, total_results = query_variants(results_model, num_results=2)
        self.assertListEqual(variants, PARSED_ANY_AFFECTED_VARIANTS)
        self.assertEqual(total_results, 10)

        self.assertExecutedSearches([dict(filters=[
            ANNOTATION_QUERY,
            {'bool': {
                'should': [
                    {'terms': {'samples_num_alt_1': ['HG00731']}},
                    {'terms': {'samples_num_alt_2': ['HG00731']}},
                    {'terms': {'samples': ['HG00731']}},
                ]
            }}
        ], index=MITO_WGS_INDEX_NAME, start_index=0, size=2), dict(filters=[
            ANNOTATION_QUERY,
            {'bool': {
                'should': [
                    {'terms': {'samples_num_alt_1': ['HG00731', 'NA19675', 'NA20870']}},
                    {'terms': {'samples_num_alt_2': ['HG00731', 'NA19675', 'NA20870']}},
                    {'terms': {'samples': ['HG00731', 'NA19675', 'NA20870']}},
                ]
            }}
        ], index=INDEX_NAME, start_index=0, size=2)])

    @mock.patch('seqr.utils.search.elasticsearch.es_search.MAX_SEARCH_CLAUSES', 1)
    @urllib3_responses.activate
    def test_many_family_inheitance_get_es_variants(self):
        setup_responses()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']}, 'inheritance': {'mode': 'recessive'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(self.families)

        variants, total_results = query_variants(results_model, num_results=2)

        self.assertEqual(len(variants), 2)
        self.assertEqual(total_results, 14)
        self.assertDictEqual(variants[0], PARSED_MULTI_SAMPLE_VARIANT_0)
        self.assertListEqual(variants[1], PARSED_MULTI_SAMPLE_COMPOUND_HET_VARIANTS)

        self.assertCachedResults(results_model, {
            'compound_het_results': [],
            'variant_results': [PARSED_MULTI_SAMPLE_VARIANT, PARSED_MITO_VARIANT],
            'grouped_results': [{'null': [PARSED_MULTI_SAMPLE_VARIANT_0]}, {'ENSG00000228198': PARSED_MULTI_SAMPLE_COMPOUND_HET_VARIANTS}],
            'duplicate_doc_count': 3,
            'loaded_variant_counts': {'test_index_compound_het': {'total': 2, 'loaded': 2},
                                      MITO_WGS_INDEX_NAME: {'loaded': 1, 'total': 5},
                                      INDEX_NAME: {'loaded': 4, 'total': 10}},
            'total_results': 14,
        })

        self.assertExecutedSearches([
            dict(
                filters=[
                    ANNOTATION_QUERY,
                    {
                        'bool': {
                            '_name': 'F000002_2',
                            'must': [
                                {'term': {'samples_num_alt_1': 'HG00731'}},
                            ]
                        }
                    },
                ],
                index=MITO_WGS_INDEX_NAME,
                gene_aggs=True,
                start_index=0,
                size=1
            ),
            dict(
                filters=[
                    ANNOTATION_QUERY,
                    {
                        'bool': {
                            '_name': 'F000002_2',
                            'must': [
                                {'term': {'samples_num_alt_2': 'HG00731'}},
                            ]
                        }
                    },
                ],
                index=MITO_WGS_INDEX_NAME,
                start_index=0,
                size=2,
            ),
            dict(
                filters=[
                    ANNOTATION_QUERY,
                    {
                        'bool': {
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
                            ]
                        },
                    },
                ],
                gene_aggs=True,
                start_index=0,
                size=1
            ),
            dict(
                filters=[
                    ANNOTATION_QUERY,
                    {
                        'bool': {
                            '_name': 'F000003_3',
                            'must': [{'term': {'samples_num_alt_1': 'NA20870'}}],
                        },
                    },
                ],
                gene_aggs=True,
                start_index=0,
                size=1
            ),
            dict(
                filters=[
                    ANNOTATION_QUERY,
                    {
                        'bool': {
                            '_name': 'F000002_2',
                            'must': [
                                {'bool': {
                                    'must_not': [
                                        {'term': {'samples_no_call': 'HG00732'}},
                                        {'term': {'samples_num_alt_2': 'HG00732'}},
                                        {'term': {'samples_no_call': 'HG00733'}},
                                        {'term': {'samples_num_alt_2': 'HG00733'}}
                                    ],
                                    'must': [{'term': {'samples_num_alt_2': 'HG00731'}}]
                                }},
                            ]
                        }
                    },
                ],
                start_index=0,
                size=2,
            ),
            dict(
                filters=[
                    ANNOTATION_QUERY,
                    {
                        'bool': {
                            '_name': 'F000003_3',
                            'must': [
                               {'term': {'samples_num_alt_2': 'NA20870'}},
                            ]
                        }
                    },
                ],
                start_index=0,
                size=2,
            ),
        ])

    @urllib3_responses.activate
    def test_multi_project_get_es_variants(self):
        setup_responses()
        # Testing mito indices is done in other tests, it is helpful to have a strightforward single datatype test
        Sample.objects.get(elasticsearch_index=MITO_WGS_INDEX_NAME).delete()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'qualityFilter': {'min_gq': 10},
            'inheritance': {'mode': 'recessive'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(guid__in=['F000011_11', 'F000003_3', 'F000002_2']))

        variants, total_results = query_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertDictEqual(variants[0], PARSED_VARIANTS[0])
        self.assertDictEqual(variants[1][0], PARSED_COMPOUND_HET_VARIANTS_PROJECT_2[0])
        self.assertDictEqual(variants[1][1], PARSED_COMPOUND_HET_VARIANTS_PROJECT_2[1])
        self.assertEqual(total_results, 11)

        self.assertCachedResults(results_model, {
            'compound_het_results': [{'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT}],
            'variant_results': [PARSED_MULTI_INDEX_VARIANT],
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
        self.assertTrue('index_metadata__{}'.format(INDEX_NAME) in REDIS_CACHE)
        self.assertTrue('index_metadata__{}'.format(SECOND_INDEX_NAME) in REDIS_CACHE)

        project_2_search = dict(
            filters=[
                ANNOTATION_QUERY,
                {'bool': {
                    'must': [
                        {'term': {'samples_num_alt_2': 'NA20885'}},
                        {'bool': {
                            'must_not': [
                                {'term': {'samples_gq_0_to_5': 'NA20885'}},
                                {'term': {'samples_gq_5_to_10': 'NA20885'}},
                            ]
                        }}
                    ],
                    '_name': 'F000011_11'
                }}
            ], start_index=0, size=2, index=SECOND_INDEX_NAME)
        project_1_search = dict(
            filters=[
                ANNOTATION_QUERY,
                RECESSIVE_INHERITANCE_QUERY,
            ], start_index=0, size=2, index=INDEX_NAME)
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
                gene_aggs=True, start_index=0, size=1, index=SECOND_INDEX_NAME,
            ),
            project_2_search,
            dict(
                filters=[ANNOTATION_QUERY, COMPOUND_HET_INHERITANCE_QUERY],
                gene_aggs=True, start_index=0, size=1, index=INDEX_NAME,
            ),
            project_1_search,
        ])

        # test pagination
        variants, total_results = query_variants(results_model, num_results=2, page=2)
        self.assertEqual(len(variants), 2)
        self.assertListEqual(variants, [PARSED_VARIANTS[0], PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT])
        self.assertEqual(total_results, 9)

        cache_results = {
            'compound_het_results': [],
            'variant_results': [PARSED_MULTI_SAMPLE_MULTI_INDEX_VARIANT],
            'grouped_results': [
                {'null': [PARSED_VARIANTS[0]]},
                {'ENSG00000135953': PARSED_COMPOUND_HET_VARIANTS_PROJECT_2},
                {'null': [PARSED_VARIANTS[0]]},
                {'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS_MULTI_PROJECT}
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
        query_variants(results_model, num_results=2, page=3)
        project_2_search['start_index'] = 2
        project_2_search['size'] = 4
        self.assertExecutedSearches([project_2_search])

    @urllib3_responses.activate
    def test_multi_project_all_samples_all_inheritance_get_es_variants(self):
        setup_responses()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(project__id__in=[1, 3]))

        variants, total_results = query_variants(results_model, num_results=2)
        expected_variants = [PARSED_VARIANTS[0], PARSED_MULTI_INDEX_VARIANT]
        self.assertListEqual(variants, expected_variants)
        self.assertEqual(total_results, 4)

        cached_variants = expected_variants + [PARSED_MITO_VARIANT]
        self.assertCachedResults(results_model, {
            'all_results': cached_variants,
            'duplicate_doc_count': 1,
            'total_results': 4,
        })

        self.assertExecutedSearch(
            index=','.join([INDEX_NAME, SECOND_INDEX_NAME, MITO_WGS_INDEX_NAME]),
            filters=[ANNOTATION_QUERY],
            size=6,
        )

        # test pagination
        variants, total_results = query_variants(results_model, num_results=2, page=2)
        expected_variants = [PARSED_MITO_VARIANT, PARSED_VARIANTS[0]]
        self.assertListEqual(variants, expected_variants)
        self.assertEqual(total_results, 3)

        self.assertCachedResults(results_model, {
            'all_results': cached_variants + cached_variants,
            'duplicate_doc_count': 2,
            'total_results': 3,
        })

        self.assertExecutedSearch(
            index=','.join([INDEX_NAME, MITO_WGS_INDEX_NAME, SECOND_INDEX_NAME]),
            filters=[ANNOTATION_QUERY],
            size=8,
            start_index=4,
        )

        # test skipping page fetches all consecutively
        _set_cache('search_results__{}__xpos'.format(results_model.guid), None)
        query_variants(results_model, num_results=2, page=2)
        self.assertExecutedSearch(
            index=','.join([INDEX_NAME, MITO_WGS_INDEX_NAME, SECOND_INDEX_NAME]),
            filters=[ANNOTATION_QUERY],
            size=12,
        )

    @urllib3_responses.activate
    def test_multi_project_all_samples_any_affected_get_es_variants(self):
        setup_responses()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']}, 'inheritance': {'mode': 'any_affected'},
        },
        )
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(project__id__in=[1, 3]))

        variants, total_results = query_variants(results_model, num_results=2)
        expected_variants = [PARSED_VARIANTS[0], PARSED_ANY_AFFECTED_MULTI_INDEX_VERSION_VARIANT]
        self.assertListEqual(variants, expected_variants)
        self.assertEqual(total_results, 14)

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
                ], start_index=0, size=2, index=SECOND_INDEX_NAME),
            dict(
                filters=[
                    ANNOTATION_QUERY,
                    {'bool': {
                        'should': [
                            {'terms': {'samples_num_alt_1': ['HG00731']}},
                            {'terms': {'samples_num_alt_2': ['HG00731']}},
                            {'terms': {'samples': ['HG00731']}},
                        ]
                    }}
                ], start_index=0, size=2, index=MITO_WGS_INDEX_NAME),
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
                ], start_index=0, size=2, index=INDEX_NAME)
        ])

    @mock.patch('seqr.utils.search.elasticsearch.es_search.MAX_INDEX_SEARCHES', 1)
    @urllib3_responses.activate
    def test_multi_project_prefilter_indices_get_es_variants(self):
        setup_responses()
        search_model = VariantSearch.objects.create(search={
            'inheritance': {'mode': 'de_novo'},
            'qualityFilter': {'min_gq': 10},
            'locus': {'rawItems': 'ENSG00000228198'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(project__id__in=[1, 3]))

        _, total_results = query_variants(results_model, num_results=2)
        self.assertEqual(total_results, 14)
        self.assertTrue('index_metadata__{},{},{}'.format(INDEX_NAME, MITO_WGS_INDEX_NAME, SV_INDEX_NAME) in REDIS_CACHE)

        gene_filter = {'terms': {'geneIds': ['ENSG00000228198']}}
        prefilter_search = dict(
            filters=[gene_filter], index=f'{SV_INDEX_NAME},{MITO_WGS_INDEX_NAME},{SECOND_INDEX_NAME},{INDEX_NAME}',
            size=200, expected_source_fields=set(),
        )
        sv_search = dict(
            filters=[
                gene_filter,
                {'bool': {
                    'must': [
                        {'bool': {
                            'must_not': [{'term': {'samples': 'HG00732'}}, {'term': {'samples': 'HG00733'}}],
                            'must': [{'term': {'samples': 'HG00731'}}],
                        }},
                        {'bool': {
                            'must_not': [
                                {'term': {'samples_gq_0_to_5': 'HG00731'}},
                                {'term': {'samples_gq_5_to_10': 'HG00731'}},
                                {'term': {'samples_gq_0_to_5': 'HG00732'}},
                                {'term': {'samples_gq_5_to_10': 'HG00732'}},
                                {'term': {'samples_gq_0_to_5': 'HG00733'}},
                                {'term': {'samples_gq_5_to_10': 'HG00733'}},
                            ],
                        }},
                    ],
                    '_name': 'F000002_2'
                }}
            ], start_index=0, size=2, index=SV_INDEX_NAME)
        num_calls = 3
        self.assertEqual(len(urllib3_responses.calls), num_calls)
        self.assertExecutedSearch(call_index=num_calls-2, **prefilter_search)
        # Search total is greater than returned hits, so proceed with regular multi-search
        self.assertExecutedSearches([
            sv_search,
            dict(filters=[
                gene_filter,
                {
                    'bool': {'must': [
                        {'bool': {'should': [
                            {'term': {'samples_num_alt_1': 'NA20885'}},
                            {'term': {'samples_num_alt_2': 'NA20885'}},
                        ]}}, {'bool': {'must_not': [
                            {'term': {'samples_gq_0_to_5': 'NA20885'}},
                            {'term': {'samples_gq_5_to_10': 'NA20885'}},
                        ]}}
                    ],
                        '_name': 'F000011_11'
                    }}
            ], start_index=0, size=2, index=SECOND_INDEX_NAME),
            dict(filters=[
                gene_filter,
                {
                    'bool': {'must': [
                        {'bool': {'should': [
                            {'term': {'samples_num_alt_1': 'HG00731'}},
                            {'term': {'samples_num_alt_2': 'HG00731'}},
                        ]}}, {'bool': {'must_not': [
                            {'term': {'samples_gq_0_to_5': 'HG00731'}},
                            {'term': {'samples_gq_5_to_10': 'HG00731'}},
                            {'term': {'samples_gq_0_to_5': 'HG00732'}},
                            {'term': {'samples_gq_5_to_10': 'HG00732'}},
                            {'term': {'samples_gq_0_to_5': 'HG00733'}},
                            {'term': {'samples_gq_5_to_10': 'HG00733'}},
                        ]}}
                    ],
                        '_name': 'F000002_2'
                    }}], start_index=0, size=2, index=MITO_WGS_INDEX_NAME),
            dict(filters=[
                    gene_filter,
                    {'bool': {'should': [
                        {'bool': {'must': [
                            {'bool': {'should': [
                                {'term': {'samples_num_alt_1': 'NA19675'}},
                                {'term': {'samples_num_alt_2': 'NA19675'}},
                            ]}}, {'bool': {'must_not': [
                                {'term': {'samples_gq_0_to_5': 'NA19675'}},
                                {'term': {'samples_gq_5_to_10': 'NA19675'}},
                            ]}}], '_name': 'F000001_1'}},
                        {'bool': {'must': [
                            {'bool': {'should': [
                                {'term': {'samples_num_alt_1': 'HG00731'}},
                                {'term': {'samples_num_alt_2': 'HG00731'}},
                            ], 'must_not': [
                                {'term': {'samples_no_call': 'HG00732'}},
                                {'term': {'samples_num_alt_1': 'HG00732'}},
                                {'term': {'samples_num_alt_2': 'HG00732'}},
                                {'term': {'samples_no_call': 'HG00733'}},
                                {'term': {'samples_num_alt_1': 'HG00733'}},
                                {'term': {'samples_num_alt_2': 'HG00733'}},
                            ], 'minimum_should_match': 1}},
                            {'bool': {
                                'must_not': [
                                    {'term': {'samples_gq_0_to_5': 'HG00731'}},
                                    {'term': {'samples_gq_5_to_10': 'HG00731'}},
                                    {'term': {'samples_gq_0_to_5': 'HG00732'}},
                                    {'term': {'samples_gq_5_to_10': 'HG00732'}},
                                    {'term': {'samples_gq_0_to_5': 'HG00733'}},
                                    {'term': {'samples_gq_5_to_10': 'HG00733'}},
                                ],
                            }},
                        ],
                            '_name': 'F000002_2'
                        }},
                        {'bool': {'must': [
                            {'bool': {'should': [
                                {'term': {'samples_num_alt_1': 'NA20870'}},
                                {'term': {'samples_num_alt_2': 'NA20870'}},
                            ]}}, {'bool': {'must_not': [
                                {'term': {'samples_gq_0_to_5': 'NA20870'}},
                                {'term': {'samples_gq_5_to_10': 'NA20870'}},
                            ]}}], '_name': 'F000003_3'}},
                    ]}}], start_index=0, size=2, index=INDEX_NAME),
        ])

        # Test successful prefilter
        _set_cache('search_results__{}__xpos'.format(results_model.guid), None)
        gene_filter['terms']['geneIds'] = ['ENSG00000186092']
        search_model.search['locus']['rawItems'] = 'ENSG00000186092'
        search_model.save()

        _, total_results = query_variants(results_model, num_results=2)
        self.assertEqual(total_results, 1)
        num_calls += 2
        self.assertEqual(len(urllib3_responses.calls), num_calls)
        self.assertExecutedSearch(call_index=num_calls-2, **prefilter_search)
        sv_search['query'] = [{'ids': {'values': ['prefix_19107_DEL']}}]
        self.assertExecutedSearches([sv_search])

        # Test no results in prefilter
        _set_cache('search_results__{}__xpos'.format(results_model.guid), None)
        gene_filter['terms']['geneIds'] = ['ENSG00000269732']
        search_model.search['locus']['rawItems'] = 'ENSG00000269732'
        search_model.save()

        _, total_results = query_variants(results_model, num_results=2)
        self.assertEqual(total_results, 0)
        # Only the prefliter search is run, no multi-search
        self.assertEqual(len(urllib3_responses.calls), num_calls + 1)
        self.assertExecutedSearch(**prefilter_search)


    @mock.patch('seqr.utils.search.elasticsearch.es_search.MAX_VARIANTS', 3)
    @urllib3_responses.activate
    def test_skip_genotype_filter(self):
        setup_responses()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'locus': {'rawItems': 'ENSG00000228198'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(project__id__in=[1, 3]))

        variants, _ = query_variants(results_model, num_results=2, skip_genotype_filter=True)
        expected_transcript_variant = deepcopy(PARSED_VARIANTS[0])
        expected_transcript_variant['selectedMainTranscriptId'] = PARSED_VARIANTS[1]['selectedMainTranscriptId']
        self.assertListEqual(variants, [expected_transcript_variant, PARSED_MULTI_INDEX_VARIANT])
        self.assertExecutedSearch(
            index=','.join([INDEX_NAME, MITO_WGS_INDEX_NAME, SECOND_INDEX_NAME]),
            filters=[{'terms': {'geneIds': ['ENSG00000228198']}}, ANNOTATION_QUERY],
            size=3,
        )

        # test with inheritance override
        search_model.search['inheritance'] = {'mode': 'any_affected'}
        search_model.save()
        _set_cache('search_results__{}__xpos'.format(results_model.guid), None)
        query_variants(results_model, num_results=2, skip_genotype_filter=True)

        self.assertExecutedSearches([
            dict(
                filters=[
                    {'terms': {'geneIds': ['ENSG00000228198']}},
                    ANNOTATION_QUERY,
                    {'bool': {
                        'should': [
                            {'terms': {'samples_num_alt_1': ['NA20885']}},
                            {'terms': {'samples_num_alt_2': ['NA20885']}},
                            {'terms': {'samples': ['NA20885']}},
                        ]
                    }}
                ], start_index=0, size=2, index=SECOND_INDEX_NAME),
            dict(
                filters=[
                    {'terms': {'geneIds': ['ENSG00000228198']}},
                    ANNOTATION_QUERY,
                    {'bool': {
                        'should': [
                            {'terms': {'samples_num_alt_1': ['HG00731']}},
                            {'terms': {'samples_num_alt_2': ['HG00731']}},
                            {'terms': {'samples': ['HG00731']}},
                        ]
                    }}
                ], start_index=0, size=2, index=MITO_WGS_INDEX_NAME),
            dict(
                filters=[
                    {'terms': {'geneIds': ['ENSG00000228198']}},
                    ANNOTATION_QUERY,
                    {'bool': {
                        'should': [
                            {'terms': {'samples_num_alt_1': ['HG00731', 'NA19675', 'NA20870']}},
                            {'terms': {'samples_num_alt_2': ['HG00731', 'NA19675', 'NA20870']}},
                            {'terms': {'samples': ['HG00731', 'NA19675', 'NA20870']}},
                        ]
                    }},
                ], start_index=0, size=2, index=INDEX_NAME)
        ])

    @mock.patch('seqr.utils.search.elasticsearch.es_search.LIFTOVER_GRCH38_TO_GRCH37', None)
    @mock.patch('seqr.utils.search.elasticsearch.es_search.LiftOver')
    @urllib3_responses.activate
    def test_get_lifted_grch38_variants(self, mock_liftover):
        setup_responses()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(guid__in=['F000011_11']))

        Project.objects.filter(guid='R0003_test').update(genome_version='38')
        Sample.objects.filter(elasticsearch_index=SECOND_INDEX_NAME).update(elasticsearch_index=HG38_INDEX_NAME)

        mock_liftover.side_effect = Exception()
        expected_no_lift_grch38_variant = deepcopy(PARSED_HG38_VARIANT)
        expected_no_lift_grch38_variant.update({
            'liftedOverGenomeVersion': None,
            'liftedOverChrom': None,
            'liftedOverPos': None,
        })
        variants, _ = query_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertListEqual(variants, [PARSED_HG38_VARIANT, expected_no_lift_grch38_variant])
        self.assertIsNone(_liftover_grch38_to_grch37())
        mock_liftover.assert_called_with('hg38', 'hg19')

        _set_cache('search_results__{}__xpos'.format(results_model.guid), None)
        mock_liftover.side_effect = None
        mock_liftover.return_value.convert_coordinate.side_effect = lambda chrom, pos: [[chrom, pos - 10]]
        variants, _ = query_variants(results_model, num_results=2)
        self.assertEqual(len(variants), 2)
        self.assertListEqual(variants, [PARSED_HG38_VARIANT, PARSED_HG38_VARIANT])
        self.assertIsNotNone(_liftover_grch38_to_grch37())
        mock_liftover.assert_called_with('hg38', 'hg19')

    @mock.patch('seqr.utils.search.elasticsearch.es_search.MAX_INDEX_NAME_LENGTH', 30)
    @urllib3_responses.activate
    def test_get_es_variants_create_index_alias(self):
        search_model = VariantSearch.objects.create(search={})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(project__id__in=[1, 3]))

        setup_search_responses()
        urllib3_responses.add_json(
            '/{}/_mapping'.format(INDEX_ALIAS), {k: {'mappings': v} for k, v in CORE_INDEX_METADATA.items()})
        urllib3_responses.add_json('/_aliases', {'success': True}, method=urllib3_responses.POST)

        query_variants(results_model, num_results=2)

        self.assertExecutedSearch(index=INDEX_ALIAS, size=8)
        self.assertDictEqual(urllib3_responses.call_request_json(index=0), {
            'actions': [{'add': {'indices': [INDEX_NAME, MITO_WGS_INDEX_NAME, SECOND_INDEX_NAME, SV_INDEX_NAME], 'alias': INDEX_ALIAS}}]})

    @urllib3_responses.activate
    def test_get_es_variants_search_index_alias(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'inheritance': {'mode': 'de_novo'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(guid__in=['F000011_11']))

        setup_search_responses()
        urllib3_responses.add_json('/{}/_mapping'.format(SECOND_INDEX_NAME), {
            k: {'mappings': INDEX_METADATA[SECOND_INDEX_NAME]} for k in SUB_INDICES})

        query_variants(results_model, num_results=2)

        expected_search = {
            'start_index': 0, 'size': 2, 'filters': [ANNOTATION_QUERY, {
                'bool': {'must': [
                    {'bool': {'should': [
                        {'term': {'samples_num_alt_1': 'NA20885'}},
                        {'term': {'samples_num_alt_2': 'NA20885'}},
                    ]}}
                ],
                '_name': 'F000011_11'
            }}]
        }
        self.assertExecutedSearches([
            dict(index=SUB_INDICES[1], **expected_search),
            dict(index=SUB_INDICES[0], **expected_search),
        ])
        _set_cache('index_metadata__{}'.format(SECOND_INDEX_NAME), None)

    @urllib3_responses.activate
    def test_get_es_variants_search_multiple_index_alias(self):
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'inheritance': {'mode': 'de_novo'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(guid__in=['F000003_3', 'F000011_11']))

        setup_search_responses()
        mappings = {k: {'mappings': INDEX_METADATA[INDEX_NAME]} for k in SUB_INDICES}
        mappings.update({k: {'mappings': INDEX_METADATA[SECOND_INDEX_NAME]} for k in SECOND_SUB_INDICES})
        urllib3_responses.add_json('/{},{}/_mapping'.format(INDEX_NAME, SECOND_INDEX_NAME), mappings)
        aliases = {k: {'aliases': {INDEX_NAME: {}}} for k in SUB_INDICES}
        aliases.update({k: {'aliases': {SECOND_INDEX_NAME: {}, INDEX_ALIAS: {}}} for k in SECOND_SUB_INDICES})
        urllib3_responses.add_json('/{},{}/_alias'.format(INDEX_NAME, SECOND_INDEX_NAME), aliases)

        query_variants(results_model, num_results=2)

        second_alias_expected_search = {
            'start_index': 0, 'size': 2, 'filters': [ANNOTATION_QUERY, {
                'bool': {'must': [
                    {'bool': {'should': [
                        {'term': {'samples_num_alt_1': 'NA20885'}},
                        {'term': {'samples_num_alt_2': 'NA20885'}},
                    ]}}
                ],
                    '_name': 'F000011_11'
                }}]
        }
        first_alias_expected_search = {
            'start_index': 0, 'size': 2, 'filters': [ANNOTATION_QUERY, {
                'bool': {'must': [
                    {'bool': {'should': [
                        {'term': {'samples_num_alt_1': 'NA20870'}},
                        {'term': {'samples_num_alt_2': 'NA20870'}},
                    ]}}
                ],
                    '_name': 'F000003_3'
                }}]
        }
        self.assertExecutedSearches([
            dict(index=SECOND_SUB_INDICES[1], **second_alias_expected_search),
            dict(index=SECOND_SUB_INDICES[0], **second_alias_expected_search),
            dict(index=SUB_INDICES[1], **first_alias_expected_search),
            dict(index=SUB_INDICES[0], **first_alias_expected_search),
        ])
        _set_cache('index_metadata__{},{}'.format(INDEX_NAME, SECOND_INDEX_NAME), None)

    @urllib3_responses.activate
    def test_get_es_variant_gene_counts(self):
        setup_responses()
        # Testing mito indices is done in other tests, it is helpful to have a strightforward single datatype test
        Sample.objects.get(elasticsearch_index=MITO_WGS_INDEX_NAME).delete()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
            'qualityFilter': {'min_gq': 10},
            'inheritance': {'mode': 'recessive'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(guid__in=['F000003_3', 'F000002_2', 'F000005_5']))

        initial_cached_results = {
            'compound_het_results': [{'ENSG00000240361': PARSED_COMPOUND_HET_VARIANTS}],
            'variant_results': [PARSED_VARIANTS[1]],
            'grouped_results': [{'null': [PARSED_VARIANTS[0]]}, {'ENSG00000228198': PARSED_COMPOUND_HET_VARIANTS}],
            'duplicate_doc_count': 0,
            'loaded_variant_counts': {'test_index_compound_het': {'total': 2, 'loaded': 2}, INDEX_NAME: {'loaded': 2, 'total': 5}},
            'total_results': 7,
        }
        _set_cache('search_results__{}__xpos'.format(results_model.guid), json.dumps(initial_cached_results))

        #  Test gene counts
        gene_counts = get_variant_query_gene_counts(results_model, None)
        self.assertDictEqual(gene_counts, {
            'ENSG00000135953': {'total': 3, 'families': {'F000003_3': 2, 'F000002_2': 1, 'F000005_5': 1}},
            'ENSG00000228198': {'total': 5, 'families': {'F000003_3': 4, 'F000002_2': 1, 'F000005_5': 1}},
            'ENSG00000240361': {'total': 2, 'families': {'F000003_3': 2}},
        })

        self.assertExecutedSearch(
            filters=[ANNOTATION_QUERY, RECESSIVE_INHERITANCE_QUERY],
            size=1, index=INDEX_NAME, gene_count_aggs={'vars_by_gene': {'top_hits': {'_source': 'none', 'size': 100}}})

        expected_cached_results = {'gene_aggs': gene_counts}
        expected_cached_results.update(initial_cached_results)
        self.assertCachedResults(results_model, expected_cached_results)

    @urllib3_responses.activate
    def test_multi_project_get_es_variant_gene_counts(self):
        setup_responses()
        # Testing mito indices is done in other tests, it is helpful to have a strightforward single datatype test
        Sample.objects.get(elasticsearch_index=MITO_WGS_INDEX_NAME).delete()
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
        gene_counts = get_variant_query_gene_counts(results_model, None)
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
                        {'term': {'samples_num_alt_2': 'NA20885'}},
                        {'bool': {
                            'must_not': [
                                {'term': {'samples_gq_0_to_5': 'NA20885'}},
                                {'term': {'samples_gq_5_to_10': 'NA20885'}},
                            ]
                        }}
                    ],
                    '_name': 'F000011_11'
                }}
            ], index=SECOND_INDEX_NAME, **expected_search),
            dict(filters=[ANNOTATION_QUERY, RECESSIVE_INHERITANCE_QUERY], index=INDEX_NAME, **expected_search),
        ])

        expected_cached_results = {'gene_aggs': gene_counts}
        expected_cached_results.update(initial_cached_results)
        self.assertCachedResults(results_model, expected_cached_results)

    @urllib3_responses.activate
    def test_multi_project_all_samples_all_inheritance_get_es_variant_gene_counts(self):
        setup_responses()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(project__id__in=[1, 3]))
        _set_cache('search_results__{}__xpos'.format(results_model.guid), json.dumps({'total_results': 5}))
        gene_counts = get_variant_query_gene_counts(results_model, None)

        self.assertDictEqual(gene_counts, {
            'ENSG00000135953': {'total': 6, 'families': {'F000003_3': 2, 'F000002_2': 2, 'F000011_11': 2}},
            'ENSG00000228198': {'total': 6, 'families': {'F000003_3': 2, 'F000002_2': 2, 'F000011_11': 2}}
        })

        self.assertExecutedSearch(
            index=','.join([INDEX_NAME, MITO_WGS_INDEX_NAME, SECOND_INDEX_NAME]),
            filters=[ANNOTATION_QUERY],
            size=1,
            gene_count_aggs={
                'samples': {'terms': {'field': 'samples', 'size': 10000}},
                'samples_num_alt_1': {'terms': {'field': 'samples_num_alt_1', 'size': 10000}},
                'samples_num_alt_2': {'terms': {'field': 'samples_num_alt_2', 'size': 10000}}
            }
        )

        self.assertCachedResults(results_model, {'gene_aggs': gene_counts, 'total_results': 5})

    @urllib3_responses.activate
    def test_all_samples_any_affected_get_es_variant_gene_counts(self):
        setup_responses()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']}, 'inheritance': {'mode': 'any_affected'},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(project__guid='R0001_1kg'))
        gene_counts = get_variant_query_gene_counts(results_model, None)

        self.assertDictEqual(gene_counts, {
            'ENSG00000135953': {'total': 3, 'families': {'F000003_3': 3, 'F000002_2': 2}},
            'ENSG00000228198': {'total': 3, 'families': {'F000003_3': 3, 'F000002_2': 2}}
        })

        self.assertExecutedSearches([dict(
            filters=[
                ANNOTATION_QUERY,
                {'bool': {
                    'should': [
                        {'terms': {'samples_num_alt_1': ['HG00731']}},
                        {'terms': {'samples_num_alt_2': ['HG00731']}},
                        {'terms': {'samples': ['HG00731']}},
                    ]
                }}
            ],
            index=MITO_WGS_INDEX_NAME,
            start_index=0,
            size=1,
            gene_count_aggs={
                'samples': {'terms': {'field': 'samples', 'size': 10000}},
                'samples_num_alt_1': {'terms': {'field': 'samples_num_alt_1', 'size': 10000}},
                'samples_num_alt_2': {'terms': {'field': 'samples_num_alt_2', 'size': 10000}}
            }
        ), dict(
            filters=[
                ANNOTATION_QUERY,
                {'bool': {
                    'should': [
                        {'terms': {'samples_num_alt_1': ['HG00731', 'NA19675', 'NA20870']}},
                        {'terms': {'samples_num_alt_2': ['HG00731', 'NA19675', 'NA20870']}},
                        {'terms': {'samples': ['HG00731', 'NA19675', 'NA20870']}},
                    ]
                }}
            ],
            start_index=0,
            size=1,
            gene_count_aggs={
                'samples': {'terms': {'field': 'samples', 'size': 10000}},
                'samples_num_alt_1': {'terms': {'field': 'samples_num_alt_1', 'size': 10000}},
                'samples_num_alt_2': {'terms': {'field': 'samples_num_alt_2', 'size': 10000}}
            }
        )])

        self.assertCachedResults(results_model, {'gene_aggs': gene_counts})

    def test_get_family_affected_status(self):
        samples_by_id = {
            sample_id: Sample.objects.get(sample_id=sample_id, dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS)
            for sample_id in ['HG00731', 'HG00732', 'HG00733']
        }
        custom_affected = {'I000004_hg00731': 'N', 'I000005_hg00732': 'A'}
        custom_multi_affected = {'I000005_hg00732': 'A'}

        self.assertDictEqual(_get_family_affected_status(samples_by_id, {}), {
            'I000004_hg00731': 'A', 'I000005_hg00732': 'N', 'I000006_hg00733': 'N'})

        custom_affected_status = _get_family_affected_status(samples_by_id, {'affected': custom_affected})
        self.assertDictEqual(custom_affected_status, {
            'I000004_hg00731': 'N', 'I000005_hg00732': 'A', 'I000006_hg00733': 'N'})

        custom_affected_status = _get_family_affected_status(samples_by_id, {'affected': custom_multi_affected})
        self.assertDictEqual(custom_affected_status, {
            'I000004_hg00731': 'A', 'I000005_hg00732': 'A', 'I000006_hg00733': 'N'})

    @urllib3_responses.activate
    def test_sort(self):
        setup_responses()
        search_model = VariantSearch.objects.create(search={
            'annotations': {'frameshift': ['frameshift_variant']},
        })
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(project__guid='R0001_1kg'))

        variants, _ = query_variants(results_model, sort='primate_ai', num_results=2)
        self.assertExecutedSearch(filters=[ANNOTATION_QUERY], sort=[
            {'primate_ai_score': {'order': 'desc', 'unmapped_type': 'double', 'numeric_type': 'double'}}, 'xpos', 'variantId'],
                                  index=','.join([INDEX_NAME, MITO_WGS_INDEX_NAME]), size=4)
        self.assertEqual(variants[0]['_sort'][0], maxsize)
        self.assertEqual(variants[1]['_sort'][0], -1)

        variants, _ = query_variants(results_model, sort='gnomad', num_results=2)
        self.assertExecutedSearch(filters=[ANNOTATION_QUERY], index=','.join([INDEX_NAME, MITO_WGS_INDEX_NAME]), size=4, sort=[
            {
                '_script': {
                    'type': 'number',
                    'script': {
                        'params': {'field': 'gnomad_genomes_AF'},
                        'source': mock.ANY,
                    }
                }
            }, 'xpos', 'variantId'])
        self.assertEqual(variants[0]['_sort'][0], 0.00012925741614425127)
        self.assertEqual(variants[1]['_sort'][0], maxsize)

        variants, _ = query_variants(results_model, sort='in_omim', num_results=2)
        self.assertExecutedSearch(filters=[ANNOTATION_QUERY], index=','.join([INDEX_NAME, MITO_WGS_INDEX_NAME]), size=4, sort=[
            {
                '_script': {
                    'type': 'number',
                    'script': {
                        'params': {
                            'omim_gene_ids': ['ENSG00000240361', 'ENSG00000135953']
                        },
                        'source': mock.ANY,
                    }
                }
            }, {
                '_script': {
                    'type': 'number',
                    'script': {
                        'params': {
                            'omim_gene_ids': ['ENSG00000240361', 'ENSG00000135953']
                        },
                        'source': mock.ANY,
                    }
                }
            }, 'xpos', 'variantId'])

        results_model.families.set(Family.objects.filter(guid='F000001_1'))
        query_variants(results_model, sort='prioritized_gene', num_results=2)
        family_sample_filter = {'bool': {'_name': 'F000001_1', 'must': mock.ANY}}
        self.assertExecutedSearch(filters=[ANNOTATION_QUERY, family_sample_filter], index=INDEX_NAME, size=2, sort=[
            {
                '_script': {
                    'type': 'number',
                    'script': {
                        'params': {
                            'prioritized_ranks_by_gene': {'ENSG00000268903': 1, 'ENSG00000268904': 11}
                        },
                        'source': mock.ANY,
                    }
                }
            }, 'xpos', 'variantId'])

    @urllib3_responses.activate
    def test_genotype_inheritance_filter(self):
        setup_responses()
        # Testing mito indices is done in other tests, it is helpful to have a strightforward single datatype test
        Sample.objects.get(elasticsearch_index=MITO_WGS_INDEX_NAME).delete()
        custom_affected = {'I000004_hg00731': 'N', 'I000005_hg00732': 'A'}
        custom_multi_affected = {'I000005_hg00732': 'A'}

        search_model = VariantSearch.objects.create(search={})
        results_model = VariantSearchResults.objects.create(variant_search=search_model)
        results_model.families.set(Family.objects.filter(guid='F000002_2'))
        cache_key = 'search_results__{}__xpos'.format(results_model.guid)

        def _execute_inheritance_search(
                mode=None, inheritance_filter=None, expected_filter=None, expected_comp_het_filter=None,
                quality_filter=None, expected_quality_filter=None, dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS, **kwargs):
            _set_cache(cache_key, None)
            annotations = {'frameshift': ['frameshift_variant']} if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS \
                else {'structural': ['DEL', 'gCNV_DEL']}
            search_model.search = {
                'inheritance': {'mode': mode, 'filter': inheritance_filter},
                'annotations': annotations,
            }
            if quality_filter:
                search_model.search['qualityFilter'] = quality_filter
            search_model.save()
            variants, _ = query_variants(results_model, num_results=2)

            if mode not in {'compound_het', 'recessive'}:
                self.assertSetEqual(
                    set(variants[-1]['genotypes'].keys()),
                    {'I000004_hg00731', 'I000005_hg00732', 'I000006_hg00733'},
                )

            index = INDEX_NAME if dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS else SV_INDEX_NAME
            annotation_query = {'terms': {'transcriptConsequenceTerms': next(iter(annotations.values()))}}
            if expected_comp_het_filter:
                self.assertExecutedSearches([
                    dict(gene_aggs=True, start_index=0, size=1, index=index, filters=[
                        annotation_query, {'bool': {'_name': 'F000002_2', 'must': [expected_comp_het_filter]}}
                    ]),
                    dict(start_index=0, size=2, index=index, filters=[
                        annotation_query,  {'bool': {'_name': 'F000002_2', 'must': [expected_filter]}}])
                ])
            else:
                filters = [expected_filter]
                if expected_quality_filter:
                    filters.append(expected_quality_filter)
                self.assertExecutedSearch(index=index, filters=[
                    annotation_query, {'bool': {'_name': 'F000002_2', 'must': filters}}], **kwargs)

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
                'must_not': [{'term': {'samples': 'HG00732'}}, {'term': {'samples': 'HG00733'}}],
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
        }, quality_filter={'affected_only': True, 'min_gq': 10}, expected_quality_filter={
            'bool': {'must_not': [
                {'term': {'samples_gq_0_to_5': 'HG00732'}},
                {'term': {'samples_gq_5_to_10': 'HG00732'}},
            ]}}
        )

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
                'must_not': [
                    {'term': {'samples_cn_0': 'HG00732'}},
                    {'term': {'samples_cn_gte_4': 'HG00732'}},
                    {'term': {'samples_cn_0': 'HG00733'}},
                    {'term': {'samples_cn_gte_4': 'HG00733'}},
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
                    {'range': {'xpos': {'gte': 23000000001, 'lte': 24000000001}}},
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
                'must_not': [
                    {'term': {'samples': 'HG00732'}},
                    {'term': {'samples_cn_0': 'HG00733'}},
                    {'term': {'samples_cn_gte_4': 'HG00733'}},
                ],
                'must': [{'range': {'xpos': {'gte': 23000000001, 'lte': 24000000001}}},],
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
                    {'range': {'xpos': {'gte': 23000000001, 'lte': 24000000001}}},
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
        _execute_inheritance_search(mode='recessive', expected_comp_het_filter=com_het_filter, expected_filter=recessive_filter)

        _execute_inheritance_search(
            mode='recessive', dataset_type='SV', expected_comp_het_filter=sv_com_het_filter, expected_filter=sv_recessive_filter)

        _execute_inheritance_search(
            mode='recessive', inheritance_filter={'affected': custom_affected},
            expected_comp_het_filter=custom_affected_comp_het_filter, expected_filter=custom_affected_recessive_filter)

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
