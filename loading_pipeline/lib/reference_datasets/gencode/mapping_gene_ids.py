import gzip
import logging

import requests

logger = logging.getLogger(__name__)

# Mirror of 'https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_{gencode_release}/gencode.v{gencode_release}.metadata.RefSeq.gz'
GENCODE_ENSEMBL_TO_REFSEQ_URL = 'https://storage.googleapis.com/seqr-reference-data/gencode/gencode.v{gencode_release}.metadata.RefSeq.gz'

EXPECTED_ENSEMBLE_TO_REFSEQ_FIELDS = 3


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
