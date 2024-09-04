from aiohttp.test_utils import AioHTTPTestCase
import asyncio
from copy import deepcopy
import time
from unittest import mock

from hail_search.test_utils import get_hail_search_body, FAMILY_2_VARIANT_SAMPLE_DATA, FAMILY_2_MISSING_SAMPLE_DATA, \
    VARIANT1, VARIANT2, VARIANT3, VARIANT4, MULTI_PROJECT_SAMPLE_DATA, MULTI_PROJECT_MISSING_SAMPLE_DATA, \
    LOCATION_SEARCH, EXCLUDE_LOCATION_SEARCH, VARIANT_ID_SEARCH, RSID_SEARCH, GENE_COUNTS, SV_WGS_SAMPLE_DATA, \
    SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, \
    GCNV_MULTI_FAMILY_VARIANT1, GCNV_MULTI_FAMILY_VARIANT2, SV_WES_SAMPLE_DATA, EXPECTED_SAMPLE_DATA, \
    FAMILY_2_MITO_SAMPLE_DATA, FAMILY_2_ALL_SAMPLE_DATA, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3, \
    EXPECTED_SAMPLE_DATA_WITH_SEX, SV_WGS_SAMPLE_DATA_WITH_SEX, VARIANT_LOOKUP_VARIANT, \
    MULTI_PROJECT_SAMPLE_TYPES_SAMPLE_DATA
from hail_search.web_app import init_web_app, sync_to_async_hail_query
from hail_search.queries.base import BaseHailTableQuery

PROJECT_2_VARIANT = {
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
        'I000015_na20885': [{
            'sampleId': 'NA20885', 'sampleType': 'WES', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
            'numAlt': 1, 'dp': 8, 'gq': 14, 'ab': 0.875,
        }],
    },
    'genotypeFilters': '',
    'clinvar': None,
    'hgmd': None,
    'screenRegionType': None,
    'populations': {
        'seqr': {'af': 0.0, 'ac': 0, 'an': 90, 'hom': 0},
        'topmed': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'het': 0},
        'exac': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'het': 0, 'filter_af': 0.0},
        'gnomad_exomes': {'af': 0.0, 'ac': 0, 'an': 0, 'hom': 0, 'hemi': 0, 'filter_af': 0.0},
        'gnomad_genomes': {'af': 0.00012430080096237361, 'ac': 2, 'an': 16090, 'hom': 0, 'hemi': 0, 'filter_af': 0.002336448524147272},
    },
    'predictions': {
        'cadd': 4.6529998779296875,
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
    '_sort': [1000010146],
    'CAID': 'CA520798130',
}
PROJECT_2_VARIANT_BOTH_SAMPLE_TYPES = deepcopy(PROJECT_2_VARIANT)
PROJECT_2_VARIANT_BOTH_SAMPLE_TYPES['genotypes']['I000015_na20885'].append({
    'sampleId': 'NA20885', 'sampleType': 'WGS', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
    'numAlt': 1, 'dp': 8, 'gq': 14, 'ab': 0.875,
})

GRCH37_VARIANT = {
    'variantId': '7-143270172-A-G',
    'xpos': 7143270172,
    'chrom': '7',
    'pos': 143270172,
    'ref': 'A',
    'alt': 'G',
    'genomeVersion': '37',
    'rsid': 'rs72611576',
    'familyGuids': ['F000002_2'],
    'genotypes': {
        'I000004_hg00731': [{
            'sampleId': 'HG00731', 'sampleType': 'WES', 'individualGuid': 'I000004_hg00731',
            'familyGuid': 'F000002_2', 'numAlt': 2, 'dp': 16, 'gq': 48, 'ab': 1,
        }], 'I000006_hg00733': [{
            'sampleId': 'HG00733', 'sampleType': 'WES', 'individualGuid': 'I000006_hg00733',
            'familyGuid': 'F000002_2', 'numAlt': 1, 'dp': 49, 'gq': 99, 'ab': 0.6530612111091614,
        }],
    },
    'genotypeFilters': 'VQSRTrancheSNP99.90to99.95',
    'populations': {
        'seqr': {'af': 0.5912399888038635, 'ac': 4711, 'an': 7968, 'hom': 1508},
        'topmed': {'af': 0.5213189721107483, 'ac': 65461, 'an': 125568, 'hom': 16156, 'het': 33149},
        'exac': {'af': 0.6299999952316284, 'ac': 66593, 'an': 104352, 'hom': 22162, 'hemi': 0, 'het': 22269, 'filter_af': 0.8198773860931396},
        'gnomad_exomes': {'af': 0.6354219317436218, 'ac': 137532, 'an': 216442, 'hom': 45869, 'hemi': 0, 'filter_af': 0.8226116299629211},
        'gnomad_genomes': {'af': 0.6136477589607239, 'ac': 14649, 'an': 23872, 'hom': 4584, 'hemi': 0, 'filter_af': 0.828438937664032},
    },
    'predictions': {
        'cadd': 13.020000457763672, 'eigen': 3.9509999752044678, 'primate_ai': 0.4906357526779175,
        'splice_ai': 0, 'splice_ai_consequence': 'No consequence',
        'mpc': None, 'mut_taster': None, 'polyphen': None, 'revel': None, 'sift': None,
    },
    'clinvar': None,
    'hgmd': None,
    'transcripts': {
        'ENSG00000271079': [
            {'aminoAcids': 'E/G', 'canonical': 1, 'codons': 'gAa/gGa', 'geneId': 'ENSG00000271079',
             'hgvsc': 'ENST00000420911.2:c.1262A>G', 'hgvsp': 'ENSP00000474204.1:p.Glu421Gly',
             'transcriptId': 'ENST00000420911', 'isLofNagnag': None, 'transcriptRank': 0,
             'biotype': 'protein_coding', 'lofFilters': None, 'majorConsequence': 'missense_variant'},
        ],
        'ENSG00000176227': [
            {'aminoAcids': None, 'canonical': 1, 'codons': None, 'geneId': 'ENSG00000176227',
             'hgvsc': 'ENST00000447022.1:n.1354A>G', 'hgvsp': None,
             'transcriptId': 'ENST00000447022', 'isLofNagnag': None, 'transcriptRank': 0,
             'biotype': 'processed_pseudogene', 'lofFilters': None, 'majorConsequence': 'non_coding_transcript_exon_variant'},
        ],
    },
    'mainTranscriptId': 'ENST00000420911',
    'selectedMainTranscriptId': None,
    '_sort': [7143270172],
    'CAID': 'CA4540310',
}

FAMILY_3_VARIANT = deepcopy(VARIANT3)
FAMILY_3_VARIANT['familyGuids'] = ['F000003_3']
FAMILY_3_VARIANT['genotypes'] = {
    'I000007_na20870': [{
        'sampleId': 'NA20870', 'sampleType': 'WES', 'individualGuid': 'I000007_na20870', 'familyGuid': 'F000003_3',
        'numAlt': 1, 'dp': 28, 'gq': 99, 'ab': 0.6785714285714286,
    }],
}

MULTI_FAMILY_VARIANT = deepcopy(VARIANT3)
MULTI_FAMILY_VARIANT['familyGuids'] += FAMILY_3_VARIANT['familyGuids']
MULTI_FAMILY_VARIANT['genotypes'].update(FAMILY_3_VARIANT['genotypes'])

SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT = {**MULTI_FAMILY_VARIANT, 'selectedMainTranscriptId': 'ENST00000426137'}
SELECTED_ANNOTATION_TRANSCRIPT_MULTI_FAMILY_VARIANT = {**MULTI_FAMILY_VARIANT, 'selectedMainTranscriptId': 'ENST00000497611'}
SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4 = {**VARIANT4, 'selectedMainTranscriptId': 'ENST00000350997'}
SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_3 = {**VARIANT3, 'selectedMainTranscriptId': 'ENST00000497611'}
SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2 = {**VARIANT2, 'selectedMainTranscriptId': 'ENST00000459627'}
MULTI_DATA_TYPE_COMP_HET_VARIANT2 = {**VARIANT2, 'selectedMainTranscriptId': 'ENST00000450625'}

PROJECT_2_VARIANT1 = deepcopy(VARIANT1)
PROJECT_2_VARIANT1['familyGuids'] = ['F000011_11']
PROJECT_2_VARIANT1['genotypes'] = {
    'I000015_na20885': [{
        'sampleId': 'NA20885', 'sampleType': 'WES', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
        'numAlt': 2, 'dp': 6, 'gq': 16, 'ab': 1.0,
    }],
}
MULTI_PROJECT_VARIANT1 = deepcopy(VARIANT1)
MULTI_PROJECT_VARIANT1['familyGuids'] += PROJECT_2_VARIANT1['familyGuids']
MULTI_PROJECT_VARIANT1['genotypes'].update(PROJECT_2_VARIANT1['genotypes'])
MULTI_PROJECT_VARIANT2 = deepcopy(VARIANT2)
MULTI_PROJECT_VARIANT2['familyGuids'].append('F000011_11')
MULTI_PROJECT_VARIANT2['genotypes']['I000015_na20885'] = [{
    'sampleId': 'NA20885', 'sampleType': 'WES', 'individualGuid': 'I000015_na20885', 'familyGuid': 'F000011_11',
    'numAlt': 1, 'dp': 28, 'gq': 99, 'ab': 0.5,
}]

NO_GENOTYPE_GCNV_VARIANT = {**GCNV_VARIANT4, 'numExon': 8, 'end': 38736268}

FAMILY_4_VARIANT = {
    'xpos': 4052038257,
    'rsid': None,
    'CAID': 'CA10604324',
    'genotypes': {
        'I00001_BON_UC4991': [
            {
                'sampleId': 'BON_UC499_1_1',
                'sampleType': 'WES',
                'familyGuid': 'F000004_4',
                'individualGuid': 'I00001_BON_UC4991',
                'numAlt': 1,
                'dp': 14,
                'gq': 99,
                'ab': 0.3571428656578064,
            },
            {
                'sampleId': 'BON_UC499_1_1',
                'sampleType': 'WGS',
                'familyGuid': 'F000004_4',
                'individualGuid': 'I00001_BON_UC4991',
                'numAlt': 1,
                'dp': 36,
                'gq': 99,
                'ab': 0.3611111044883728,
            },
        ],
        'I00003_BON_UC4993': [
            {
                'sampleId': 'BON_UC499_3_1',
                'sampleType': 'WES',
                'familyGuid': 'F000004_4',
                'individualGuid': 'I00003_BON_UC4993',
                'numAlt': 0,
                'dp': None,
                'gq': 40,
                'ab': None,
            },
            {
                'sampleId': 'BON_UC499_3_1',
                'sampleType': 'WGS',
                'familyGuid': 'F000004_4',
                'individualGuid': 'I00003_BON_UC4993',
                'numAlt': 0,
                'dp': 34,
                'gq': 40,
                'ab': 0.0,
            },
        ],
        'I00004_BON_UC4994': [
            {
                'sampleId': 'BON_UC499_4_1',
                'sampleType': 'WES',
                'familyGuid': 'F000004_4',
                'individualGuid': 'I00004_BON_UC4994',
                'numAlt': 0,
                'dp': None,
                'gq': 0,
                'ab': None,
            },
            {
                'sampleId': 'BON_UC499_4_1',
                'sampleType': 'WGS',
                'familyGuid': 'F000004_4',
                'individualGuid': 'I00004_BON_UC4994',
                'numAlt': 1,
                'dp': 29,
                'gq': 99,
                'ab': 0.517241358757019,
            },
        ],
    },
    'populations': {
        'seqr': {'af': 0.000141964788781479, 'ac': 6, 'an': 42264, 'hom': 0},
        'topmed': {
            'af': 6.044809924787842e-05,
            'ac': 16,
            'an': 264690,
            'hom': 0,
            'het': 16,
        },
        'exac': {
            'af': 0.0,
            'ac': 0,
            'an': 0,
            'hom': 0,
            'hemi': 0,
            'het': 0,
            'filter_af': 0.0,
        },
        'gnomad_exomes': {
            'af': 0.0,
            'ac': 0,
            'an': 0,
            'hom': 0,
            'hemi': 0,
            'filter_af': 0.0,
        },
        'gnomad_genomes': {
            'af': 0.0,
            'ac': 0,
            'an': 0,
            'hom': 0,
            'hemi': 0,
            'filter_af': 0.0,
        },
    },
    'predictions': {
        'cadd': 18.1200008392334,
        'eigen': None,
        'mpc': None,
        'primate_ai': None,
        'splice_ai': 0.0,
        'splice_ai_consequence': 'No consequence',
        'mut_taster': None,
        'polyphen': None,
        'revel': None,
        'sift': None,
        'fathmm': None,
        'mut_pred': None,
        'vest': None,
        'gnomad_noncoding': 2.711364507675171,
    },
    'chrom': '4',
    'pos': 52038257,
    'ref': 'CAT',
    'alt': 'C',
    'mainTranscriptId': 'ENST00000381431',
    'selectedMainTranscriptId': None,
    'familyGuids': ['F000004_4'],
    'genotypeFilters': '',
    'variantId': '4-52038257-CAT-C',
    'liftedOverGenomeVersion': '37',
    'liftedOverChrom': '4',
    'liftedOverPos': 52904423,
    'clinvar': {
        'alleleId': 267097,
        'conflictingPathogenicities': None,
        'goldStars': 2,
        'submitters': [
            'GeneDx',
            'Eurofins Ntd Llc (ga)',
            'Natera, Inc.',
            'Invitae',
            'Clinical Genetics and Genomics, Karolinska University Hospital',
            'Revvity Omics, Revvity',
            'Illumina Laboratory Services, Illumina',
            'Baylor Genetics',
        ],
        'conditions': [
            'not provided',
            'not provided',
            'Autosomal recessive limb-girdle muscular dystrophy type 2E',
            'Autosomal recessive limb-girdle muscular dystrophy type 2E',
            'not provided',
            'Autosomal recessive limb-girdle muscular dystrophy type 2E',
            'Qualitative or quantitative defects of beta-sarcoglycan',
            'Autosomal recessive limb-girdle muscular dystrophy type 2E',
        ],
        'pathogenicity': 'Pathogenic/Likely_pathogenic',
        'assertions': [],
        'version': '2024-02-21',
    },
    'hgmd': {'accession': 'CD086203', 'class': 'DM'},
    'screenRegionType': 'PLS',
    'transcripts': {
        'ENSG00000163069': [
            {
                'aminoAcids': 'M/X',
                'canonical': 1,
                'codons': 'ATg/g',
                'geneId': 'ENSG00000163069',
                'hgvsc': 'ENST00000381431.10:c.1_2del',
                'hgvsp': 'ENSP00000370839.6:p.Met1?',
                'transcriptId': 'ENST00000381431',
                'maneSelect': 'NM_000232.5',
                'manePlusClinical': None,
                'exon': {'index': 1, 'total': 6},
                'intron': None,
                'alphamissense': {'pathogenicity': None},
                'loftee': {'isLofNagnag': None, 'lofFilters': None},
                'spliceregion': {
                    'extended_intronic_splice_region_variant': False
                },
                'utrannotator': {
                    'existingInframeOorfs': None,
                    'existingOutofframeOorfs': None,
                    'existingUorfs': None,
                    'fiveutrAnnotation': None,
                    'fiveutrConsequence': None,
                },
                'refseqTranscriptId': 'NM_000232.5',
                'biotype': 'protein_coding',
                'majorConsequence': 'frameshift_variant',
                'transcriptRank': 0,
            }
        ]
    },
    'sortedMotifFeatureConsequences': [
        {
            'motifFeatureId': 'ENSM00525017134',
            'consequenceTerms': ['TF_binding_site_variant'],
        },
        {
            'motifFeatureId': 'ENSM00190765165',
            'consequenceTerms': ['TF_binding_site_variant'],
        },
        {
            'motifFeatureId': 'ENSM00191195279',
            'consequenceTerms': ['TF_binding_site_variant'],
        },
        {
            'motifFeatureId': 'ENSM00026078608',
            'consequenceTerms': ['TF_binding_site_variant'],
        },
    ],
    'sortedRegulatoryFeatureConsequences': [
        {
            'regulatoryFeatureId': 'ENSR00000168217',
            'biotype': 'promoter',
            'consequenceTerms': ['regulatory_region_variant'],
        }
    ],
    '_sort': [4052038257],
    'genomeVersion': '38',
}

FAMILY_4_SAMPLE_DATA = {
    'SNV_INDEL': [
        {'sample_id': 'BON_UC499_1_1', 'individual_guid': 'I00001_BON_UC4991', 'family_guid': 'F000004_4',
         'affected': 'A', 'project_guid': 'Project_4', 'sample_type': 'WES', 'sex': 'F'},
        {'sample_id': 'BON_UC499_1_1', 'individual_guid': 'I00001_BON_UC4991', 'family_guid': 'F000004_4',
         'affected': 'A', 'project_guid': 'Project_4', 'sample_type': 'WGS', 'sex': 'F'},
        {'sample_id': 'BON_UC499_3_1', 'individual_guid': 'I00003_BON_UC4993', 'family_guid': 'F000004_4',
         'affected': 'N', 'project_guid': 'Project_4', 'sample_type': 'WES', 'sex': 'F'},
        {'sample_id': 'BON_UC499_3_1', 'individual_guid': 'I00003_BON_UC4993', 'family_guid': 'F000004_4',
         'affected': 'N', 'project_guid': 'Project_4', 'sample_type': 'WGS', 'sex': 'F'},
        {'sample_id': 'BON_UC499_4_1', 'individual_guid': 'I00004_BON_UC4994', 'family_guid': 'F000004_4',
         'affected': 'N', 'project_guid': 'Project_4', 'sample_type': 'WES', 'sex': 'M'},
        {'sample_id': 'BON_UC499_4_1', 'individual_guid': 'I00004_BON_UC4994', 'family_guid': 'F000004_4',
         'affected': 'N', 'project_guid': 'Project_4', 'sample_type': 'WGS', 'sex': 'M'},
    ]
}

FAMILY_5_VARIANT = {
    "xpos": 2044312653,
    "rsid": None,
    "CAID": "CA127830",
    "genotypes": {
        "I00001_bon_b15_95_1_d1": [
            {
                "sampleId": "BON_B15-95_1_D1",
                "sampleType": "WES",
                "familyGuid": "F000005_5",
                "individualGuid": "I00001_bon_b15_95_1_d1",
                "numAlt": 1,
                "dp": 71,
                "gq": 99,
                "ab": 0.5211267471313477,
            },
            {
                "sampleId": "BON_B15-95_1_D1",
                "sampleType": "WGS",
                "familyGuid": "F000005_5",
                "individualGuid": "I00001_bon_b15_95_1_d1",
                "numAlt": 1,
                "dp": 49,
                "gq": 99,
                "ab": 0.5306122303009033,
            },
        ],
        "I00003_bon_b15_95_3_d1": [
            {
                "sampleId": "BON_B15-95_3_D1",
                "sampleType": "WES",
                "familyGuid": "F000005_5",
                "individualGuid": "I00003_bon_b15_95_3_d1",
                "numAlt": 1,
                "dp": 78,
                "gq": 99,
                "ab": 0.4743589758872986,
            }
        ],
        "I00004_bon_b15_95_4_d1": [
            {
                "sampleId": "BON_B15-95_4_D1",
                "sampleType": "WES",
                "familyGuid": "F000005_5",
                "individualGuid": "I00004_bon_b15_95_4_d1",
                "numAlt": 0,
                "dp": None,
                "gq": 40,
                "ab": None,
            }
        ],
    },
    "populations": {
        "seqr": {"af": 0.003060524584725499, "ac": 232, "an": 75804, "hom": 3},
        "topmed": {
            "af": 0.002274360042065382,
            "ac": 602,
            "an": 264690,
            "hom": 1,
            "het": 600,
        },
        "exac": {
            "af": 0.0,
            "ac": 0,
            "an": 0,
            "hom": 0,
            "hemi": 0,
            "het": 0,
            "filter_af": 0.0,
        },
        "gnomad_exomes": {
            "af": 0.0,
            "ac": 0,
            "an": 0,
            "hom": 0,
            "hemi": 0,
            "filter_af": 0.0,
        },
        "gnomad_genomes": {
            "af": 0.0,
            "ac": 0,
            "an": 0,
            "hom": 0,
            "hemi": 0,
            "filter_af": 0.0,
        },
    },
    "predictions": {
        "cadd": 22.799999237060547,
        "eigen": None,
        "mpc": None,
        "primate_ai": 0.6688539981842041,
        "splice_ai": 0.0,
        "splice_ai_consequence": "No consequence",
        "mut_taster": None,
        "polyphen": None,
        "revel": None,
        "sift": None,
        "fathmm": None,
        "mut_pred": None,
        "vest": None,
        "gnomad_noncoding": -3.0888006687164307,
    },
    "chrom": "2",
    "pos": 44312653,
    "ref": "T",
    "alt": "C",
    "mainTranscriptId": None,
    "selectedMainTranscriptId": None,
    "familyGuids": ["F000005_5"],
    "genotypeFilters": "",
    "variantId": "2-44312653-T-C",
    "liftedOverGenomeVersion": "37",
    "liftedOverChrom": "2",
    "liftedOverPos": 44539792,
    "clinvar": {
        "alleleId": 33154,
        "conflictingPathogenicities": None,
        "goldStars": 2,
        "submitters": [],
        "conditions": [],
        "pathogenicity": "Pathogenic/Likely_pathogenic",
        "assertions": [],
        "version": "2024-02-21",
    },
    "hgmd": {"accession": "CM941281", "class": "DM"},
    "screenRegionType": None,
    "transcripts": {},
    "sortedMotifFeatureConsequences": None,
    "sortedRegulatoryFeatureConsequences": None,
    "_sort": [2044312653],
    "genomeVersion": "38",
}

FAMILY_5_SAMPLE_DATA = {
    'SNV_INDEL': [
        {'sample_id': 'BON_B15-95_1_D1', 'individual_guid': 'I00001_bon_b15_95_1_d1', 'family_guid': 'F000005_5',
         'affected': 'A', 'project_guid': 'Project_4', 'sample_type': 'WES', 'sex': 'F'},
        {'sample_id': 'BON_B15-95_1_D1', 'individual_guid': 'I00001_bon_b15_95_1_d1', 'family_guid': 'F000005_5',
         'affected': 'A', 'project_guid': 'Project_4', 'sample_type': 'WGS', 'sex': 'F'},
        {'sample_id': 'BON_B15-95_3_D1', 'individual_guid': 'I00003_bon_b15_95_3_d1', 'family_guid': 'F000005_5',
         'affected': 'N', 'project_guid': 'Project_4', 'sample_type': 'WES', 'sex': 'F'},
        {'sample_id': 'BON_B15-95_4_D1', 'individual_guid': 'I00004_bon_b15_95_4_d1', 'family_guid': 'F000005_5',
         'affected': 'N', 'project_guid': 'Project_4', 'sample_type': 'WES', 'sex': 'M'},
    ]
}

# Ensures no variants are filtered out by annotation/path filters for compound hets
COMP_HET_ALL_PASS_FILTERS = {
    'annotations': {'splice_ai': '0.0', 'structural': ['DEL', 'CPX', 'INS', 'gCNV_DEL', 'gCNV_DUP']},
    'pathogenicity': {'clinvar': ['likely_pathogenic']},
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

OMIM_SORT_METADATA = ['ENSG00000177000', 'ENSG00000097046', 'ENSG00000275023']


def _sorted(variant, sorts):
    return {**variant, '_sort': sorts + variant['_sort']}


class HailSearchTestCase(AioHTTPTestCase):

    maxDiff = None

    async def get_application(self):
        return await init_web_app()

    async def test_sync_to_async_hail_query(self):
        request = mock.Mock()
        request.app = await self.get_application()
        # NB: request.json() is the first arg passed to the callable
        request.json.return_value = asyncio.Future()
        request.json.return_value.set_result(3)
        with self.assertRaises(TimeoutError):
            await sync_to_async_hail_query(request, time.sleep, timeout_s=1)

        with mock.patch('hail_search.web_app.ctypes.pythonapi.PyThreadState_SetAsyncExc') as mock_set_async_exc:
            mock_set_async_exc.return_value = 2
            with self.assertRaises(SystemExit):
                await sync_to_async_hail_query(request, time.sleep, timeout_s=1)

    async def test_status(self):
        async with self.client.request('GET', '/status') as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, {'success': True})

    async def _assert_expected_search(self, results, gene_counts=None, **search_kwargs):
        search_body = get_hail_search_body(**search_kwargs)
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertSetEqual(set(resp_json.keys()), {'results', 'total'})
        self.assertEqual(resp_json['total'], len(results))
        for i, result in enumerate(resp_json['results']):
            self.assertEqual(result, results[i])

        if gene_counts:
            async with self.client.request('POST', '/gene_counts', json=search_body) as resp:
                self.assertEqual(resp.status, 200)
                gene_counts_json = await resp.json()
            self.assertDictEqual(gene_counts_json, gene_counts)

    async def test_single_family_search(self):
        variant_gene_counts = {
            'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
            'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2}},
            'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}}
        }
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT3, VARIANT4], sample_data=FAMILY_2_VARIANT_SAMPLE_DATA, gene_counts=variant_gene_counts,
        )

        mito_gene_counts = {
            'ENSG00000210112': {'total': 1, 'families': {'F000002_2': 1}},
            'ENSG00000198886': {'total': 1, 'families': {'F000002_2': 1}},
            'ENSG00000198727': {'total': 1, 'families': {'F000002_2': 1}},
        }
        await self._assert_expected_search(
            [MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sample_data=FAMILY_2_MITO_SAMPLE_DATA, gene_counts=mito_gene_counts,
        )

        await self._assert_expected_search(
            [GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], omit_data_type='SNV_INDEL', gene_counts=GCNV_GENE_COUNTS,
        )

        await self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, gene_counts=SV_GENE_COUNTS,
        )

        await self._assert_expected_search(
            [VARIANT1, SV_VARIANT1, SV_VARIANT2, VARIANT2, VARIANT3, VARIANT4, SV_VARIANT3, GCNV_VARIANT1, SV_VARIANT4,
             GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], sample_data={
                'SV_WES': EXPECTED_SAMPLE_DATA['SV_WES'], **FAMILY_2_ALL_SAMPLE_DATA, **SV_WGS_SAMPLE_DATA,
            }, gene_counts={**variant_gene_counts, **mito_gene_counts, **GCNV_GENE_COUNTS, **SV_GENE_COUNTS, 'ENSG00000277258': {'total': 2, 'families': {'F000002_2': 2}}},
        )

        await self._assert_expected_search(
            [GRCH37_VARIANT], genome_version='GRCh37', sample_data=FAMILY_2_VARIANT_SAMPLE_DATA)

    async def test_single_project_search(self):
        variant_gene_counts = {
            'ENSG00000097046': {'total': 3, 'families': {'F000002_2': 2, 'F000003_3': 1}},
            'ENSG00000177000': {'total': 3, 'families': {'F000002_2': 2, 'F000003_3': 1}},
            'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
        }
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], omit_data_type='SV_WES', gene_counts=variant_gene_counts,
        )

        await self._assert_expected_search(
            [GCNV_MULTI_FAMILY_VARIANT1, GCNV_MULTI_FAMILY_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], sample_data=SV_WES_SAMPLE_DATA, gene_counts={
                'ENSG00000129562': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000013364': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000079616': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000103495': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000167371': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000280789': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000280893': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000281348': {'total': 2, 'families': {'F000002_2': 1, 'F000003_3': 1}},
                'ENSG00000275023': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000277972': {'total': 1, 'families': {'F000002_2': 1}},
            }
        )

        await self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            gene_counts={**variant_gene_counts, **GCNV_GENE_COUNTS, 'ENSG00000277258': {'total': 2, 'families': {'F000002_2': 2}}}
        )

    async def test_multi_project_search(self):
        await self._assert_expected_search(
            [PROJECT_2_VARIANT, MULTI_PROJECT_VARIANT1, MULTI_PROJECT_VARIANT2, VARIANT3, VARIANT4],
            gene_counts=GENE_COUNTS, sample_data=MULTI_PROJECT_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [PROJECT_2_VARIANT, MULTI_PROJECT_VARIANT1, SV_VARIANT1, SV_VARIANT2, MULTI_PROJECT_VARIANT2, VARIANT3,
             VARIANT4, SV_VARIANT3, SV_VARIANT4], gene_counts={**GENE_COUNTS, **SV_GENE_COUNTS},
            sample_data={**MULTI_PROJECT_SAMPLE_DATA, **SV_WGS_SAMPLE_DATA},
        )

    async def test_both_sample_type_search(self):
        expected_variants = [PROJECT_2_VARIANT, MULTI_PROJECT_VARIANT1, MULTI_PROJECT_VARIANT2, VARIANT3, VARIANT4]
        expected_results = []
        for variant in expected_variants:
            v = deepcopy(variant)
            if 'I000015_na20885' in v['genotypes']:
                v['genotypes']['I000015_na20885'].append({**v['genotypes']['I000015_na20885'][0], 'sampleType': 'WGS'})
            expected_results.append(v)

        await self._assert_expected_search(
            expected_results, gene_counts=GENE_COUNTS, sample_data=MULTI_PROJECT_SAMPLE_TYPES_SAMPLE_DATA,
        )

        # Variant is de novo in exome but maternally inherited in genome.
        # Expect variant with genotypes from both sample types to be returned.
        inheritance_mode = 'de_novo'
        await self._assert_expected_search(
            [FAMILY_4_VARIANT], sample_data=FAMILY_4_SAMPLE_DATA, inheritance_mode=inheritance_mode,
        )

        # Variant is inherited in exome and there is no parental data for this variant in genome.
        # Expect variant to be present in recessive response but absent in de novo response.
        inheritance_mode = 'de_novo'
        await self._assert_expected_search(
            [], sample_data=FAMILY_5_SAMPLE_DATA, inheritance_mode=inheritance_mode,
        )
        inheritance_mode = 'recessive'
        await self._assert_expected_search(
            [FAMILY_5_VARIANT], sample_data=FAMILY_5_SAMPLE_DATA, inheritance_mode=inheritance_mode,
        )

    async def test_inheritance_filter(self):
        inheritance_mode = 'any_affected'
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            inheritance_mode=inheritance_mode,
        )

        await self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2, SV_VARIANT3, SV_VARIANT4], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [GCNV_VARIANT3], inheritance_mode=inheritance_mode, annotations=NEW_SV_FILTER, omit_data_type='SNV_INDEL',
        )

        await self._assert_expected_search(
            [SV_VARIANT2], inheritance_mode=inheritance_mode, annotations=NEW_SV_FILTER, sample_data=SV_WGS_SAMPLE_DATA,
        )

        inheritance_mode = 'de_novo'
        await self._assert_expected_search(
            [VARIANT1, FAMILY_3_VARIANT, VARIANT4, GCNV_VARIANT1], inheritance_mode=inheritance_mode,
        )

        await self._assert_expected_search(
            [SV_VARIANT1], inheritance_mode=inheritance_mode,  sample_data=SV_WGS_SAMPLE_DATA,
        )

        inheritance_mode = 'x_linked_recessive'
        await self._assert_expected_search([], inheritance_mode=inheritance_mode, sample_data=EXPECTED_SAMPLE_DATA_WITH_SEX)
        await self._assert_expected_search([], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA_WITH_SEX)

        inheritance_mode = 'homozygous_recessive'
        await self._assert_expected_search([VARIANT2, GCNV_VARIANT3], inheritance_mode=inheritance_mode)

        await self._assert_expected_search(
            [PROJECT_2_VARIANT1, VARIANT2], inheritance_mode=inheritance_mode, sample_data=MULTI_PROJECT_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [SV_VARIANT4], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA,
        )

        gt_inheritance_filter = {'genotype': {'I000006_hg00733': 'ref_ref', 'I000005_hg00732': 'has_alt'}}
        await self._assert_expected_search(
            [VARIANT2], inheritance_filter=gt_inheritance_filter, sample_data=FAMILY_2_VARIANT_SAMPLE_DATA)

        inheritance_mode = 'compound_het'
        await self._assert_expected_search(
            [[VARIANT3, VARIANT4]], inheritance_mode=inheritance_mode, sample_data=MULTI_PROJECT_SAMPLE_DATA, gene_counts={
                'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000177000': {'total': 1, 'families': {'F000002_2': 1}},
            }, **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [[GCNV_VARIANT3, GCNV_VARIANT4]], inheritance_mode=inheritance_mode, omit_data_type='SNV_INDEL', gene_counts={
                'ENSG00000275023': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000277972': {'total': 1, 'families': {'F000002_2': 1}},
            }, **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, VARIANT4], [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode=inheritance_mode, gene_counts={
                'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000275023': {'total': 3, 'families': {'F000002_2': 3}},
                'ENSG00000277258': {'total': 3, 'families': {'F000002_2': 3}},
                'ENSG00000277972': {'total': 2, 'families': {'F000002_2': 2}},
            }, **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2]], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA,
            **COMP_HET_ALL_PASS_FILTERS, gene_counts={'ENSG00000171621': {'total': 2, 'families': {'F000011_11': 2}}},
        )

        await self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2], [VARIANT3, VARIANT4]], inheritance_mode=inheritance_mode,
            sample_data={**SV_WGS_SAMPLE_DATA, **FAMILY_2_VARIANT_SAMPLE_DATA}, **COMP_HET_ALL_PASS_FILTERS, gene_counts={
                'ENSG00000171621': {'total': 2, 'families': {'F000011_11': 2}},
                'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000177000': {'total': 1, 'families': {'F000002_2': 1}},
            },
        )

        inheritance_mode = 'recessive'
        await self._assert_expected_search(
            [PROJECT_2_VARIANT1, VARIANT2, [VARIANT3, VARIANT4]], inheritance_mode=inheritance_mode, gene_counts={
                'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000177000': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
            }, sample_data=MULTI_PROJECT_SAMPLE_DATA, **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]], inheritance_mode=inheritance_mode, omit_data_type='SNV_INDEL', gene_counts={
                'ENSG00000275023': {'total': 3, 'families': {'F000002_2': 3}},
                'ENSG00000277258': {'total': 1, 'families': {'F000002_2': 1}},
                'ENSG00000277972': {'total': 1, 'families': {'F000002_2': 1}},
            }, **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, VARIANT4], GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode=inheritance_mode, gene_counts={
                'ENSG00000097046': {'total': 2, 'families': {'F000002_2': 2}},
                'ENSG00000177000': {'total': 3, 'families': {'F000002_2': 3}},
                'ENSG00000275023': {'total': 4, 'families': {'F000002_2': 4}},
                'ENSG00000277258': {'total': 4, 'families': {'F000002_2': 4}},
                'ENSG00000277972': {'total': 2, 'families': {'F000002_2': 2}},
            }, **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2], SV_VARIANT4], inheritance_mode=inheritance_mode, sample_data=SV_WGS_SAMPLE_DATA,
            **COMP_HET_ALL_PASS_FILTERS, gene_counts={
                'ENSG00000171621': {'total': 2, 'families': {'F000011_11': 2}},
                'ENSG00000184986': {'total': 1, 'families': {'F000011_11': 1}},
            }
        )

    async def test_quality_filter(self):
        quality_filter = {'vcf_filter': 'pass'}
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            quality_filter=quality_filter
        )

        await self._assert_expected_search(
            [SV_VARIANT4, MITO_VARIANT1, MITO_VARIANT2], quality_filter=quality_filter,
            sample_data={**SV_WGS_SAMPLE_DATA, **FAMILY_2_MITO_SAMPLE_DATA}
        )

        await self._assert_expected_search(
            [MITO_VARIANT1, MITO_VARIANT3], quality_filter={'min_gq': 60, 'min_hl': 5}, sample_data=FAMILY_2_MITO_SAMPLE_DATA,
        )

        gcnv_quality_filter = {'min_gq': 40, 'min_qs': 20}
        await self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT4], quality_filter=gcnv_quality_filter,
        )

        await self._assert_expected_search(
            [], annotations=NEW_SV_FILTER, quality_filter=gcnv_quality_filter, omit_data_type='SNV_INDEL',
        )

        sv_quality_filter = {'min_gq_sv': 40}
        await self._assert_expected_search(
            [SV_VARIANT3, SV_VARIANT4], quality_filter=sv_quality_filter, sample_data=SV_WGS_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [], annotations=NEW_SV_FILTER, quality_filter=sv_quality_filter, sample_data=SV_WGS_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT], quality_filter={'min_gq': 40, 'vcf_filter': 'pass'}, omit_data_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            quality_filter={'min_gq': 60, 'min_qs': 10, 'affected_only': True},
        )

        await self._assert_expected_search(
            [SV_VARIANT3, SV_VARIANT4], quality_filter={'min_gq_sv': 60, 'affected_only': True}, sample_data=SV_WGS_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [VARIANT1, VARIANT2, FAMILY_3_VARIANT], quality_filter={'min_ab': 50}, omit_data_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT2, VARIANT3], quality_filter={'min_ab': 70, 'affected_only': True},
            omit_data_type='SV_WES',
        )

        quality_filter.update({'min_gq': 40, 'min_ab': 50})
        await self._assert_expected_search(
            [VARIANT2, FAMILY_3_VARIANT], quality_filter=quality_filter, omit_data_type='SV_WES',
        )

        annotations = {'splice_ai': '0.0'}  # Ensures no variants are filtered out by annotation/path filters
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, FAMILY_3_VARIANT, MITO_VARIANT1, MITO_VARIANT3], quality_filter=quality_filter, omit_data_type='SV_WES',
            annotations=annotations, pathogenicity={'clinvar': ['likely_pathogenic', 'vus_or_conflicting']},
            sample_data={**EXPECTED_SAMPLE_DATA, **FAMILY_2_MITO_SAMPLE_DATA},
        )

        await self._assert_expected_search(
            [VARIANT2, FAMILY_3_VARIANT], quality_filter=quality_filter, omit_data_type='SV_WES',
            annotations=annotations, pathogenicity={'clinvar': ['pathogenic']},
        )

    async def test_location_search(self):
        await self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4], omit_data_type='SV_WES', **LOCATION_SEARCH,
        )

        # Test "large" gene list search
        # Expect VARIANT2 to be filtered out due to intervals
        await self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4], omit_data_type='SV_WES', intervals=LOCATION_SEARCH['intervals'],
            gene_ids=LOCATION_SEARCH['gene_ids'] + ['ENSG00000277258', 'ENSG00000275023'],
        )

        await self._assert_expected_search(
            [GRCH37_VARIANT], intervals=[['7', 143268894, 143271480]], genome_version='GRCh37', sample_data=FAMILY_2_VARIANT_SAMPLE_DATA)

        sv_intervals = [['1', 9310023, 9380264], ['17', 38717636, 38724781]]
        await self._assert_expected_search(
            [GCNV_VARIANT3, GCNV_VARIANT4], intervals=sv_intervals, gene_ids=['ENSG00000275023'], omit_data_type='SNV_INDEL',
        )

        await self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2], sample_data=SV_WGS_SAMPLE_DATA, intervals=sv_intervals, gene_ids=['ENSG00000171621'],
        )

        await self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], intervals=sv_intervals,
            sample_data={'SV_WES': EXPECTED_SAMPLE_DATA['SV_WES'], **SV_WGS_SAMPLE_DATA},
        )

        await self._assert_expected_search(
            [VARIANT1, VARIANT2], omit_data_type='SV_WES', **EXCLUDE_LOCATION_SEARCH,
        )

        await self._assert_expected_search(
            [GCNV_VARIANT1, GCNV_VARIANT2], intervals=sv_intervals, exclude_intervals=True, omit_data_type='SNV_INDEL',
        )

        await self._assert_expected_search(
            [SV_VARIANT3, SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, intervals=sv_intervals, exclude_intervals=True,
        )

        await self._assert_expected_search(
            [SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT],  omit_data_type='SV_WES',
            intervals=LOCATION_SEARCH['intervals'][-1:], gene_ids=LOCATION_SEARCH['gene_ids'][:1]
        )

        await self._assert_expected_search(
            [GCNV_VARIANT4], padded_interval={'chrom': '17', 'start': 38720781, 'end': 38738703, 'padding': 0.2},
            omit_data_type='SNV_INDEL',
        )

        await self._assert_expected_search(
            [], padded_interval={'chrom': '17', 'start': 38720781, 'end': 38738703, 'padding': 0.1},
            omit_data_type='SNV_INDEL',
        )

        await self._assert_expected_search(
            [SV_VARIANT4], padded_interval={'chrom': '14', 'start': 106692244, 'end': 106742587, 'padding': 0.1},
            sample_data=SV_WGS_SAMPLE_DATA,
        )

        # For gene search, return SVs annotated in gene even if they fall outside the gene interval
        nearest_tss_gene_intervals = [['1', 9292894, 9369532]]
        await self._assert_expected_search(
            [SV_VARIANT1], sample_data=SV_WGS_SAMPLE_DATA, intervals=nearest_tss_gene_intervals,
        )
        await self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT2], sample_data=SV_WGS_SAMPLE_DATA, intervals=nearest_tss_gene_intervals,
            gene_ids=['ENSG00000171621'],
        )

    async def test_cluster_intervals(self):
        intervals = [
            ['1', 11785723, 11806455], ['1', 91500851, 91525764], ['2', 1234, 5678], ['2', 12345, 67890],
            ['7', 1, 11100], ['7', 202020, 20202020],
        ]

        self.assertListEqual(BaseHailTableQuery.cluster_intervals(intervals, max_intervals=5), [
            ['1', 11785723, 11806455], ['1', 91500851, 91525764], ['2', 1234, 67890],
            ['7', 1, 11100], ['7', 202020, 20202020],
        ])

        self.assertListEqual(BaseHailTableQuery.cluster_intervals(intervals, max_intervals=4), [
            ['1', 11785723, 11806455], ['1', 91500851, 91525764], ['2', 1234, 67890], ['7', 1, 20202020],
        ])

        self.assertListEqual(BaseHailTableQuery.cluster_intervals(intervals, max_intervals=3), [
            ['1', 11785723, 91525764], ['2', 1234, 67890], ['7', 1, 20202020],
        ])


    async def test_variant_id_search(self):
        await self._assert_expected_search([VARIANT2], omit_data_type='SV_WES', **RSID_SEARCH)

        await self._assert_expected_search([VARIANT1], omit_data_type='SV_WES', **VARIANT_ID_SEARCH)

        await self._assert_expected_search(
            [VARIANT1], omit_data_type='SV_WES', variant_ids=VARIANT_ID_SEARCH['variant_ids'][:1],
        )

        await self._assert_expected_search(
            [], omit_data_type='SV_WES', variant_ids=VARIANT_ID_SEARCH['variant_ids'][1:],
        )

        variant_keys = ['suffix_95340_DUP', 'suffix_140608_DUP']
        await self._assert_expected_search([GCNV_VARIANT1, GCNV_VARIANT4], omit_data_type='SNV_INDEL', variant_keys=variant_keys)

        await self._assert_expected_search([VARIANT1, GCNV_VARIANT1, GCNV_VARIANT4], variant_keys=variant_keys, **VARIANT_ID_SEARCH)

        await self._assert_expected_search([SV_VARIANT2, SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, variant_keys=[
            'cohort_2911.chr1.final_cleanup_INS_chr1_160', 'phase2_DEL_chr14_4640',
        ])

    async def test_variant_lookup(self):
        body = {'genome_version': 'GRCh38', 'variant_id': VARIANT_ID_SEARCH['variant_ids'][0]}
        async with self.client.request('POST', '/lookup', json=body) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, VARIANT_LOOKUP_VARIANT)

        body['variant_id'] = VARIANT_ID_SEARCH['variant_ids'][1]
        async with self.client.request('POST', '/lookup', json=body) as resp:
            self.assertEqual(resp.status, 404)

        body.update({'genome_version': 'GRCh37', 'variant_id': ['7', 143270172, 'A', 'G']})
        async with self.client.request('POST', '/lookup', json=body) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, {
            **{k: v for k, v in GRCH37_VARIANT.items() if k not in {'familyGuids', 'genotypes', 'genotypeFilters'}},
            'familyGenotypes': {GRCH37_VARIANT['familyGuids'][0]: [
                {k: v for k, v in g[0].items() if k != 'individualGuid'} for g in GRCH37_VARIANT['genotypes'].values()
            ]},
        })

        body.update({'variant_id': ['M', 4429, 'G', 'A'], 'data_type': 'MITO', 'genome_version': 'GRCh38'})
        async with self.client.request('POST', '/lookup', json=body) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, {
            **{k: v for k, v in MITO_VARIANT1.items() if k not in {'familyGuids', 'genotypes', 'genotypeFilters'}},
            'familyGenotypes': {MITO_VARIANT1['familyGuids'][0]: [
                {k: v for k, v in g[0].items() if k != 'individualGuid'} for g in MITO_VARIANT1['genotypes'].values()
            ]},
        })

        body.update({'variant_id': 'phase2_DEL_chr14_4640', 'data_type': 'SV_WGS', 'sample_data': SV_WGS_SAMPLE_DATA['SV_WGS']})
        async with self.client.request('POST', '/lookup', json=body) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, SV_VARIANT4)

        body.update({'variant_id': 'suffix_140608_DUP', 'data_type': 'SV_WES', 'sample_data': EXPECTED_SAMPLE_DATA['SV_WES']})
        async with self.client.request('POST', '/lookup', json=body) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, {
            **NO_GENOTYPE_GCNV_VARIANT, 'genotypes': {
                individual: [{k: v for k, v in sample.items() if k not in {'start', 'end', 'numExon', 'geneIds'}}  for sample in genotypes]
                for individual, genotypes in GCNV_VARIANT4['genotypes'].items()
            }
        })

        body['variant_id'] = 'suffix_140608_DEL'
        async with self.client.request('POST', '/lookup', json=body) as resp:
            self.assertEqual(resp.status, 404)

    async def test_multi_variant_lookup(self):
        await self._test_multi_lookup(VARIANT_ID_SEARCH['variant_ids'], 'SNV_INDEL', [VARIANT1])

        await self._test_multi_lookup([['7', 143270172, 'A', 'G']], 'SNV_INDEL', [GRCH37_VARIANT], genome_version='GRCh37')

        await self._test_multi_lookup([['M', 4429, 'G', 'A'], ['M', 14783, 'T', 'C']], 'MITO', [MITO_VARIANT1, MITO_VARIANT3])

        await self._test_multi_lookup(
            ['cohort_2911.chr1.final_cleanup_INS_chr1_160', 'phase2_DEL_chr14_4640'],
            'SV_WGS', [SV_VARIANT2, SV_VARIANT4],
        )

        await self._test_multi_lookup(['suffix_140608_DUP'], 'SV_WES', [NO_GENOTYPE_GCNV_VARIANT])

    async def _test_multi_lookup(self, variant_ids, data_type, results, genome_version='GRCh38'):
        body = {'genome_version': genome_version, 'data_type': data_type, 'variant_ids': variant_ids}
        async with self.client.request('POST', '/multi_lookup', json=body) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, {'results': [
            {k: v for k, v in variant.items() if k not in {'familyGuids', 'genotypes', 'genotypeFilters'}}
            for variant in results
        ]})

    async def test_frequency_filter(self):
        sv_callset_filter = {'sv_callset': {'af': 0.05}}
        await self._assert_expected_search(
            [VARIANT1, VARIANT4, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            frequencies={'seqr': {'af': 0.2}, **sv_callset_filter},
        )

        await self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4], frequencies={'seqr': {'ac': 4}}, omit_data_type='SV_WES',
        )

        await self._assert_expected_search(
            [MULTI_FAMILY_VARIANT, VARIANT4], frequencies={'seqr': {'hh': 1}}, omit_data_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT4], frequencies={'seqr': {'ac': 4, 'hh': 0}}, omit_data_type='SV_WES',
        )

        await self._assert_expected_search(
            [MITO_VARIANT1, MITO_VARIANT2], frequencies={'seqr': {'af': 0.01}}, sample_data=FAMILY_2_MITO_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [SV_VARIANT1], frequencies=sv_callset_filter, sample_data=SV_WGS_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT4], frequencies={'gnomad_genomes': {'af': 0.05}}, omit_data_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT2, VARIANT4], frequencies={'gnomad_genomes': {'af': 0.05, 'hh': 1}}, omit_data_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT2, VARIANT4, MITO_VARIANT1, MITO_VARIANT2], sample_data=FAMILY_2_ALL_SAMPLE_DATA,
            frequencies={'gnomad_genomes': {'af': 0.005}, 'gnomad_mito': {'af': 0.05}},
        )

        await self._assert_expected_search(
            [SV_VARIANT1, SV_VARIANT3, SV_VARIANT4], frequencies={'gnomad_svs': {'af': 0.001}}, sample_data=SV_WGS_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [VARIANT4], frequencies={'seqr': {'af': 0.2}, 'gnomad_genomes': {'ac': 50}},
            omit_data_type='SV_WES',
        )

        await self._assert_expected_search(
            [VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], frequencies={'seqr': {}, 'gnomad_genomes': {'af': None}},
            omit_data_type='SV_WES',
        )

        annotations = {'splice_ai': '0.0'}  # Ensures no variants are filtered out by annotation/path filters
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, VARIANT4], frequencies={'gnomad_genomes': {'af': 0.01}}, omit_data_type='SV_WES',
            annotations=annotations, pathogenicity={'clinvar': ['pathogenic', 'likely_pathogenic', 'vus_or_conflicting']},
        )

        await self._assert_expected_search(
            [VARIANT2, VARIANT4], frequencies={'gnomad_genomes': {'af': 0.01}}, omit_data_type='SV_WES',
            annotations=annotations, pathogenicity={'clinvar': ['pathogenic', 'vus_or_conflicting']},
        )

    async def test_annotations_filter(self):
        await self._assert_expected_search([VARIANT2], pathogenicity={'hgmd': ['hgmd_other']}, omit_data_type='SV_WES')

        pathogenicity = {'clinvar': ['likely_pathogenic', 'vus_or_conflicting', 'benign']}
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, MITO_VARIANT1, MITO_VARIANT3], pathogenicity=pathogenicity, sample_data=FAMILY_2_ALL_SAMPLE_DATA,
        )

        pathogenicity['clinvar'] = pathogenicity['clinvar'][:1]
        annotations = {'SCREEN': ['CTCF-only', 'DNase-only'], 'UTRAnnotator': ['5_prime_UTR_stop_codon_loss_variant']}
        selected_transcript_variant_2 = {**VARIANT2, 'selectedMainTranscriptId': 'ENST00000408919'}
        await self._assert_expected_search(
            [VARIANT1, selected_transcript_variant_2, VARIANT4, MITO_VARIANT3], pathogenicity=pathogenicity, annotations=annotations,
            sample_data=FAMILY_2_ALL_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [], pathogenicity=pathogenicity, annotations=annotations, sample_data=FAMILY_2_VARIANT_SAMPLE_DATA,
            genome_version='GRCh37',
        )

        annotations = {
            'missense': ['missense_variant'], 'in_frame': ['inframe_insertion', 'inframe_deletion'], 'frameshift': None,
            'structural_consequence': ['INTRONIC', 'LOF'],
        }
        await self._assert_expected_search(
            [VARIANT1, VARIANT2, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4, MITO_VARIANT2, MITO_VARIANT3], pathogenicity=pathogenicity,
            annotations=annotations, sample_data=FAMILY_2_ALL_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [VARIANT2, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], annotations=annotations,
        )

        await self._assert_expected_search([SV_VARIANT1], annotations=annotations, sample_data=SV_WGS_SAMPLE_DATA)

        annotations['splice_ai'] = '0.005'
        annotations['structural'] = ['gCNV_DUP', 'DEL']
        await self._assert_expected_search(
            [VARIANT2, MULTI_FAMILY_VARIANT, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4, GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            annotations=annotations,
        )

        await self._assert_expected_search([SV_VARIANT1, SV_VARIANT4], annotations=annotations, sample_data=SV_WGS_SAMPLE_DATA)

        annotations = {'other': ['non_coding_transcript_exon_variant__canonical', 'non_coding_transcript_exon_variant']}
        await self._assert_expected_search(
            [VARIANT1, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_3, MITO_VARIANT1, MITO_VARIANT3],
            pathogenicity=pathogenicity, annotations=annotations, sample_data=FAMILY_2_ALL_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, SELECTED_TRANSCRIPT_MULTI_FAMILY_VARIANT],
            gene_ids=LOCATION_SEARCH['gene_ids'][:1], annotations=annotations, omit_data_type='SV_WES',
        )

        annotations['other'] = annotations['other'][:1]
        annotations['splice_ai'] = '0.005'
        await self._assert_expected_search(
            [VARIANT1, VARIANT3, MITO_VARIANT1, MITO_VARIANT3],
            pathogenicity=pathogenicity, annotations=annotations, sample_data=FAMILY_2_ALL_SAMPLE_DATA,
        )

        annotations['extended_splice_site'] = ['extended_intronic_splice_region_variant']
        await self._assert_expected_search(
            [VARIANT1, VARIANT3, VARIANT4, MITO_VARIANT1, MITO_VARIANT3],
            pathogenicity=pathogenicity, annotations=annotations, sample_data=FAMILY_2_ALL_SAMPLE_DATA,
        )

        annotations = {'motif_feature': ['TF_binding_site_variant'], 'regulatory_feature': ['regulatory_region_variant']}
        await self._assert_expected_search(
            [VARIANT3, VARIANT4], annotations=annotations, sample_data=FAMILY_2_VARIANT_SAMPLE_DATA,
        )

    async def test_secondary_annotations_filter(self):
        annotations_1 = {'missense': ['missense_variant']}
        annotations_2 = {'other': ['intron_variant']}

        await self._assert_expected_search(
            [[VARIANT3, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4]], inheritance_mode='compound_het', omit_data_type='SV_WES',
            annotations=annotations_1, annotations_secondary=annotations_2,
        )

        await self._assert_expected_search(
            [VARIANT2, [VARIANT3, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4]], inheritance_mode='recessive', omit_data_type='SV_WES',
            annotations=annotations_1, annotations_secondary=annotations_2,
        )

        await self._assert_expected_search(
            [[VARIANT3, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4]], inheritance_mode='recessive', omit_data_type='SV_WES',
            annotations=annotations_2, annotations_secondary=annotations_1,
        )

        gcnv_annotations_1 = {'structural': ['gCNV_DUP']}
        gcnv_annotations_2 = {'structural_consequence': ['LOF'], 'structural': []}

        await self._assert_expected_search(
            [[GCNV_VARIANT3, GCNV_VARIANT4]], omit_data_type='SNV_INDEL', inheritance_mode='compound_het',
            annotations=gcnv_annotations_1, annotations_secondary=gcnv_annotations_2,
        )

        await self._assert_expected_search(
            [GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]], omit_data_type='SNV_INDEL', inheritance_mode='recessive',
            annotations=gcnv_annotations_2, annotations_secondary=gcnv_annotations_1,
        )

        # Do not return pairs where annotations match in a non-paired gene
        gcnv_annotations_no_pair = {'structural_consequence': ['COPY_GAIN']}
        await self._assert_expected_search(
            [], omit_data_type='SNV_INDEL', inheritance_mode='compound_het',
            annotations=gcnv_annotations_1, annotations_secondary=gcnv_annotations_no_pair,
        )

        await self._assert_expected_search(
            [], omit_data_type='SNV_INDEL', inheritance_mode='compound_het',
            annotations={**gcnv_annotations_1, **gcnv_annotations_no_pair},
        )

        await self._assert_expected_search(
            [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4]], inheritance_mode='compound_het',
            annotations=annotations_1, annotations_secondary=gcnv_annotations_2,
        )

        await self._assert_expected_search(
            [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [VARIANT3, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4], GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode='recessive',
            annotations={**annotations_1, **gcnv_annotations_1}, annotations_secondary={**annotations_2, **gcnv_annotations_2},
        )

        sv_annotations_1 = {'structural': ['INS', 'LOF']}
        sv_annotations_2 = {'structural': ['DEL', 'gCNV_DUP'], 'structural_consequence': ['INTRONIC']}

        await self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2]], sample_data=SV_WGS_SAMPLE_DATA, inheritance_mode='compound_het',
            annotations=sv_annotations_1, annotations_secondary=sv_annotations_2,
        )

        await self._assert_expected_search(
            [[SV_VARIANT1, SV_VARIANT2], SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, inheritance_mode='recessive',
            annotations=sv_annotations_2, annotations_secondary=sv_annotations_1,
        )

        pathogenicity = {'clinvar': ['likely_pathogenic', 'vus_or_conflicting']}
        await self._assert_expected_search(
            [VARIANT2, [VARIANT3, SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_4]], inheritance_mode='recessive', omit_data_type='SV_WES',
            annotations=annotations_2, annotations_secondary=annotations_1, pathogenicity=pathogenicity,
        )

        await self._assert_expected_search(
            [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode='compound_het', pathogenicity=pathogenicity,
            annotations=gcnv_annotations_2, annotations_secondary=gcnv_annotations_1,
        )

        await self._assert_expected_search(
            [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]],
            inheritance_mode='recessive', pathogenicity=pathogenicity,
            annotations=gcnv_annotations_2, annotations_secondary=gcnv_annotations_1,
        )

        selected_transcript_annotations = {'other': ['non_coding_transcript_exon_variant']}
        await self._assert_expected_search(
            [VARIANT2, [MULTI_DATA_TYPE_COMP_HET_VARIANT2, GCNV_VARIANT4], GCNV_VARIANT3],
            inheritance_mode='recessive', pathogenicity=pathogenicity,
            annotations=gcnv_annotations_2, annotations_secondary=selected_transcript_annotations,
        )

        # Search works with a different number of samples within the family
        missing_gt_gcnv_variant = {
            **GCNV_VARIANT4, 'genotypes': {k: v for k, v in GCNV_VARIANT4['genotypes'].items() if k != 'I000005_hg00732'}
        }
        await self._assert_expected_search(
            [[MULTI_DATA_TYPE_COMP_HET_VARIANT2, missing_gt_gcnv_variant]],
            inheritance_mode='compound_het', pathogenicity=pathogenicity,
            annotations=gcnv_annotations_2, annotations_secondary=selected_transcript_annotations,
            sample_data={**EXPECTED_SAMPLE_DATA, 'SV_WES': [EXPECTED_SAMPLE_DATA['SV_WES'][0], EXPECTED_SAMPLE_DATA['SV_WES'][2]]}

        )

        # Do not return pairs where annotations match in a non-paired gene
        await self._assert_expected_search(
            [GCNV_VARIANT3], inheritance_mode='recessive',
            annotations=gcnv_annotations_2, annotations_secondary=selected_transcript_annotations,
        )

        screen_annotations = {'SCREEN': ['CTCF-only']}
        await self._assert_expected_search(
            [], inheritance_mode='recessive', omit_data_type='SV_WES',
            annotations=screen_annotations, annotations_secondary=annotations_1,
        )

        await self._assert_expected_search(
            [[VARIANT3, VARIANT4]], inheritance_mode='recessive', omit_data_type='SV_WES',
            annotations=screen_annotations, annotations_secondary=annotations_2,
        )

        await self._assert_expected_search(
            [VARIANT2, [SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_3, VARIANT4]], inheritance_mode='recessive',
            annotations=screen_annotations, annotations_secondary=selected_transcript_annotations,
            pathogenicity=pathogenicity, omit_data_type='SV_WES',
        )

        await self._assert_expected_search(
            [SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, [SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_3, VARIANT4]],
            annotations={**selected_transcript_annotations, **screen_annotations}, annotations_secondary=annotations_2,
            inheritance_mode='recessive', omit_data_type='SV_WES',
        )

    async def test_in_silico_filter(self):
        in_silico = {'eigen': '3.5', 'mut_taster': 'N', 'vest': 0.5}
        await self._assert_expected_search(
            [VARIANT1, VARIANT4, MITO_VARIANT1, MITO_VARIANT2, MITO_VARIANT3], in_silico=in_silico,
            sample_data=FAMILY_2_ALL_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [GRCH37_VARIANT], genome_version='GRCh37', in_silico=in_silico,
            sample_data=FAMILY_2_VARIANT_SAMPLE_DATA,
        )

        in_silico['requireScore'] = True
        in_silico.pop('eigen')
        await self._assert_expected_search(
            [VARIANT4, MITO_VARIANT2], in_silico=in_silico, sample_data=FAMILY_2_ALL_SAMPLE_DATA,
        )

        sv_in_silico = {'strvctvre': 0.1, 'requireScore': True}
        await self._assert_expected_search(
            [GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], omit_data_type='SNV_INDEL', in_silico=sv_in_silico,
        )

        await self._assert_expected_search(
            [SV_VARIANT4], sample_data=SV_WGS_SAMPLE_DATA, in_silico=sv_in_silico,
        )

    async def test_search_errors(self):
        search_body = get_hail_search_body(sample_data=FAMILY_2_MISSING_SAMPLE_DATA)
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 400)
            reason = resp.reason
        self.assertEqual(reason, 'The following samples are available in seqr but missing the loaded data: NA19675_1, NA19678')

        search_body = get_hail_search_body(sample_data=MULTI_PROJECT_MISSING_SAMPLE_DATA)
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 400)
            reason = resp.reason
        self.assertEqual(reason, 'The following samples are available in seqr but missing the loaded data: NA19675_1, NA19678')

        search_body = get_hail_search_body(
            intervals=LOCATION_SEARCH['intervals'] + [['1', 1, 999999999]], omit_data_type='SV_WES',
        )
        async with self.client.request('POST', '/search', json=search_body) as resp:
            self.assertEqual(resp.status, 400)
            reason = resp.reason
        self.assertEqual(reason, 'Invalid intervals: 1:1-999999999')

    async def test_sort(self):
        await self._assert_expected_search(
            [_sorted(VARIANT4, [2, 2]), _sorted(MITO_VARIANT2, [11, 11]), _sorted(VARIANT2, [12, 12]),
             _sorted(MITO_VARIANT3, [17, 17]),  _sorted(MITO_VARIANT1, [22, 22]), _sorted(VARIANT3, [26, 27]),
             _sorted(VARIANT1, [None, None])], sample_data=FAMILY_2_ALL_SAMPLE_DATA, sort='protein_consequence',
        )

        await self._assert_expected_search(
            [_sorted(GCNV_VARIANT2, [0]), _sorted(GCNV_VARIANT3, [0]), _sorted(GCNV_VARIANT4, [0]),
             _sorted(GCNV_VARIANT1, [3])], omit_data_type='SNV_INDEL', sort='protein_consequence',
        )

        await self._assert_expected_search(
            [_sorted(VARIANT4, [2, 2]), _sorted(GCNV_VARIANT2, [4.5, 0]), _sorted(GCNV_VARIANT3, [4.5, 0]), _sorted(GCNV_VARIANT4, [4.5, 0]),
             _sorted(GCNV_VARIANT1, [4.5, 3]), _sorted(VARIANT2, [12, 12]),
             _sorted(MULTI_FAMILY_VARIANT, [26, 27]), _sorted(VARIANT1, [None, None])], sort='protein_consequence',
        )

        await self._assert_expected_search(
            [_sorted(SV_VARIANT1, [11]), _sorted(SV_VARIANT2, [12]), _sorted(SV_VARIANT3, [12]), _sorted(SV_VARIANT4, [12])],
             sample_data=SV_WGS_SAMPLE_DATA, sort='protein_consequence',
        )

        await self._assert_expected_search(
            [_sorted(VARIANT4, [2, 2]), _sorted(SELECTED_ANNOTATION_TRANSCRIPT_VARIANT_2, [12, 26]),
             _sorted(SELECTED_ANNOTATION_TRANSCRIPT_MULTI_FAMILY_VARIANT, [26, 26])],
            omit_data_type='SV_WES', sort='protein_consequence',
            annotations={'other': ['non_coding_transcript_exon_variant'], 'splice_ai': '0'},
        )

        await self._assert_expected_search(
            [_sorted(VARIANT1, [4]), _sorted(VARIANT2, [8]), _sorted(MULTI_FAMILY_VARIANT, [12.5]),
             _sorted(VARIANT4, [12.5]), GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], sort='pathogenicity',
        )

        await self._assert_expected_search(
            [ _sorted(MITO_VARIANT3, [4]), _sorted(VARIANT1, [4, None]), _sorted(VARIANT2, [8, 3]),
             _sorted(MITO_VARIANT1, [11]), _sorted(MITO_VARIANT2, [12.5]), _sorted(VARIANT3, [12.5, None]),
              _sorted(VARIANT4, [12.5, None])],
            sort='pathogenicity_hgmd', sample_data=FAMILY_2_ALL_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [_sorted(VARIANT2, [0]), _sorted(MITO_VARIANT1, [0]), _sorted(MITO_VARIANT2, [0]),
             _sorted(VARIANT4, [0.00026519427774474025]), _sorted(VARIANT1, [0.034449315071105957]),
             _sorted(MITO_VARIANT3, [0.05534649267792702]), _sorted(VARIANT3, [0.38041073083877563])],
            sort='gnomad', sample_data=FAMILY_2_ALL_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [_sorted(VARIANT1, [0]), _sorted(MULTI_FAMILY_VARIANT, [0]), _sorted(VARIANT4, [0]),
             _sorted(VARIANT2, [0.28899794816970825]), GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4],
            sort='gnomad_exomes',
        )

        await self._assert_expected_search(
            [_sorted(GCNV_VARIANT3, [0.0015185698866844177]), _sorted(GCNV_VARIANT4, [0.004989586770534515]),
             _sorted(GCNV_VARIANT2, [0.012322110123932362]), _sorted(VARIANT4, [0.02222222276031971]),
             _sorted(GCNV_VARIANT1, [0.076492540538311]), _sorted(VARIANT1, [0.10000000149011612]),
             _sorted(VARIANT2, [0.31111112236976624]), _sorted(MULTI_FAMILY_VARIANT, [0.6666666865348816])],
            sort='callset_af',
        )

        await self._assert_expected_search(
            [_sorted(MITO_VARIANT1, [0]), _sorted(MITO_VARIANT2, [0]), _sorted(MITO_VARIANT3, [0.019480518996715546]),
             _sorted(VARIANT4, [0.02222222276031971]), _sorted(VARIANT1, [0.10000000149011612]),
             _sorted(VARIANT2, [0.31111112236976624]), _sorted(VARIANT3, [0.6666666865348816])],
            sort='callset_af', sample_data=FAMILY_2_ALL_SAMPLE_DATA,
        )

        await self._assert_expected_search(
            [_sorted(VARIANT4, [-29.899999618530273]), _sorted(VARIANT2, [-20.899999618530273]),
             _sorted(VARIANT1, [-4.668000221252441]), _sorted(MULTI_FAMILY_VARIANT, [-2.753999948501587]),
             GCNV_VARIANT1, GCNV_VARIANT2, GCNV_VARIANT3, GCNV_VARIANT4], sort='cadd',
        )

        await self._assert_expected_search(
            [_sorted(VARIANT4, [-0.5260000228881836]), _sorted(VARIANT2, [-0.19699999690055847]),
             _sorted(VARIANT1, [0]), _sorted(MULTI_FAMILY_VARIANT, [0])], omit_data_type='SV_WES', sort='revel',
        )

        await self._assert_expected_search(
            [_sorted(MULTI_FAMILY_VARIANT, [-0.009999999776482582]), _sorted(VARIANT2, [0]), _sorted(VARIANT4, [0]),
             _sorted(VARIANT1, [0])], omit_data_type='SV_WES', sort='splice_ai',
        )

        await self._assert_expected_search(
            [_sorted(VARIANT2, [-0.9977999925613403, -0.9977999925613403]), _sorted(VARIANT1, [0, 0]),
             _sorted(MULTI_FAMILY_VARIANT, [0, 0]), _sorted(VARIANT4, [0, 0])], omit_data_type='SV_WES', sort='alphamissense',
        )

        sort = 'in_omim'
        await self._assert_expected_search(
            [_sorted(MULTI_FAMILY_VARIANT, [0, -2]), _sorted(VARIANT2, [0, -1]), _sorted(VARIANT4, [0, -1]), _sorted(VARIANT1, [1, 0])],
            omit_data_type='SV_WES', sort=sort, sort_metadata=OMIM_SORT_METADATA,
        )

        await self._assert_expected_search(
            [_sorted(GCNV_VARIANT3, [-1]), _sorted(GCNV_VARIANT4, [-1]), _sorted(GCNV_VARIANT1, [0]), _sorted(GCNV_VARIANT2, [0])],
            omit_data_type='SNV_INDEL', sort=sort, sort_metadata=OMIM_SORT_METADATA,
        )

        await self._assert_expected_search(
            [_sorted(MULTI_FAMILY_VARIANT, [0, -2]), _sorted(VARIANT2, [0, -1]), _sorted(VARIANT4, [0, -1]),
             _sorted(GCNV_VARIANT3, [0, -1]), _sorted(GCNV_VARIANT4, [0, -1]), _sorted(GCNV_VARIANT1, [0, 0]),
             _sorted(GCNV_VARIANT2, [0, 0]),  _sorted(VARIANT1, [1, 0])], sort=sort, sort_metadata=OMIM_SORT_METADATA,
        )

        await self._assert_expected_search(
            [_sorted(VARIANT2, [0, -1]), _sorted(MULTI_FAMILY_VARIANT, [1, -1]), _sorted(VARIANT1, [1, 0]), _sorted(VARIANT4, [1, 0])],
            omit_data_type='SV_WES', sort=sort, sort_metadata=['ENSG00000177000'],
        )

        constraint_sort_metadata = {'ENSG00000177000': 2, 'ENSG00000275023': 3, 'ENSG00000097046': 4}
        sort = 'constraint'
        await self._assert_expected_search(
            [_sorted(VARIANT2, [2, 2]), _sorted(MULTI_FAMILY_VARIANT, [4, 2]), _sorted(VARIANT4, [4, 4]),
             _sorted(VARIANT1, [None, None])], omit_data_type='SV_WES', sort=sort, sort_metadata=constraint_sort_metadata,
        )

        await self._assert_expected_search(
            [_sorted(GCNV_VARIANT3, [3]), _sorted(GCNV_VARIANT4, [3]), _sorted(GCNV_VARIANT1, [None]),
             _sorted(GCNV_VARIANT2, [None])], omit_data_type='SNV_INDEL', sort=sort, sort_metadata=constraint_sort_metadata,
        )

        await self._assert_expected_search(
            [_sorted(VARIANT2, [2, 2]), _sorted(GCNV_VARIANT3, [3, 3]), _sorted(GCNV_VARIANT4, [3, 3]),
             _sorted(MULTI_FAMILY_VARIANT, [4, 2]), _sorted(VARIANT4, [4, 4]), _sorted(VARIANT1, [None, None]),
             _sorted(GCNV_VARIANT1, [None, None]), _sorted(GCNV_VARIANT2, [None, None])],
            sort=sort, sort_metadata=constraint_sort_metadata,
        )

        await self._assert_expected_search(
            [_sorted(VARIANT2, [3, 3]), _sorted(MULTI_FAMILY_VARIANT, [None, 3]), _sorted(VARIANT1, [None, None]),
             _sorted(VARIANT4, [None, None])], omit_data_type='SV_WES', sort='prioritized_gene',
            sort_metadata={'ENSG00000177000': 3},
        )

        # size sort only applies to SVs, so has no impact on other variant
        await self._assert_expected_search(
            [_sorted(GCNV_VARIANT1, [-171766]), _sorted(GCNV_VARIANT2, [-17768]), _sorted(GCNV_VARIANT4, [-14487]),
             _sorted(GCNV_VARIANT3, [-2666]), VARIANT1, VARIANT2, MULTI_FAMILY_VARIANT, VARIANT4], sort='size',
        )

        await self._assert_expected_search(
            [_sorted(SV_VARIANT4, [-46343]), _sorted(SV_VARIANT1, [-104]), _sorted(SV_VARIANT2, [-50]),
             _sorted(SV_VARIANT3, [-50])], sample_data=SV_WGS_SAMPLE_DATA, sort='size',
        )

        # sort applies to compound hets
        await self._assert_expected_search(
            [[_sorted(VARIANT4, [-0.5260000228881836]), _sorted(VARIANT3, [0])],
             _sorted(VARIANT2, [-0.19699999690055847])],
            sort='revel', inheritance_mode='recessive', omit_data_type='SV_WES', **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [[_sorted(VARIANT3, [-0.009999999776482582]),  _sorted(VARIANT4, [0])], _sorted(VARIANT2, [0])],
            sort='splice_ai', inheritance_mode='recessive', omit_data_type='SV_WES', **COMP_HET_ALL_PASS_FILTERS,
        )

    async def test_multi_data_type_comp_het_sort(self):
        await self._assert_expected_search(
            [[_sorted(VARIANT4, [2, 2]), _sorted(VARIANT3, [26, 27])],
             _sorted(GCNV_VARIANT3, [4.5, 0]), [_sorted(GCNV_VARIANT3, [0]), _sorted(GCNV_VARIANT4, [0])],
             [_sorted(GCNV_VARIANT4, [4.5, 0]), _sorted(MULTI_DATA_TYPE_COMP_HET_VARIANT2, [12, 12])],
             _sorted(VARIANT2, [12, 12])],
            sort='protein_consequence', inheritance_mode='recessive', **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [[_sorted(GCNV_VARIANT4, [-14487]), _sorted(GCNV_VARIANT3, [-2666])],
             [_sorted(GCNV_VARIANT4, [-14487]), MULTI_DATA_TYPE_COMP_HET_VARIANT2],
             [VARIANT3, VARIANT4]],
            sort='size', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [[_sorted(MULTI_DATA_TYPE_COMP_HET_VARIANT2, [8]), GCNV_VARIANT4],
             [_sorted(VARIANT3, [12.5]), _sorted(VARIANT4, [12.5])],
             [GCNV_VARIANT3, GCNV_VARIANT4]],
            sort='pathogenicity', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [[_sorted(VARIANT4, [-0.6869999766349792]), _sorted(VARIANT3, [0])], _sorted(VARIANT2, [0]),
             [_sorted(MULTI_DATA_TYPE_COMP_HET_VARIANT2, [0]), GCNV_VARIANT4],
             GCNV_VARIANT3, [GCNV_VARIANT3, GCNV_VARIANT4]],
            sort='mut_pred', inheritance_mode='recessive', **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [[_sorted(VARIANT3, [-0.009999999776482582]), _sorted(VARIANT4, [0])],
             [_sorted(MULTI_DATA_TYPE_COMP_HET_VARIANT2, [0]), GCNV_VARIANT4],
             [GCNV_VARIANT3, GCNV_VARIANT4]],
            sort='splice_ai', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [[_sorted(GCNV_VARIANT3, [-0.7860000133514404]), _sorted(GCNV_VARIANT4, [-0.7099999785423279])],
             [_sorted(GCNV_VARIANT4, [-0.7099999785423279]), MULTI_DATA_TYPE_COMP_HET_VARIANT2],
             [VARIANT3, VARIANT4]],
            sort='strvctvre', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [[_sorted(GCNV_VARIANT3, [0.0015185698866844177]), _sorted(GCNV_VARIANT4, [0.004989586770534515])],
             [_sorted(GCNV_VARIANT4, [0.004989586770534515]), _sorted(MULTI_DATA_TYPE_COMP_HET_VARIANT2, [0.31111112236976624])],
             [_sorted(VARIANT4, [0.02222222276031971]), _sorted(VARIANT3, [0.6666666865348816])]],
            sort='callset_af', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [[_sorted(VARIANT3, [0]), _sorted(VARIANT4, [0])],
             [_sorted(MULTI_DATA_TYPE_COMP_HET_VARIANT2, [0.28899794816970825]), GCNV_VARIANT4],
             [GCNV_VARIANT3, GCNV_VARIANT4]],
            sort='gnomad_exomes', inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS,
        )

        await self._assert_expected_search(
            [[_sorted(VARIANT3, [0, -2]), _sorted(VARIANT4, [0, -1])],
             [_sorted(GCNV_VARIANT3, [-1]), _sorted(GCNV_VARIANT4, [-1])],
             [_sorted(GCNV_VARIANT4, [0, -1]), _sorted(MULTI_DATA_TYPE_COMP_HET_VARIANT2, [1, -1])]],
            sort='in_omim', sort_metadata=OMIM_SORT_METADATA, inheritance_mode='compound_het', **COMP_HET_ALL_PASS_FILTERS,
        )
