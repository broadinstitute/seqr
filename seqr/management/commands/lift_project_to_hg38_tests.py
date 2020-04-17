#-*- coding: utf-8 -*-
import mock

from django.core.management import call_command
from django.test import TestCase

PROJECT_NAME = u'1kg project n\u00e5me with uni\u00e7\u00f8de'
PROJECT_GUID = 'R0001_1kg'
ELASTICSEARCH_INDEX = 'test_index'
INDEX_METADATA = {
                    "gencodeVersion": "25",
                    "hail_version": "0.2.24",
                    "genomeVersion": "38",
                    "sampleType": "WES",
                    "sourceFilePath": "test_index_alias_1_path.vcf.gz",
                }
SAMPLE_IDS = ["NA19679", "NA19675_1", "NA19678", "HG00731", "HG00732", "HG00732", "HG00733"]

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

ES_VARIANTS = [
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
            'gnomad_genomes': {'an': 30946, 'ac': 4, 'hom': 0, 'af': 0.00012925741614425127, 'hemi': 0,
                               'filter_af': 0.000437},
            'exac': {'an': 121308, 'ac': 8, 'hom': 0, 'af': 0.00006589, 'hemi': 0, 'filter_af': 0.0006726888333653661},
            'gnomad_exomes': {'an': 245930, 'ac': 16, 'hom': 0, 'af': 0.00006505916317651364, 'hemi': 0,
                              'filter_af': 0.0009151523074911753},
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
            'gnomad_exomes': {'an': 245714, 'ac': 6, 'hom': 0, 'af': 0.000024418633044922146, 'hemi': 0,
                              'filter_af': 0.00016269686320447742},
            'topmed': {'an': 0, 'ac': 0, 'hom': 0, 'af': 0.0, 'hemi': 0, 'filter_af': None},
            'sv_callset': {'an': None, 'ac': None, 'hom': None, 'af': None, 'hemi': None, 'filter_af': None},
        },
        'pos': 103343353,
        'predictions': {
            'splice_ai': None, 'eigen': None, 'revel': None, 'mut_taster': None, 'fathmm': None, 'polyphen': None,
            'dann': None, 'sift': None, 'cadd': 17.26, 'metasvm': None, 'primate_ai': None, 'gerp_rs': None,
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


class LiftProjectToHg38Test(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('logging.getLogger')
    @mock.patch('seqr.views.utils.dataset_utils.get_elasticsearch_index_samples')
    @mock.patch('seqr.utils.elasticsearch.utils.get_es_variants_for_variant_tuples')
    def test_command(self, mock_get_es_variants, mock_get_es_samples, mock_getLogger):
        logger = mock_getLogger.return_value
        mock_get_es_samples.return_value = SAMPLE_IDS, INDEX_METADATA
        mock_get_es_variants.return_value = ES_VARIANTS
        call_command('lift_project_to_hg38', u'--project={}'.format(PROJECT_NAME),
                     '--es-index={}'.format(ELASTICSEARCH_INDEX))
        
        calls = [
            mock.call(u'Updating project genome version for {}'.format(PROJECT_NAME)),
            mock.call('Validating es index test_index')
        ]
        logger.info.assert_has_calls(calls)
