import logging

from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler, update_records
from reference_data.models import dbNSFPGene

logger = logging.getLogger(__name__)

# based on dbNSFP_gene schema README: https://drive.google.com/file/d/0B60wROKy6OqcNGJ2STJlMTJONk0/view
FIELD_MAP = {
    'Ensembl_gene': "gene_id",
    'Pathway(Uniprot)': "pathway_uniprot",
    'Pathway(BioCarta)_short': "pathway_biocarta_short", # Short name of the Pathway(s) the gene belongs to (from BioCarta)
    'Pathway(BioCarta)_full': "pathway_biocarta_full", # Full name(s) of the Pathway(s) the gene belongs to (from BioCarta)
    'Pathway(ConsensusPathDB)': "pathway_consensus_path_db", # Pathway(s) the gene belongs to (from ConsensusPathDB)
    'Pathway(KEGG)_id': "pathway_kegg_id",  # ID(s) of the Pathway(s) the gene belongs to (from KEGG)
    'Pathway(KEGG)_full': "pathway_kegg_full", # Full name(s) of the Pathway(s) the gene belongs to (from KEGG)
    'Function_description': "function_desc", # Function description of the gene (from Uniprot)
    'Disease_description': "disease_desc", # Disease(s) the gene caused or associated with (from Uniprot)
    'Trait_association(GWAS)': "trait_association_gwas", # Trait(s) the gene associated with (from GWAS catalog)
    'Tissue_specificity(Uniprot)': "tissue_specificity",  # Tissue specificity description from Uniprot
    'Expression(egenetics)': "expression_egenetics", # Tissues/organs the gene expressed in (egenetics data from BioMart)
    'Expression(GNF/Atlas)': "expression_gnf_atlas", # Tissues/organs the gene expressed in (GNF/Atlas data from BioMart)
    'ZFIN_zebrafish_gene': "zebrafish_gene",  # Homolog zebrafish gene name from ZFIN
    'ZFIN_zebrafish_structure': "zebrafish_structure", # Affected structure of the homolog zebrafish gene from ZFIN
    'ZFIN_zebrafish_phenotype_quality': "zebrafish_phenotype_quality", # Phenotype description for the homolog zebrafish gene from ZFIN
    'ZFIN_zebrafish_phenotype_tag': "zebrafish_phenotype_tag", # Phenotype tag for the homolog zebrafish gene from ZFIN
}

EXCLUDE_FIELDS = (
    'Gene damage prediction', 'P(', 'RVIS_percentile_ExAC', 'Known_rec_info', 'GDI', 'LoF', 'ExAC', 'Interactions',
    'SORVA_LOF', 'Gene', 'Essential_gene', 'chr', 'MIM', 'RVIS_percentile_EVS', 'RVIS_EVS'
)


class DbNSFPReferenceDataHandler(ReferenceDataHandler):

    model_cls = dbNSFPGene
    url = "http://storage.googleapis.com/seqr-reference-data/dbnsfp/dbNSFP3.5_gene"

    @staticmethod
    def parse_record(record):
        parsed_record = {FIELD_MAP.get(k, k.lower()): (v if v != '.' else '')
                         for k, v in record.items() if not k.startswith(EXCLUDE_FIELDS)}
        parsed_record["function_desc"] = parsed_record["function_desc"].replace("FUNCTION: ", "")
        yield parsed_record


class Command(GeneCommand):
    reference_data_handler = DbNSFPReferenceDataHandler


def update_dbnsfp_gene(**kwargs):
    """
    Args:
        file_path (str): optional local file path. If not specified, or the path doesn't exist, the table will be downloaded.
    """
    update_records(DbNSFPReferenceDataHandler, **kwargs)
