from django.db import models
from django.db.models import options

#  Allow adding the custom json_fields and internal_json_fields to the model Meta
# (from https://stackoverflow.com/questions/1088431/adding-attributes-into-django-models-meta-class)
options.DEFAULT_NAMES = options.DEFAULT_NAMES + ('json_fields', 'internal_json_fields',)

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


GENCODE_SOURCE_CHOICES = (
    ('H', 'HAVANA'),
    ('E', 'ENSEMBL'),
)


class GencodeGene(models.Model):
    """Human gene models from https://www.gencodegenes.org/releases/
    http://www.gencodegenes.org/gencodeformat.html
    """
    genome_version = models.CharField(max_length=3, choices=GENOME_VERSION_CHOICES)
    chrom = models.CharField(max_length=1)
    start = models.IntegerField()
    end = models.IntegerField()

    source = models.CharField(max_length=1, choices=GENCODE_SOURCE_CHOICES)
    strand = models.CharField(max_length=1)

    gene_id = models.CharField(max_length=20, db_index=True)         # without the version suffix
    gene_type = models.CharField(max_length=100, db_index=True)
    gene_name = models.CharField(max_length=100, db_index=True)

    level = models.IntegerField()

    protein_id = models.CharField(max_length=20, null=True)

    class Meta:
        unique_together = ('genome_version', 'gene_id', 'chrom', 'start', 'end')
        json_fields = [
            'genome_version', 'chrom', 'start', 'end', 'source', 'strand', 'gene_id',
            'gene_type', 'gene_name', 'level', 'protein_id'
        ]


class GencodeTranscript(models.Model):
    genome_version = models.CharField(max_length=3, choices=GENOME_VERSION_CHOICES)
    gene = models.ForeignKey(GencodeGene, on_delete=models.CASCADE)

    chrom = models.CharField(max_length=1)
    start = models.IntegerField()
    end = models.IntegerField()

    source = models.CharField(max_length=1, choices=GENCODE_SOURCE_CHOICES)
    strand = models.CharField(max_length=1)

    transcript_id = models.CharField(max_length=20, db_index=True)  # without the version suffix
    transcript_name = models.CharField(max_length=30, db_index=True)

    transcript_support_level = models.CharField(max_length=2, null=True)

    class Meta:
        unique_together = ('genome_version', 'transcript_id', 'chrom', 'start', 'end')
        json_fields = ('genome_version', 'chrom', 'start', 'end', 'source', 'strand', 'gene_id',
                       'transcript_id', 'transcript_name', 'transcript_support_level')

class OMIM(models.Model):
    MAP_METHOD_CHOICES = (
        ('1', 'the disorder is placed on the map based on its association with a gene, but the underlying defect is not known.'),
        ('2', 'the disorder has been placed on the map by linkage; no mutation has been found.'),
        ('3', 'the molecular basis for the disorder is known; a mutation has been found in the gene.'),
        ('4', 'a contiguous gene deletion or duplication syndrome, multiple genes are deleted or duplicated causing the phenotype.'),
    )

    date_downloaded = models.DateTimeField(auto_now_add=True)
    mim_number = models.IntegerField()  #  Example: 601365
    gene_id = models.CharField(max_length=20, db_index=True)  # Example: "ENSG00000107404"
    gene_symbol = models.CharField(null=True, blank=True, max_length=20)  # Example: "DVL1"
    gene_description = models.TextField(null=True, blank=True, max_length=20)  # Example: "Dishevelled 1 (homologous to Drosophila dsh)"
    comments = models.TextField(null=True, blank=True)  # Example: "associated with rs10492972"
    phenotype_inheritance = models.TextField(null=True, blank=True)  # Example: "Autosomal dominant"
    phenotype_mim_number = models.IntegerField(null=True, blank=True)  # Example: 616331
    phenotype_description = models.TextField(null=True, blank=True)  # Example: "Robinow syndrome, autosomal dominant 2"
    phenotype_map_method  = models.CharField(max_length=1, choices=MAP_METHOD_CHOICES)  # Example: 2

    class Meta:
        # ('mim_number', 'phenotype_mim_number') is not unique - for example ('124020', '609535')
        unique_together = ('mim_number', 'phenotype_description')


class dbNSFPGene(models.Model):
    gene_id = models.CharField(max_length=20, db_index=True)  # Example: "ENSG00000107404"
    function_desc = models.TextField(null=True, blank=True)
    disease_desc = models.TextField(null=True, blank=True)


class Clinvar(models.Model):
    release_date = models.DateTimeField()
    genome_version = models.CharField(max_length=3, choices=GENOME_VERSION_CHOICES)

    chrom = models.CharField(max_length=1)
    pos = models.IntegerField()
    ref = models.TextField(null=True, blank=True)
    alt = models.TextField(null=True, blank=True)

    measureset_type = models.TextField(null=True, blank=True)
    measureset_id = models.TextField(null=True, blank=True)
    rcv = models.TextField(null=True, blank=True)
    allele_id = models.TextField(null=True, blank=True)
    symbol = models.TextField(null=True, blank=True)
    hgvs_c = models.TextField(null=True, blank=True)
    hgvs_p = models.TextField(null=True, blank=True)
    molecular_consequence = models.TextField(null=True, blank=True)
    clinical_significance = models.TextField(null=True, blank=True)
    pathogenic = models.BooleanField()
    benign = models.BooleanField()
    conflicted = models.BooleanField()
    review_status = models.TextField(null=True, blank=True)
    gold_stars = models.IntegerField()
    all_submitters = models.TextField(null=True, blank=True)
    all_traits = models.TextField(null=True, blank=True)
    all_pmids = models.TextField(null=True, blank=True)
    inheritance_modes = models.TextField(null=True, blank=True)
    age_of_onset = models.TextField(null=True, blank=True)
    prevalence = models.TextField(null=True, blank=True)
    disease_mechanism = models.TextField(null=True, blank=True)
    origin = models.TextField(null=True, blank=True)
    xrefs = models.TextField(null=True, blank=True)

# Constraint, pLI
# GTEx

