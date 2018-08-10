import logging
import os
from django.core.management.base import BaseCommand

from reference_data.management.commands.update_human_phenotype_ontology import update_hpo
from reference_data.management.commands.update_dbnsfp_gene import update_dbnsfp_gene
from reference_data.management.commands.update_gencode import update_gencode
from reference_data.management.commands.update_gene_constraint import update_gene_constraint
from reference_data.management.commands.update_omim import update_omim

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Loads all reference data"

    def add_arguments(self, parser):
        parser.add_argument('--omim-key', help="OMIM key provided with registration at http://data.omim.org/downloads", required=True)
        parser.add_argument('--skip-gencode', help="Don't reload gencode", action="store_true")
        parser.add_argument('--skip-dbnsfp-gene', help="Don't reload the dbNSFP_gene table", action="store_true")
        parser.add_argument('--skip-gene-constraint', help="Don't reload gene constraint", action="store_true")
        parser.add_argument('--skip-omim', help="Don't reload gene constraint", action="store_true")
        parser.add_argument('--skip-hpo', help="Don't reload human phenotype ontology", action="store_true")


    def handle(self, *args, **options):
        if not options["skip_gencode"]:
            # download v19 and then v28 because there are 1000+ gene and transcript ids in v19 that
            # gencode retired by the time of v28, but that are used in the gene constraint table and other datasets
            update_gencode(19, reset=True)
            update_gencode(28)

        if not options["skip_dbnsfp_gene"]:
            update_dbnsfp_gene()
        if not options["skip_gene_constraint"]:
            update_gene_constraint()
        if not options["skip_omim"]:
            update_omim(omim_key=options["omim_key"])
        if not options["skip_hpo"]:
            update_hpo()
