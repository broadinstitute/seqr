from django.db import models

#  Allow adding the custom json_fields and internal_json_fields to the model Meta
# (from https://stackoverflow.com/questions/1088431/adding-attributes-into-django-models-meta-class)
models.options.DEFAULT_NAMES = models.options.DEFAULT_NAMES + ('json_fields',)

GENOME_VERSION_GRCh37 = "37"
GENOME_VERSION_GRCh38 = "38"

GENOME_VERSION_CHOICES = [
    (GENOME_VERSION_GRCh37, "GRCh37"),
    (GENOME_VERSION_GRCh38, "GRCh38")
]
GENOME_VERSION_LOOKUP = {k: v for (k, v) in GENOME_VERSION_CHOICES}


class ReferenceDataRouter(object):
    """
    A router to control all database operations on reference data models
    """
    @classmethod
    def db_for_read(cls, model, **hints):
        """
        Attempts to read reference_data models go to reference_data_db.
        """
        if model._meta.app_label == 'reference_data':
            return 'reference_data'
        return None

    @classmethod
    def db_for_write(cls, model, **hints):
        """
        Attempts to write reference_data models go to reference_data_db.
        """
        if model._meta.app_label == 'reference_data':
            return 'reference_data'
        return None

    @classmethod
    def allow_relation(cls, obj1, obj2, **hints):
        """
        Allow relations if a model in the reference_data app is involved.
        """
        if obj1._meta.app_label == 'reference_data' or \
           obj2._meta.app_label == 'reference_data':
           return True
        return None

    @classmethod
    def allow_migrate(cls, db, app_label, model_name=None, **hints):
        """
        Make sure the reference_data app only appears in the 'reference_data_db'
        database.
        """
        if app_label == 'reference_data':
            return db == 'reference_data'
        elif db == 'reference_data':
            return False
        return None


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
    gene_id = models.CharField(max_length=20, db_index=True, unique=True)   # without the version suffix (eg. "ENSG0000012345")
    gene_symbol = models.TextField(null=True, blank=True)

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

    # gencode-specific fields, although models could hypothetically come from refseq or other places
    gencode_gene_type = models.TextField(null=True, blank=True)
    gencode_release = models.IntegerField(null=True, blank=True)

    class Meta:
        json_fields = [
            'gene_id', 'gene_symbol', 'chrom_grch37', 'start_grch37', 'end_grch37', 'chrom_grch38', 'start_grch38',
            'end_grch38', 'gencode_gene_type', 'coding_region_size_grch37', 'coding_region_size_grch38',
        ]


class TranscriptInfo(models.Model):
    gene = models.ForeignKey(GeneInfo, on_delete=models.CASCADE)

    transcript_id = models.CharField(max_length=20, db_index=True, unique=True)  # without the version suffix
    is_mane_select = models.BooleanField(default=False)

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

    class Meta:
        json_fields = ['transcript_id', 'is_mane_select']


class RefseqTranscript(models.Model):
    transcript = models.OneToOneField(TranscriptInfo, on_delete=models.CASCADE)
    refseq_id = models.CharField(max_length=20)


# based on # ftp://ftp.broadinstitute.org/pub/ExAC_release/release0.3.1/functional_gene_constraint/fordist_cleaned_exac_r03_march16_z_pli_rec_null_data.txt
class GeneConstraint(models.Model):
    gene = models.ForeignKey(GeneInfo, on_delete=models.CASCADE)

    mis_z = models.FloatField()
    mis_z_rank = models.IntegerField()
    pLI = models.FloatField()
    pLI_rank = models.IntegerField()
    louef = models.FloatField()
    louef_rank = models.IntegerField()

    class Meta:
        json_fields = ['mis_z', 'mis_z_rank', 'pLI', 'pLI_rank', 'louef', 'louef_rank']


class GeneCopyNumberSensitivity(models.Model):
    gene = models.ForeignKey(GeneInfo, on_delete=models.CASCADE)

    pHI = models.FloatField()
    pTS = models.FloatField()

    class Meta:
        json_fields = ['pHI', 'pTS']


class GeneShet(models.Model):
    gene = models.ForeignKey(GeneInfo, on_delete=models.CASCADE)

    post_mean = models.FloatField()

    class Meta:
        json_fields = ['post_mean']


class Omim(models.Model):
    MAP_METHOD_CHOICES = (
        ('1', 'the disorder is placed on the map based on its association with a gene, but the underlying defect is not known.'),
        ('2', 'the disorder has been placed on the map by linkage; no mutation has been found.'),
        ('3', 'the molecular basis for the disorder is known; a mutation has been found in the gene.'),
        ('4', 'a contiguous gene deletion or duplication syndrome, multiple genes are deleted or duplicated causing the phenotype.'),
    )

    gene = models.ForeignKey(GeneInfo, on_delete=models.CASCADE, null=True, blank=True)

    chrom = models.CharField(max_length=2)
    start = models.IntegerField()
    end = models.IntegerField()

    mim_number = models.IntegerField()  # Example: 601365
    gene_description = models.TextField(null=True, blank=True)  # Example: "Dishevelled 1 (homologous to Drosophila dsh)"
    comments = models.TextField(null=True, blank=True)  # Example: "associated with rs10492972"
    phenotype_inheritance = models.TextField(null=True, blank=True)  # Example: "Autosomal dominant"
    phenotype_mim_number = models.IntegerField(null=True, blank=True)  # Example: 616331
    phenotype_description = models.TextField(null=True, blank=True)  # Example: "Robinow syndrome, autosomal dominant 2"
    phenotype_map_method = models.CharField(max_length=1, choices=MAP_METHOD_CHOICES, null=True, blank=True)  # Example: 2

    class Meta:
        # ('mim_number', 'phenotype_mim_number') is not unique - for example ('124020', '609535')
        unique_together = ('mim_number', 'phenotype_mim_number', 'phenotype_description')

        json_fields = ['mim_number', 'phenotype_mim_number', 'phenotype_description', 'phenotype_inheritance',
                       'chrom', 'start', 'end',]


# based on dbNSFPv3.5a_gene fields
class dbNSFPGene(models.Model):
    gene = models.ForeignKey(GeneInfo, on_delete=models.CASCADE)
    gene_names = models.TextField(blank=True)

    function_desc = models.TextField(null=True, blank=True)
    disease_desc = models.TextField(null=True, blank=True)
    uniprot_acc = models.TextField(null=True, blank=True)
    uniprot_id = models.TextField(null=True, blank=True)
    entrez_gene_id = models.TextField(null=True, blank=True)
    ccds_id = models.TextField(null=True, blank=True)
    refseq_id = models.TextField(null=True, blank=True)
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

    class Meta:
        json_fields = ['function_desc', 'disease_desc', 'gene_names']


class PrimateAI(models.Model):
    gene = models.ForeignKey(GeneInfo, on_delete=models.CASCADE)

    percentile_25 = models.FloatField()
    percentile_75 = models.FloatField()

    class Meta:
        json_fields = ['percentile_25', 'percentile_75']


class MGI(models.Model):
    gene = models.ForeignKey(GeneInfo, on_delete=models.CASCADE)

    marker_id = models.CharField(max_length=15)

    class Meta:
        unique_together = ('gene', 'marker_id')
        json_fields = ['marker_id']


class GenCC(models.Model):
    gene = models.ForeignKey(GeneInfo, on_delete=models.CASCADE)

    hgnc_id = models.CharField(max_length=10)
    classifications = models.JSONField()

    class Meta:
        json_fields = ['classifications', 'hgnc_id']


class ClinGen(models.Model):
    gene = models.ForeignKey(GeneInfo, on_delete=models.CASCADE)

    haploinsufficiency = models.TextField()
    triplosensitivity = models.TextField()
    href = models.TextField()

    class Meta:
        json_fields = ['haploinsufficiency', 'triplosensitivity', 'href']
