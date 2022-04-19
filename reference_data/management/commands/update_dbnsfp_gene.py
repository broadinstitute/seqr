from reference_data.management.commands.utils.update_utils import GeneCommand, ReferenceDataHandler
from reference_data.models import dbNSFPGene

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
    'Expression(egenetics)': "expression_egenetics", # Tissues/organs the gene expressed in (egenetics data from BioMart)
    'Expression(GNF/Atlas)': "expression_gnf_atlas", # Tissues/organs the gene expressed in (GNF/Atlas data from BioMart)
    'ZFIN_zebrafish_gene': "zebrafish_gene",  # Homolog zebrafish gene name from ZFIN
    'ZFIN_zebrafish_structure': "zebrafish_structure", # Affected structure of the homolog zebrafish gene from ZFIN
    'ZFIN_zebrafish_phenotype_quality': "zebrafish_phenotype_quality", # Phenotype description for the homolog zebrafish gene from ZFIN
    'ZFIN_zebrafish_phenotype_tag': "zebrafish_phenotype_tag", # Phenotype tag for the homolog zebrafish gene from ZFIN
}

EXCLUDE_FIELDS = (
    'Gene', 'P(', 'RVIS_percentile_ExAC', 'Known_rec_info', 'GDI', 'LoF', 'ExAC', 'Interactions', 'Orphanet', 'gnomAD',
    'SORVA_LOF', 'Essential_gene', 'chr', 'MIM', 'OMIM', 'RVIS_percentile_EVS', 'RVIS_EVS', 'HIPred',
)

class DbNSFPReferenceDataHandler(ReferenceDataHandler):

    model_cls = dbNSFPGene
    url = "http://storage.googleapis.com/seqr-reference-data/dbnsfp/dbNSFP4.0_gene"

    @staticmethod
    def parse_record(record):
        parsed_record = {FIELD_MAP.get(k, k.split('(')[0].lower()): (v if v != '.' else '')
                         for k, v in record.items() if not k.startswith(EXCLUDE_FIELDS)}
        parsed_record["function_desc"] = parsed_record["function_desc"].replace("FUNCTION: ", "")
        parsed_record['gene_id'] = parsed_record['gene_id'].split(';')[0]

        gene_names = [record['Gene_name']]
        for gene_name_key in ['Gene_old_names', 'Gene_other_names']:
            names = record[gene_name_key] if record[gene_name_key] != '.' else ''
            gene_names += names.split(';')
        parsed_record['gene_names'] = ';'.join([name for name in gene_names if name])

        if parsed_record['gene_id']:
            yield parsed_record
        else:
            yield None


class Command(GeneCommand):
    reference_data_handler = DbNSFPReferenceDataHandler
