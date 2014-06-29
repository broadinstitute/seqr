import argparse
import sys

from django.conf import settings

from xbrowse_server.base.models import DiseaseGeneList
from xbrowse import utils


if __name__ == "__main__":

    reference = settings.REFERENCE

    parser = argparse.ArgumentParser(description='Load list of genes (symbols or ensembl ID) ')
    parser.add_argument('gene_symbol_file')
    parser.add_argument('-p', '--phenotype')
    parser.add_argument('-d', '--description')

    args = parser.parse_args()

    gene_ids = []
    for line in open(args.gene_symbol_file).readlines():
        gene_str = line.strip()
        ensembl_id = utils.get_gene_id_from_str(gene_str, reference)
        if not ensembl_id:
            sys.stderr.write("Error: can't find ID for %s" % gene_str)
        gene_ids.append(ensembl_id)

    d = DiseaseGeneList(slug=args.phenotype, title=args.description)
    d.save()
    d.set_genes(gene_ids)


