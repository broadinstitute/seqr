import unittest

import pandas as pd

from loading_pipeline.lib.misc.sv import (
    BREAKEND_EXON,
    COPY_GAIN,
    DUP_PARTIAL,
    INT_EXON_DUP,
    INTRONIC,
    INV_SPAN,
    LOF,
    MSV_EXON_OVERLAP,
    NEAREST_TSS,
    PARTIAL_EXON_DUP,
    PROMOTER,
    TSS_DUP,
    UTR,
    annotate_gene_consequences,
)

GENCODE_ROWS = [
    {
        'contig': 'chr1',
        'start': 100,
        'end': 1000,
        'strand': '+',
        'feature_type': 'transcript',
        'transcriptId': 'EMMA1-201',
        'geneId': 'EMMA1',
    },
    {
        'contig': 'chr1',
        'start': 300,
        'end': 400,
        'strand': '+',
        'feature_type': 'CDS',
        'transcriptId': 'EMMA1-201',
        'geneId': 'EMMA1',
    },
    {
        'contig': 'chr1',
        'start': 500,
        'end': 600,
        'strand': '+',
        'feature_type': 'CDS',
        'transcriptId': 'EMMA1-201',
        'geneId': 'EMMA1',
    },
    {
        'contig': 'chr1',
        'start': 100,
        'end': 200,
        'strand': '+',
        'feature_type': 'UTR',
        'transcriptId': 'EMMA1-201',
        'geneId': 'EMMA1',
    },
    {
        'contig': 'chr1',
        'start': 700,
        'end': 800,
        'strand': '+',
        'feature_type': 'UTR',
        'transcriptId': 'EMMA1-201',
        'geneId': 'EMMA1',
    },
    {
        'contig': 'chr1',
        'start': 900,
        'end': 1000,
        'strand': '+',
        'feature_type': 'UTR',
        'transcriptId': 'EMMA1-201',
        'geneId': 'EMMA1',
    },
    {
        'contig': 'chr1',
        'start': 2100,
        'end': 3000,
        'strand': '-',
        'feature_type': 'transcript',
        'transcriptId': 'EMMA2-201',
        'geneId': 'EMMA2',
    },
    {
        'contig': 'chr1',
        'start': 2500,
        'end': 2600,
        'strand': '-',
        'feature_type': 'CDS',
        'transcriptId': 'EMMA2-201',
        'geneId': 'EMMA2',
    },
    {
        'contig': 'chr1',
        'start': 2300,
        'end': 2400,
        'strand': '-',
        'feature_type': 'CDS',
        'transcriptId': 'EMMA2-201',
        'geneId': 'EMMA2',
    },
    {
        'contig': 'chr1',
        'start': 2900,
        'end': 3000,
        'strand': '-',
        'feature_type': 'UTR',
        'transcriptId': 'EMMA2-201',
        'geneId': 'EMMA2',
    },
    {
        'contig': 'chr1',
        'start': 2700,
        'end': 2800,
        'strand': '-',
        'feature_type': 'UTR',
        'transcriptId': 'EMMA2-201',
        'geneId': 'EMMA2',
    },
    {
        'contig': 'chr1',
        'start': 2100,
        'end': 2200,
        'strand': '-',
        'feature_type': 'UTR',
        'transcriptId': 'EMMA2-201',
        'geneId': 'EMMA2',
    },
    {
        'contig': 'chr1',
        'start': 2100,
        'end': 3500,
        'strand': '-',
        'feature_type': 'transcript',
        'transcriptId': 'EMMA2-202',
        'geneId': 'EMMA2',
    },
    {
        'contig': 'chr3',
        'start': 15000,
        'end': 15100,
        'strand': '+',
        'feature_type': 'transcript',
        'transcriptId': 'TBX30-201',
        'geneId': 'TBX30',
    },
    {
        'contig': 'chr3',
        'start': 20000,
        'end': 20100,
        'strand': '+',
        'feature_type': 'transcript',
        'transcriptId': 'TBX31-201',
        'geneId': 'TBX31',
    },
]


def _consequence(major_consequence, gene='EMMA1', transcript='201'):
    return {
        'geneId': gene,
        'transcriptId': f'{gene}-{transcript}',
        'majorConsequence': major_consequence,
    }


class AnnotateGeneConsequencesTest(unittest.TestCase):
    def _test_expected_consequences(
        self,
        expected,
        sv_type,
        input_overrides=None,
        **input_fields,
    ):
        df = pd.DataFrame.from_dict(
            {
                f'{sv_type}_{start}_{end}': {
                    'SVTYPE': sv_type,
                    '#CHROM': 'chr1',
                    'POS': start,
                    'END': end,
                    'sv_type_detail': None,
                    'CPX_INTERVALS': None,
                    'end_chrom': 'chr1',
                    'END2': None,
                    'SVLEN': end - start,
                    **input_fields,
                    **(input_overrides or {}).get((start, end), {}),
                }
                for start, end in expected
            },
            orient='index',
        )
        consequences = annotate_gene_consequences(df, pd.DataFrame(GENCODE_ROWS))
        self.assertEqual(
            consequences.to_dict(),
            {
                f'{sv_type}_{start}_{end}': [_consequence(*csqs) for csqs in expected_consequences]
                for (start, end), expected_consequences in expected.items()
            },
        )

    def test_deletions(self):
        self._test_expected_consequences(
            {
                (350, 550): [(LOF,)],
                (320, 360): [(LOF,)],
                (550, 750): [(LOF,)],
                (450, 650): [(LOF,)],
                (250, 850): [(LOF,)],
                (150, 450): [(LOF,)],
                (250, 350): [(LOF,)],
                (350, 650): [(LOF,)],
                (150, 250): [(UTR,)],
                (650, 850): [(UTR,)],
                (150, 750): [(LOF,)],
                (220, 280): [(INTRONIC,)],
                (750, 950): [(UTR,)],
                (50, 150): [(LOF,)],
                (50, 250): [(LOF,)],
                (50, 550): [(LOF,)],
                (50, 450): [(LOF,)],
                (950, 1500): [(UTR,)],
                (650, 950): [(UTR,)],
                (50, 2000): [(LOF,)],
                (750, 790): [(UTR,)],
                (350, 1200): [(LOF,)],
                (450, 1300): [(LOF,)],
                (5000, 6000): [(NEAREST_TSS, 'EMMA2', '202')],
                (1500, 1600): [(NEAREST_TSS, 'EMMA2')],
                (10500, 11000): [(NEAREST_TSS, 'TBX30')],
            },
            'DEL',
            input_overrides={(10500, 11000): {'#CHROM': 'chr3', 'end_chrom': 'chr3'}},
        )

        df = pd.DataFrame.from_dict(
            {
                'DEL_contig_without_tss': {
                    'SVTYPE': 'DEL',
                    '#CHROM': 'chr4',
                    'POS': 900,
                    'END': 4000,
                    'sv_type_detail': None,
                    'CPX_INTERVALS': None,
                    'end_chrom': 'chr4',
                    'END2': None,
                    'SVLEN': 3100,
                },
            },
            orient='index',
        )
        consequences = annotate_gene_consequences(df, pd.DataFrame(GENCODE_ROWS))
        self.assertEqual(consequences.to_dict(), {})

    def test_duplications(self):
        self._test_expected_consequences(
            {
                (350, 550): [(LOF,)],
                (320, 360): [(LOF,)],
                (550, 750): [(LOF,)],
                (450, 650): [(INT_EXON_DUP,)],
                (250, 850): [(INT_EXON_DUP,)],
                (150, 450): [(INT_EXON_DUP,)],
                (250, 350): [(PARTIAL_EXON_DUP,)],
                (350, 650): [(PARTIAL_EXON_DUP,)],
                (150, 250): [(UTR,)],
                (650, 850): [(UTR,)],
                (150, 750): [(INT_EXON_DUP,)],
                (220, 280): [(INTRONIC,)],
                (750, 950): [(UTR,)],
                (50, 150): [(TSS_DUP,)],
                (50, 250): [(TSS_DUP,)],
                (50, 550): [(TSS_DUP,)],
                (950, 1500): [(DUP_PARTIAL,)],
                (650, 950): [(UTR,)],
                (50, 2000): [(COPY_GAIN,)],
                (750, 790): [(UTR,)],
                (350, 1200): [(DUP_PARTIAL,)],
                (450, 1300): [(DUP_PARTIAL,)],
                (2000, 2200): [(DUP_PARTIAL, 'EMMA2'), (DUP_PARTIAL, 'EMMA2', '202')],
                (3100, 3300): [(INTRONIC, 'EMMA2', '202'), (PROMOTER, 'EMMA2')],
                (2950, 3000): [(TSS_DUP, 'EMMA2'), (INTRONIC, 'EMMA2', '202')],
                (300, 400): [(INT_EXON_DUP,)],
                (300, 350): [(LOF,)],
            },
            'DUP',
        )

    def test_copy_number_variants(self):
        self._test_expected_consequences(
            {
                (350, 550): [(MSV_EXON_OVERLAP,)],
                (320, 360): [(MSV_EXON_OVERLAP,)],
                (550, 750): [(MSV_EXON_OVERLAP,)],
                (450, 650): [(MSV_EXON_OVERLAP,)],
                (250, 850): [(MSV_EXON_OVERLAP,)],
                (150, 450): [(MSV_EXON_OVERLAP,)],
                (250, 350): [(MSV_EXON_OVERLAP,)],
                (350, 650): [(MSV_EXON_OVERLAP,)],
                (150, 250): [(UTR,)],
                (650, 850): [(UTR,)],
                (150, 750): [(MSV_EXON_OVERLAP,)],
                (220, 280): [(INTRONIC,)],
                (750, 950): [(UTR,)],
                (50, 150): [(MSV_EXON_OVERLAP,)],
                (50, 250): [(MSV_EXON_OVERLAP,)],
                (50, 550): [(MSV_EXON_OVERLAP,)],
                (950, 1500): [(MSV_EXON_OVERLAP,)],
                (650, 950): [(UTR,)],
                (50, 2000): [(MSV_EXON_OVERLAP,)],
                (750, 790): [(UTR,)],
                (350, 1200): [(MSV_EXON_OVERLAP,)],
                (450, 1300): [(MSV_EXON_OVERLAP,)],
                (10, 50): [(PROMOTER,)],
                (2950, 3000): [(MSV_EXON_OVERLAP, 'EMMA2'), (INTRONIC, 'EMMA2', '202')],
                (300, 400): [(MSV_EXON_OVERLAP,)],
                (300, 350): [(MSV_EXON_OVERLAP,)],
            },
            'CNV',
        )

    def test_inversions(self):
        self._test_expected_consequences(
            {
                (350, 550): [(LOF,)],
                (320, 360): [(LOF,)],
                (550, 750): [(LOF,)],
                (450, 650): [(LOF,)],
                (250, 850): [(LOF,)],
                (150, 450): [(LOF,)],
                (250, 350): [(LOF,)],
                (350, 650): [(LOF,)],
                (150, 250): [(UTR,)],
                (650, 850): [(UTR,)],
                (150, 750): [(LOF,)],
                (220, 280): [(INTRONIC,)],
                (750, 950): [(UTR,)],
                (50, 150): [(LOF,)],
                (50, 250): [(LOF,)],
                (50, 550): [(LOF,)],
                (950, 1500): [(UTR,)],
                (650, 950): [(UTR,)],
                (50, 2000): [(INV_SPAN,)],
                (750, 790): [(UTR,)],
                (350, 1200): [(LOF,)],
                (450, 1300): [(LOF,)],
                (1100, 1700): [(NEAREST_TSS,)],
            },
            'INV',
        )

    def test_insertions(self):
        self._test_expected_consequences(
            {
                (150, 151): [(UTR,)],
                (250, 251): [(INTRONIC,)],
                (350, 351): [(LOF,)],
                (600, 601): [(LOF,)],
                (100, 101): [(UTR,)],
                (1300, 1800): [(NEAREST_TSS,)],
            },
            'INS',
            input_overrides={
                (1300, 1800): {'sv_type_detail': 'ME:LINE1', 'SVLEN': 42},
            },
        )

    def test_breakends(self):
        expected = {
            (150, 150): [(UTR,)],
            (250, 250): [(INTRONIC,)],
            (350, 350): [(BREAKEND_EXON,)],
            (99, 99): [(PROMOTER,)],
            (3001, 3001): [(INTRONIC, 'EMMA2', '202'), (PROMOTER, 'EMMA2')],
            (4000, 4000): [(PROMOTER, 'EMMA2'), (PROMOTER, 'EMMA2', '202')],
            (4001, 4001): [(PROMOTER, 'EMMA2', '202')],
            (600, 600): [(BREAKEND_EXON,)],
            (100, 100): [(UTR,)],
            (1500, 1500): [(BREAKEND_EXON, 'EMMA2'), (INTRONIC, 'EMMA2', '202')],
            (500, 500): [(INTRONIC,)],
            (30, 30): [(INTRONIC, 'EMMA2', '202'), (PROMOTER,), (PROMOTER, 'EMMA2')],
            (550, 550): [(BREAKEND_EXON,), (INTRONIC, 'TBX30')],
            (520, 520): [(BREAKEND_EXON,), (INTRONIC,)],
            (1400, 1400): [(NEAREST_TSS, 'EMMA2', '202'), (NEAREST_TSS,)],
            (1600, 1600): [(NEAREST_TSS, 'EMMA2')],
        }
        self._test_expected_consequences(
            expected,
            'BND',
            input_overrides={
                **{(pos, end): {'END2': pos} for pos, end in list(expected)[:7]},
                (1500, 1500): {'END2': 1500, 'SVLEN': 1000},
                (500, 500): {'#CHROM': 'chr2', 'END2': 250, 'SVLEN': 1000},
                (30, 30): {'END2': 3030},
                (550, 550): {'end_chrom': 'chr3', 'END2': 15050},
                (520, 520): {'END2': 250},
                (1400, 1400): {'END2': 4600},
            },
            SVLEN=-1,
        )

    def test_translocations(self):
        self._test_expected_consequences(
            {
                **{
                    (position, position + length): [(LOF,)]
                    for position in [150, 250, 350, 600, 100]
                    for length in [0, 1]
                },
                (99, 100): [(LOF,)],
                (1000, 1001): [(LOF,)],
                (5000, 5000): [(LOF, 'EMMA2'), (LOF, 'EMMA2', '202')],
                (6000, 6000): [(LOF, 'EMMA2'), (LOF, 'EMMA2', '202')],
                (700, 700): [(LOF,), (LOF, 'TBX30')],
                (12000, 12000): [(NEAREST_TSS, 'TBX30'), (NEAREST_TSS, 'EMMA2', '202')],
            },
            'CTX',
            input_overrides={
                (5000, 5000): {'#CHROM': 'chr2', 'end_chrom': 'chr1', 'END2': 2099},
                (6000, 6000): {'#CHROM': 'chr2', 'end_chrom': 'chr1', 'END2': 3000},
                (700, 700): {'end_chrom': 'chr3', 'END2': 15050},
                (12000, 12000): {'#CHROM': 'chr3', 'end_chrom': 'chr1', 'END2': None},
            },
            end_chrom='chr2',
            END2=1,
            SVLEN=-1,
        )

    def test_complex_variants(self):
        self._test_expected_consequences(
            {
                (90, 1010): [(LOF,)],
                (250, 650): [(LOF,)],
                (1100, 1100): [(NEAREST_TSS,)],
                (450, 3100): [(LOF, 'EMMA2'), (INTRONIC, 'EMMA2', '202')],
                (1101, 1102): [(NEAREST_TSS,)],
                (1400, 1900): [(NEAREST_TSS, 'EMMA2')],
                (50, 2050): [(COPY_GAIN,)],
                (2900, 3600): [(LOF, 'EMMA2', '202'), (PROMOTER, 'EMMA2')],
                (14900, 15500): [(INV_SPAN, 'TBX30')],
                (1100, 3200): [(INV_SPAN, 'EMMA2'), (INTRONIC, 'EMMA2', '202')],
                (1200, 1200): [(NEAREST_TSS,)],
                (1100, 3100): [(LOF, 'EMMA2'), (INTRONIC, 'EMMA2', '202')],
                (2900, 4500): [(LOF, 'EMMA2', '202'), (PROMOTER, 'EMMA2')],
                (1050, 1900): [(NEAREST_TSS,)],
                (1060, 1900): [(NEAREST_TSS,)],
                (1020, 1900): [(NEAREST_TSS,)],
                (1030, 2000): [(NEAREST_TSS,)],
                (10, 11): [
                    (COPY_GAIN, 'EMMA2'),
                    (COPY_GAIN, 'EMMA2', '202'),
                    (PROMOTER,),
                ],
                (20, 3500): [
                    (INV_SPAN,),
                    (COPY_GAIN, 'EMMA2'),
                    (COPY_GAIN, 'EMMA2', '202'),
                ],
            },
            'CPX',
            input_overrides={
                (90, 1010): {
                    'sv_type_detail': 'INVdup',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 90, 'end': 1010, 'type': 'INV'},
                        {'chrom': '1', 'start': 890, 'end': 1010, 'type': 'DUP'},
                    ],
                },
                (250, 650): {
                    'sv_type_detail': 'delINVdup',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 250, 'end': 450, 'type': 'DEL'},
                        {'chrom': '1', 'start': 450, 'end': 650, 'type': 'INV'},
                        {'chrom': '1', 'start': 610, 'end': 650, 'type': 'DUP'},
                    ],
                },
                (1100, 1100): {
                    'sv_type_detail': 'dDUP',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 450, 'end': 1000, 'type': 'DUP'},
                    ],
                    'SVLEN': 550,
                },
                (450, 3100): {
                    'sv_type_detail': 'dupINV',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 450, 'end': 2200, 'type': 'DUP'},
                        {'chrom': '1', 'start': 450, 'end': 3100, 'type': 'INV'},
                    ],
                },
                (1101, 1102): {
                    'sv_type_detail': 'dDUP_iDEL',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 10, 'end': 60, 'type': 'DUP'},
                        {'chrom': '1', 'start': 10, 'end': 60, 'type': 'INV'},
                        {'chrom': '1', 'start': 1100, 'end': 1700, 'type': 'DEL'},
                    ],
                    'SVLEN': 700,
                },
                (1400, 1900): {
                    'sv_type_detail': 'delINV',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 1400, 'end': 1500, 'type': 'DEL'},
                        {'chrom': '1', 'start': 1500, 'end': 1900, 'type': 'INV'},
                    ],
                },
                (50, 2050): {
                    'sv_type_detail': 'dupINVdel',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 50, 'end': 1050, 'type': 'DUP'},
                        {'chrom': '1', 'start': 50, 'end': 1900, 'type': 'INV'},
                        {'chrom': '1', 'start': 1900, 'end': 2050, 'type': 'DEL'},
                    ],
                },
                (2900, 3600): {
                    'sv_type_detail': 'dupINVdel',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 2900, 'end': 3100, 'type': 'DUP'},
                        {'chrom': '1', 'start': 2900, 'end': 3500, 'type': 'INV'},
                        {'chrom': '1', 'start': 3500, 'end': 3600, 'type': 'DEL'},
                    ],
                },
                (14900, 15500): {
                    '#CHROM': 'chr3',
                    'sv_type_detail': 'INVdel',
                    'CPX_INTERVALS': [
                        {'chrom': '3', 'start': 14900, 'end': 15200, 'type': 'INV'},
                        {'chrom': '3', 'start': 15200, 'end': 15500, 'type': 'DEL'},
                    ],
                    'end_chrom': 'chr3',
                },
                (1100, 3200): {
                    'sv_type_detail': 'delINVdel',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 1100, 'end': 2000, 'type': 'DEL'},
                        {'chrom': '1', 'start': 2000, 'end': 3100, 'type': 'INV'},
                        {'chrom': '1', 'start': 3100, 'end': 3200, 'type': 'DEL'},
                    ],
                },
                (1200, 1200): {
                    'sv_type_detail': 'dDUP',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 450, 'end': 1000, 'type': 'INV'},
                        {'chrom': '1', 'start': 450, 'end': 1000, 'type': 'DUP'},
                    ],
                    'SVLEN': 550,
                },
                (1100, 3100): {
                    'sv_type_detail': 'delINVdup',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 1100, 'end': 1200, 'type': 'DEL'},
                        {'chrom': '1', 'start': 1200, 'end': 3100, 'type': 'INV'},
                        {'chrom': '1', 'start': 2900, 'end': 3100, 'type': 'DUP'},
                    ],
                },
                (2900, 4500): {
                    'sv_type_detail': 'dupINVdup',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 2900, 'end': 3100, 'type': 'DUP'},
                        {'chrom': '1', 'start': 2900, 'end': 4500, 'type': 'INV'},
                        {'chrom': '1', 'start': 4400, 'end': 4500, 'type': 'DUP'},
                    ],
                },
                (10, 11): {
                    'sv_type_detail': 'dDUP',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 2000, 'end': 3500, 'type': 'DUP'},
                    ],
                    'SVLEN': 1500,
                },
                (20, 3500): {
                    'sv_type_detail': 'dupINVdup',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 20, 'end': 70, 'type': 'DUP'},
                        {'chrom': '1', 'start': 20, 'end': 3500, 'type': 'INV'},
                        {'chrom': '1', 'start': 2000, 'end': 3500, 'type': 'DUP'},
                    ],
                },
                (1050, 1900): {
                    'sv_type_detail': 'INVdel',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 1050, 'end': 1300, 'type': 'INV'},
                        {'chrom': '1', 'start': 1300, 'end': 1900, 'type': 'DEL'},
                    ],
                },
                (1060, 1900): {
                    'sv_type_detail': 'delINVdel',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 1060, 'end': 1100, 'type': 'DEL'},
                        {'chrom': '1', 'start': 1100, 'end': 1400, 'type': 'INV'},
                        {'chrom': '1', 'start': 1400, 'end': 1900, 'type': 'DEL'},
                    ],
                },
                (1020, 1900): {
                    'sv_type_detail': 'dupINVdel',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 1020, 'end': 1070, 'type': 'DUP'},
                        {'chrom': '1', 'start': 1020, 'end': 1400, 'type': 'INV'},
                        {'chrom': '1', 'start': 1400, 'end': 1900, 'type': 'DEL'},
                    ],
                },
                (1030, 2000): {
                    'sv_type_detail': 'delINVdup',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 1030, 'end': 1300, 'type': 'DEL'},
                        {'chrom': '1', 'start': 1300, 'end': 2000, 'type': 'INV'},
                        {'chrom': '1', 'start': 1900, 'end': 2000, 'type': 'DUP'},
                    ],
                },
            },
        )
        self._test_expected_consequences(
            {(1101, 1102): [(NEAREST_TSS,)]},
            'CPX',
            input_overrides={
                (1101, 1102): {
                    'sv_type_detail': 'INS_iDEL',
                    'CPX_INTERVALS': [
                        {'chrom': '1', 'start': 10, 'end': 60, 'type': 'INV'},
                        {'chrom': '1', 'start': 1100, 'end': 1700, 'type': 'DEL'},
                        {'chrom': '1', 'start': 10, 'end': 60, 'type': 'INS'},
                    ],
                    'SVLEN': 700,
                },
            },
        )
