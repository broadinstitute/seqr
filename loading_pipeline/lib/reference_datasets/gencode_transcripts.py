import luigi
import pandas as pd

GENCODE_FILE_HEADER = [
    'contig',
    'source',
    'feature_type',
    'start',
    'end',
    'score',
    'strand',
    'phase',
    'info',
]


def get_df(input_target: luigi.Target) -> pd.DataFrame:
    input_target.format = luigi.format.UTF8 >> luigi.format.Gzip
    with input_target.open('r') as f:
        df = pd.read_csv(
            f,
            sep='\t',
            comment='#',
            header=None,
            names=GENCODE_FILE_HEADER,
        )

    df = df[df['feature_type'].isin(['transcript', 'CDS', 'UTR'])].assign(
        transcriptId=lambda df: df['info'].str.extract(
            r'transcript_id "([^".]*)',
            expand=False,
        ),
        geneId=lambda df: df['info'].str.extract(
            r'gene_id "([^".]*)',
            expand=False,
        ),
        gene_type=lambda df: df['info'].str.extract(
            r'gene_type "([^"]*)',
            expand=False,
        ),
    )

    return df[df['gene_type'] == 'protein_coding'][
        ['contig', 'start', 'end', 'strand', 'feature_type', 'transcriptId', 'geneId']
    ]
