from django.conf import settings

# dict of ensembl -> desc
GENE_DESCRIPTIONS = { a: b for a, b in [l.split('\t') for l in [line.strip() for line in open(settings.REFSEQ_DESCRIPTION_FILE)]] }