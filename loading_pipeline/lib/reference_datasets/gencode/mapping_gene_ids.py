import gzip
import logging

import requests

logger = logging.getLogger(__name__)

# Mirror of 'http://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_{gencode_release}/gencode.v{gencode_release}.annotation.gtf.gz'
GENCODE_GTF_URL = 'https://storage.googleapis.com/seqr-reference-data/gencode/gencode.v{gencode_release}.annotation.gtf.gz'
# Mirror of 'https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_{gencode_release}/gencode.v{gencode_release}.metadata.RefSeq.gz'
GENCODE_ENSEMBL_TO_REFSEQ_URL = 'https://storage.googleapis.com/seqr-reference-data/gencode/gencode.v{gencode_release}.metadata.RefSeq.gz'

# expected GTF file header
GENCODE_FILE_HEADER = [
    'chrom',
    'source',
    'feature_type',
    'start',
    'end',
    'score',
    'strand',
    'phase',
    'info',
]
EXPECTED_ENSEMBLE_TO_REFSEQ_FIELDS = 3


def load_gencode_gene_symbol_to_gene_id(gencode_release: int) -> dict[str, str]:
    url = GENCODE_GTF_URL.format(gencode_release=gencode_release)
    response = requests.get(url, stream=True, timeout=10)
    gene_symbol_to_gene_id = {}
    for line in gzip.GzipFile(fileobj=response.raw):
        line = line.decode('ascii')  # noqa: PLW2901
        if not line or line.startswith('#'):
            continue
        fields = line.strip().split('\t')
        if len(fields) != len(GENCODE_FILE_HEADER):
            msg = f'Unexpected number of fields: {fields}'
            raise ValueError(
                msg,
            )
        record = dict(zip(GENCODE_FILE_HEADER, fields, strict=False))
        if record['feature_type'] != 'gene':
            continue
        # parse info field
        info_fields = [x.strip().split() for x in record['info'].split(';') if x != '']
        info_fields = {k: v.strip('"') for k, v in info_fields}
        gene_symbol_to_gene_id[info_fields['gene_name']] = info_fields['gene_id'].split(
            '.',
        )[0]
    return gene_symbol_to_gene_id


def load_gencode_ensembl_to_refseq_id(gencode_release: int):
    url = GENCODE_ENSEMBL_TO_REFSEQ_URL.format(gencode_release=gencode_release)
    response = requests.get(url, stream=True, timeout=10)
    ensembl_to_refseq_ids = {}
    for line in gzip.GzipFile(fileobj=response.raw):
        fields = line.decode('ascii').strip().split('\t')
        if len(fields) > EXPECTED_ENSEMBLE_TO_REFSEQ_FIELDS:
            msg = 'Unexpected number of fields on line in ensemble_to_refseq mapping'
            raise ValueError(msg)
        ensembl_to_refseq_ids[fields[0].split('.')[0]] = fields[1]
    return ensembl_to_refseq_ids
