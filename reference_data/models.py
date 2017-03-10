from django.db import models

GENOME_BUILD_GRCh37 = "b37"
GENOME_BUILD_GRCh38 = "b38"

_GENOME_BUILD_CHOICES = (
    (GENOME_BUILD_GRCh37, GENOME_BUILD_GRCh37),
    (GENOME_BUILD_GRCh38, GENOME_BUILD_GRCh38),
)


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


class GencodeRelease(models.Model):
    release_number = models.IntegerField(unique=True)  # eg. 25
    release_date = models.DateTimeField(unique=True)
    genome_build_id = models.CharField(max_length=3, choices=_GENOME_BUILD_CHOICES)

    def __unicode__(self):
        return "gencode_v%s (released: %s)" % (self.release_number, str(self.release_date)[:10])


GENCODE_STATUS_CHOICES = (
    ("K", "KNOWN"),
    ("N", "NOVEL"),
    ("P", "PUTATIVE"),
)

GENCODE_SOURCE_CHOICES = (
    ('H', 'HAVANA'),
    ('E', 'ENSEMBL'),
)


class GencodeGene(models.Model):
    """Human gene models from https://www.gencodegenes.org/releases/
    http://www.gencodegenes.org/gencodeformat.html
    """
    gencode_release = models.ForeignKey(GencodeRelease)
    chrom = models.CharField(max_length=1)
    start = models.IntegerField()
    end = models.IntegerField()

    source = models.CharField(max_length=1, choices=GENCODE_SOURCE_CHOICES)
    strand = models.CharField(max_length=1)

    gene_id = models.CharField(max_length=20, db_index=True)         # without the version suffix
    gene_type = models.CharField(max_length=30, db_index=True)
    gene_status = models.CharField(max_length=1, choices=GENCODE_STATUS_CHOICES)
    gene_name = models.CharField(max_length=30, db_index=True)

    level = models.IntegerField()

    protein_id = models.CharField(max_length=20, null=True)

    class Meta:
        unique_together = ('gencode_release', 'chrom', 'start', 'end', 'gene_id')


class GencodeTranscript(models.Model):
    gencode_release = models.ForeignKey(GencodeRelease)
    gene = models.ForeignKey(GencodeGene)

    chrom = models.CharField(max_length=1)
    start = models.IntegerField()
    end = models.IntegerField()

    source = models.CharField(max_length=1, choices=GENCODE_SOURCE_CHOICES)
    strand = models.CharField(max_length=1)

    transcript_id = models.CharField(max_length=20, db_index=True)  # without the version suffix
    transcript_status = models.CharField(max_length=1, choices=GENCODE_STATUS_CHOICES)
    transcript_name = models.CharField(max_length=30, db_index=True)

    transcript_support_level = models.IntegerField(null=True)

    class Meta:
        unique_together = ('gencode_release', 'chrom', 'start', 'end', 'transcript_id')


class OMIM(models.Model):
    MAP_METHOD_CHOICES = (
        ('1', 'the disorder is placed on the map based on its association with a gene, but the underlying defect is not known.'),
        ('2', 'the disorder has been placed on the map by linkage; no mutation has been found.'),
        ('3', 'the molecular basis for the disorder is known; a mutation has been found in the gene.'),
        ('4', 'a contiguous gene deletion or duplication syndrome, multiple genes are deleted or duplicated causing the phenotype.'),
    )

    mim_number = models.IntegerField()  #  Example: 601365
    gene_id = models.CharField(max_length=20, db_index=True)  # Example: "ENSG00000107404"
    gene_symbol = models.CharField(null=True, blank=True, max_length=20)  # Example: "DVL1"
    gene_description = models.TextField(null=True, blank=True, max_length=20)  # Example: "Dishevelled 1 (homologous to Drosophila dsh)"
    comments = models.TextField(null=True, blank=True)  # Example: "associated with rs10492972"
    phenotype_inheritance = models.TextField(null=True, blank=True)  # Example: "Autosomal dominant"
    phenotype_mim_number = models.IntegerField(null=True, blank=True)  # Example: 616331
    phenotype_description = models.TextField(null=True, blank=True)  # Example: "Robinow syndrome, autosomal dominant 2"
    phenotype_map_method  = models.CharField(max_length=1, choices=MAP_METHOD_CHOICES)  # Example: 2
    date_downloaded = models.DateTimeField(auto_now_add=True)

    class Meta:
        # ('mim_number', 'phenotype_mim_number') is not unique - for example ('124020', '609535')
        unique_together = ('mim_number', 'phenotype_description')


class dbNSFPGene(models.Model):
    gene_id = models.CharField(max_length=20, db_index=True)  # Example: "ENSG00000107404"
    function_desc = models.TextField(null=True, blank=True)
    disease_desc = models.TextField(null=True, blank=True)


"""
class ClinvarRelease(models.Model):
    release_date = models.DateTimeField()
    genome_build_id = models.CharField(max_length=3, choices=_GENOME_BUILD_CHOICES)


class Clinvar(models.Model):
    ""clinvar table""


# Clinvar
# Constraint, pLI
# GTEx
# dbNSFP gene table
"""

