from django.db import models

GENOME_VERSION_GRCh37 = "37"
GENOME_VERSION_GRCh38 = "38"

GENOME_VERSION_CHOICES = [
    (GENOME_VERSION_GRCh37, "GRCh37"),
    (GENOME_VERSION_GRCh38, "GRCh38")
]


# HPO categories are direct children of HP:0000118 "Phenotypic abnormality".  See http://compbio.charite.de/hpoweb/showterm?id=HP:0000118
HPO_CATEGORY_NAMES = {
    'HP:0000478': 'Eye',
    'HP:0025142': 'Constitutional Symptom',
    'HP:0002664': 'Neoplasm',
    'HP:0000818': 'Endocrine System',
    'HP:0000152': 'Head or Neck',
    'HP:0002715': 'Immune System',
    'HP:0001507': 'Growth Abnormality',
    'HP:0045027': 'Thoracic Cavity',
    'HP:0001871': 'Blood',
    'HP:0002086': 'Respiratory',
    'HP:0000598': 'Ear',
    'HP:0001939': 'Metabolism/Homeostasis',
    'HP:0003549': 'Connective Tissue',
    'HP:0001608': 'Voice',
    'HP:0000707': 'Nervous System',
    'HP:0000769': 'Breast',
    'HP:0001197': 'Prenatal development or birth',
    'HP:0040064': 'Limbs',
    'HP:0025031': 'Digestive System',
    'HP:0003011': 'Musculature',
    'HP:0001626': 'Cardiovascular System',
    'HP:0000924': 'Skeletal System',
    'HP:0500014': 'Test Result',
    'HP:0001574': 'Integument',
    'HP:0000119': 'Genitourinary System',
    'HP:0025354': 'Cellular Phenotype',
}

class HumanPhenotypeOntology(models.Model):
    """Human Phenotype Ontology table contains one record per phenotype term parsed from the hp.obo
    file at http://human-phenotype-ontology.github.io/downloads.html
    """
    hpo_id = models.CharField(max_length=20, null=False, blank=False, unique=True, db_index=True)
    parent_id = models.CharField(max_length=20, null=True, blank=True)
    # hpo id of top-level phenotype category (eg. 'cardiovascular')
    category_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)

    # whether this hpo id is itself one of the top-level categories (eg. 'cardiovascular')
    is_category = models.BooleanField(default=False, db_index=True)

    name = models.TextField(null=False, blank=False)

    definition = models.TextField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)


class GeneInfo(models.Model):
    """Human gene models from https://www.gencodegenes.org/releases/
    http://www.gencodegenes.org/gencodeformat.html
    """

    # gencode fields
    gene_id = models.CharField(max_length=20, db_index=True, unique=True)         # without the version suffix (eg. "ENSG0000012345")

    gencode_release = models.IntegerField(null=True, blank=True)  # eg. 25 - the (newest) gencode release from which this gene was loaded

    chrom_grch37 = models.CharField(max_length=2, null=True, blank=True)
    start_grch37 = models.IntegerField(null=True, blank=True)
    end_grch37 = models.IntegerField(null=True, blank=True)
    strand_grch37 = models.CharField(max_length=1, null=True, blank=True)
    coding_region_size_grch37 = models.IntegerField(default=0)  # number of protein-coding base-pairs in this gene (= 0 for non-coding genes)

    chrom_grch38 = models.CharField(max_length=2, null=True, blank=True)
    start_grch38 = models.IntegerField(null=True, blank=True)
    end_grch38 = models.IntegerField(null=True, blank=True)
    strand_grch38 = models.CharField(max_length=1, null=True, blank=True)
    coding_region_size_grch38 = models.IntegerField(default=0)  # number of protein-coding base-pairs in this gene (= 0 for non-coding genes)

    gencode_gene_type = models.TextField(null=True, blank=True)
    gencode_gene_name = models.TextField(null=True, blank=True)



    # OMIM fields
    mim_number = models.IntegerField(null=True, blank=True)  # Example: 601365
    omim_version = models.DateTimeField(null=True, blank=True)  # date omim was downloaded
    omim_gene_description = models.TextField(null=True, blank=True)  # Example: "Dishevelled 1 (homologous to Drosophila dsh)"
    omim_comments = models.TextField(null=True, blank=True)  # Example: "associated with rs10492972"
    omim_phenotypes = models.TextField(null=True, blank=True)  # Example: '{ "phenotype_inheritance": "Autosomal dominant", "phenotype_mim_number": "616331", "phenotype_description": "Robinow syndrome, autosomal dominant 2", "phenotype_map_method": 2}'

    # dbNSFPv3.5a_gene fields
    function_desc = models.TextField(null=True, blank=True)
    disease_desc = models.TextField(null=True, blank=True)
    uniprot_acc = models.TextField(null=True, blank=True)
    uniprot_id = models.TextField(null=True, blank=True)
    entrez_gene_id = models.TextField(null=True, blank=True)
    ccds_id = models.TextField(null=True, blank=True)
    ucsc_id = models.TextField(null=True, blank=True)
    pathway_uniprot = models.TextField(null=True, blank=True)
    pathway_biocarta_short = models.TextField(null=True, blank=True)  #  Short name of the Pathway(s) the gene belongs to (from BioCarta)
    pathway_biocarta_full = models.TextField(null=True, blank=True)    #  Full name(s) of the Pathway(s) the gene belongs to (from BioCarta)
    pathway_consensus_path_db = models.TextField(null=True, blank=True)   # Pathway(s) the gene belongs to (from ConsensusPathDB)
    pathway_kegg_id = models.TextField(null=True, blank=True)           # ID(s) of the Pathway(s) the gene belongs to (from KEGG)
    pathway_kegg_full = models.TextField(null=True, blank=True)         # Full name(s) of the Pathway(s) the gene belongs to (from KEGG)
    function_desc = models.TextField(null=True, blank=True)  # Function description of the gene (from Uniprot)
    disease_desc = models.TextField(null=True, blank=True)    # Disease(s) the gene caused or associated with (from Uniprot)
    trait_association_gwas = models.TextField(null=True, blank=True) # Trait(s) the gene associated with (from GWAS catalog)
    go_biological_process = models.TextField(null=True, blank=True)   # GO terms for biological process
    go_cellular_component = models.TextField(null=True, blank=True)   # GO terms for cellular component
    go_molecular_function = models.TextField(null=True, blank=True)   # GO terms for molecular function
    tissue_specificity = models.TextField(null=True, blank=True)   # Tissue specificity description from Uniprot
    expression_egenetics = models.TextField(null=True, blank=True)   # Tissues/organs the gene expressed in (egenetics data from BioMart)
    expression_gnf_atlas = models.TextField(null=True, blank=True)   # Tissues/organs the gene expressed in (GNF/Atlas data from BioMart)
    rvis_exac = models.TextField(null=True, blank=True)
    ghis = models.TextField(null=True, blank=True)
    essential_gene = models.TextField(null=True, blank=True)   # Essential ("E") or Non-essential phenotype-changing ("N") based on Mouse Genome Informatics database. from doi:10.1371/journal.pgen.1003484
    mgi_mouse_gene = models.TextField(null=True, blank=True)   # Homolog mouse gene name from MGI
    mgi_mouse_phenotype = models.TextField(null=True, blank=True)   # Phenotype description for the homolog mouse gene from MGI
    zebrafish_gene = models.TextField(null=True, blank=True)   # Homolog zebrafish gene name from ZFIN
    zebrafish_structure = models.TextField(null=True, blank=True)   # Affected structure of the homolog zebrafish gene from ZFIN
    zebrafish_phenotype_quality = models.TextField(null=True, blank=True)   # Phenotype description for the homolog zebrafish gene from ZFIN
    zebrafish_phenotype_tag = models.TextField(null=True, blank=True)   # Phenotype tag for the homolog zebrafish gene from ZFIN

    # gene constraint fields
    missense_z = models.FloatField(null=True, blank=True)
    pLI = models.FloatField(null=True, blank=True)
    pRec = models.FloatField(null=True, blank=True)


class TranscriptInfo(models.Model):
    gene = models.ForeignKey(GeneInfo, on_delete=models.CASCADE)
    transcript_id = models.CharField(max_length=20, db_index=True, unique=True)  # without the version suffix
    #protein_id = models.CharField(max_length=20, null=True)



    chrom_grch37 = models.CharField(max_length=2, null=True, blank=True)
    start_grch37 = models.IntegerField(null=True, blank=True)
    end_grch37 = models.IntegerField(null=True, blank=True)
    strand_grch37 = models.CharField(max_length=1, null=True, blank=True)
    coding_region_size_grch37 = models.IntegerField(default=0)  # number of protein-coding bases (= 0 for non-coding genes)

    chrom_grch38 = models.CharField(max_length=2, null=True, blank=True)
    start_grch38 = models.IntegerField(null=True, blank=True)
    end_grch38 = models.IntegerField(null=True, blank=True)
    strand_grch38 = models.CharField(max_length=1, null=True, blank=True)
    coding_region_size_grch38 = models.IntegerField(default=0)  # number of protein-coding bases (= 0 for non-coding genes)

# Constraint, pLI
# GTEx

