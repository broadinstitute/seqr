import os
from collections import defaultdict
from tqdm import tqdm
from django.core.management.base import BaseCommand

from reference_data.models import dbNSFPGene

class Command(BaseCommand):
    """This command updates the dbNSFP gene table. See https://sites.google.com/site/jpopgen/dbNSFP
    for more details.
    """

    def add_arguments(self, parser):
        parser.add_argument('dbnsfp_gene_table', help="The dbNSFP gene table")

    def handle(self, *args, **options):
        dbnsfp_gene_table_path = options['dbnsfp_gene_table']
        if not os.path.isfile(dbnsfp_gene_table_path):
            raise ValueError("File not found: %s" % dbnsfp_gene_table_path)

        counters = defaultdict(int)
        with open(dbnsfp_gene_table_path) as f:
            header = next(f).rstrip('\n').split('\t')
            #pprint(list(enumerate(header)))
            for line in tqdm(f, unit=' genes'):
                counters['total'] += 1
                fields = line.rstrip('\n').split('\t')

                record = dict(zip(header, fields))

                # based on dbNSFP_gene schema README: https://drive.google.com/file/d/0B60wROKy6OqcNGJ2STJlMTJONk0/view

                dbNSFPGene.objects.create(
                    gene_id=record['Ensembl_gene'],
                    refseq_id=record['Refseq_id'],
                    pathway_uniprot=record['Pathway(Uniprot)'],
                    pathway_biocarta_short=record['Pathway(BioCarta)_short'],  #  Short name of the Pathway(s) the gene belongs to (from BioCarta)
                    pathway_biocarta_full=record['Pathway(BioCarta)_full'],    #  Full name(s) of the Pathway(s) the gene belongs to (from BioCarta)
                    pathway_consensus_path_db=record['Pathway(ConsensusPathDB)'],   # Pathway(s) the gene belongs to (from ConsensusPathDB)
                    pathway_kegg_id=record['Pathway(KEGG)_id'],           # ID(s) of the Pathway(s) the gene belongs to (from KEGG)
                    pathway_kegg_full=record['Pathway(KEGG)_full'],         # Full name(s) of the Pathway(s) the gene belongs to (from KEGG)
                    function_desc=record['Function_description'].replace("FUNCTION: ", ""),  # Function description of the gene (from Uniprot)
                    disease_desc=record['Disease_description'].replace("FUNCTION: ", ""),    # Disease(s) the gene caused or associated with (from Uniprot)
                    trait_association_gwas=record['Trait_association(GWAS)'], # Trait(s) the gene associated with (from GWAS catalog)
                    go_biological_process=record['GO_biological_process'],   # GO terms for biological process
                    go_cellular_component=record['GO_cellular_component'],   # GO terms for cellular component
                    go_molecular_function=record['GO_molecular_function'],   # GO terms for molecular function
                    tissue_specificity=record['Tissue_specificity(Uniprot)'],   # Tissue specificity description from Uniprot
                    expression_egenetics=record['Expression(egenetics)'],   # Tissues/organs the gene expressed in (egenetics data from BioMart)
                    expression_gnf_atlas=record['Expression(GNF/Atlas)'],   # Tissues/organs the gene expressed in (GNF/Atlas data from BioMart)
                    essential_gene=record['Essential_gene'],   # Essential ("E") or Non-essential phenotype-changing ("N") based on Mouse Genome Informatics database. from doi:10.1371/journal.pgen.1003484
                    mgi_mouse_gene=record['MGI_mouse_gene'],   # Homolog mouse gene name from MGI
                    mgi_mouse_phenotype=record['MGI_mouse_phenotype'],   # Phenotype description for the homolog mouse gene from MGI
                    zebrafish_gene=record['ZFIN_zebrafish_gene'],   # Homolog zebrafish gene name from ZFIN
                    zebrafish_structure=record['ZFIN_zebrafish_structure'],   # Affected structure of the homolog zebrafish gene from ZFIN
                    zebrafish_phenotype_quality=record['ZFIN_zebrafish_phenotype_quality'],   # Phenotype description for the homolog zebrafish gene from ZFIN
                    zebrafish_phenotype_tag=record['ZFIN_zebrafish_phenotype_tag'],   # Phenotype tag for the homolog zebrafish gene from ZFIN
                )

            print("Done inserting %s records." % (counters['total'],))
