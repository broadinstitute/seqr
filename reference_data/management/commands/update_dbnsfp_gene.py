from collections import defaultdict
import logging
import os
from tqdm import tqdm
from django.core.management.base import BaseCommand, CommandError

from reference_data.management.commands.utils.download_utils import download_file
from reference_data.models import dbNSFPGene, GeneInfo

logger = logging.getLogger(__name__)

DBNSFP_GENE_URL = "http://storage.googleapis.com/seqr-reference-data/dbnsfp/dbNSFP3.5_gene"

class Command(BaseCommand):
    help ="Loads the dbNSFP_gene table (see https://sites.google.com/site/jpopgen/dbNSFP)"

    def add_arguments(self, parser):
        parser.add_argument('dbnsfp_gene_table', help="The dbNSFP gene table. Currently it's only available as part "
            "of the much larger dbNSFPv3.5a.zip download from https://sites.google.com/site/jpopgen/dbNSFP")

    def handle(self, *args, **options):
        update_dbnsfp_gene(options['dbnsfp_gene_table'])


def update_dbnsfp_gene(dbnsfp_gene_table_path=None):
    """
    Args:
        dbnsfp_gene_table_path (str): optional local dbNSFP_geen file path. If not specified, or the path doesn't exist,
            the table will be downloaded.
    """

    if GeneInfo.objects.count() == 0:
        raise CommandError("GeneInfo table is empty. Run './manage.py update_gencode' before running this command.")

    if not dbnsfp_gene_table_path or not os.path.isfile(dbnsfp_gene_table_path):
        dbnsfp_gene_table_path = download_file(DBNSFP_GENE_URL)

    gene_id_to_gene_info = {g.gene_id: g for g in GeneInfo.objects.all().only('gene_id')}

    counters = defaultdict(int)
    records = []
    with open(dbnsfp_gene_table_path) as f:
        header = next(f).rstrip('\r\n').split('\t')
        logger.info("Header: ")
        logger.info(", ".join(header))
        logger.info("Parsing gene records from {}".format(dbnsfp_gene_table_path))

        dbNSFPGene.objects.all().delete()

        for line in tqdm(f, unit=' genes'):
            counters['total'] += 1
            fields = line.rstrip('\r\n').split('\t')

            fields = dict(zip(header, fields))

            gene_id = fields['Ensembl_gene']
            if gene_id == ".":
                continue

            gene = gene_id_to_gene_info.get(gene_id)
            if not gene:
                logger.warn(("dbNSFP gene id '{}' not found in GeneInfo table. "
                    "Running ./manage.py update_gencode to update the gencode version might fix this. "
                    "Full dbNSFP record: {}").format(gene_id, fields))
                continue

            # based on dbNSFP_gene schema README: https://drive.google.com/file/d/0B60wROKy6OqcNGJ2STJlMTJONk0/view
            records.append({
                "gene": gene,
                "uniprot_acc": fields['Uniprot_acc'],
                "uniprot_id": fields['Uniprot_id'],
                "entrez_gene_id": fields['Entrez_gene_id'],
                "ccds_id": fields['CCDS_id'],
                "refseq_id": fields["Refseq_id"],
                "ucsc_id": fields['ucsc_id'],
                "pathway_uniprot": fields['Pathway(Uniprot)'],
                "pathway_biocarta_short": fields['Pathway(BioCarta)_short'],  #  Short name of the Pathway(s) the gene belongs to (from BioCarta)
                "pathway_biocarta_full": fields['Pathway(BioCarta)_full'],    #  Full name(s) of the Pathway(s) the gene belongs to (from BioCarta)
                "pathway_consensus_path_db": fields['Pathway(ConsensusPathDB)'],   # Pathway(s) the gene belongs to (from ConsensusPathDB)
                "pathway_kegg_id": fields['Pathway(KEGG)_id'],           # ID(s) of the Pathway(s) the gene belongs to (from KEGG)
                "pathway_kegg_full": fields['Pathway(KEGG)_full'],         # Full name(s) of the Pathway(s) the gene belongs to (from KEGG)
                "function_desc": fields['Function_description'].replace("FUNCTION: ", ""),  # Function description of the gene (from Uniprot)
                "disease_desc": fields['Disease_description'].replace("FUNCTION: ", ""),    # Disease(s) the gene caused or associated with (from Uniprot)
                "trait_association_gwas": fields['Trait_association(GWAS)'], # Trait(s) the gene associated with (from GWAS catalog)
                "go_biological_process": fields['GO_biological_process'],   # GO terms for biological process
                "go_cellular_component": fields['GO_cellular_component'],   # GO terms for cellular component
                "go_molecular_function": fields['GO_molecular_function'],   # GO terms for molecular function
                "tissue_specificity": fields['Tissue_specificity(Uniprot)'],   # Tissue specificity description from Uniprot
                "expression_egenetics": fields['Expression(egenetics)'],   # Tissues/organs the gene expressed in (egenetics data from BioMart)
                "expression_gnf_atlas": fields['Expression(GNF/Atlas)'],   # Tissues/organs the gene expressed in (GNF/Atlas data from BioMart)
                "rvis_exac": fields['RVIS_ExAC'],
                "ghis": fields['GHIS'],
                "essential_gene": fields['Essential_gene'],   # Essential ("E") or Non-essential phenotype-changing ("N") based on Mouse Genome Informatics database. from doi:10.1371/journal.pgen.1003484
                "mgi_mouse_gene": fields['MGI_mouse_gene'],   # Homolog mouse gene name from MGI
                "mgi_mouse_phenotype": fields['MGI_mouse_phenotype'],   # Phenotype description for the homolog mouse gene from MGI
                "zebrafish_gene": fields['ZFIN_zebrafish_gene'],   # Homolog zebrafish gene name from ZFIN
                "zebrafish_structure": fields['ZFIN_zebrafish_structure'],   # Affected structure of the homolog zebrafish gene from ZFIN
                "zebrafish_phenotype_quality": fields['ZFIN_zebrafish_phenotype_quality'],   # Phenotype description for the homolog zebrafish gene from ZFIN
                "zebrafish_phenotype_tag": fields['ZFIN_zebrafish_phenotype_tag'],   # Phenotype tag for the homolog zebrafish gene from ZFIN
            })

    print("Parsed {} records. Inserting them into dbNSFPGene".format(len(records)))

    dbNSFPGene.objects.bulk_create((dbNSFPGene(**record) for record in tqdm(records, unit=' genes')), batch_size=1000)

    logger.info("Done loading {} records into dbNSFPGene".format(dbNSFPGene.objects.count()))
