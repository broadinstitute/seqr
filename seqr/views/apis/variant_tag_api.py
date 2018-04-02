import logging
from seqr.models import VariantTagType
from xbrowse_server.base.models import Project as BaseProject, ProjectTag

logger = logging.getLogger(__name__)

DEFAULT_VARIANT_TAGS = [
    {
        "order": 1,
        "category": "CMG Discovery Tags",
        "tag_name": "Tier 1 - Novel gene and phenotype",
        "color":  "#03441E", 
        "description": "Gene not previously associated with a Mendelian condition", 
    },
    {
        "order": 2, 
        "category": "CMG Discovery Tags", 
        "tag_name": "Tier 1 - Novel gene for known phenotype", 
        "color": "#096C2F", 
        "description": "Phenotype known but no causal gene known (includes adding to locus heterogeneity)",
    },
    {
        "order": 3, 
        "category": "CMG Discovery Tags", 
        "tag_name": "Tier 1 - Phenotype expansion", 
        "color": "#298A49", 
        "description": "Phenotype studies have different clinical characteristics and/or natural history"
    },
    {
        "order": 4,
        "category": "CMG Discovery Tags",
        "tag_name": "Tier 1 - Phenotype not delineated",
        "color": "#44AA60",
        "description": "Phenotype not previously delineated (i.e. no MIM #)"
    },
    {
        "order": 5,
        "category": "CMG Discovery Tags",
        "tag_name": "Tier 1 - Novel mode of inheritance",
        "color": "#75C475",
        "description": "Gene previously associated with a Mendelian condition but mode of inheritance is different",
    },
    {
        "order": 6,
        "category": "CMG Discovery Tags",
        "tag_name": "Tier 2 - Novel gene and phenotype",
        "color": "#0B437D",
        "description": "Gene not previously associated with a Mendelian condition"
    },
    {
        "order": 7,
        "category": "CMG Discovery Tags",
        "tag_name": "Tier 2 - Novel gene for known phenotype",
        "color": "#1469B0",
        "description": "Phenotype known but no causal gene known (includes adding to locus heterogeneity)",
    },
    {
        "order": 7.5,
        "category": "CMG Discovery Tags",
        "tag_name": "Tier 2 - Phenotype expansion",
        "description": "Phenotype studies have different clinical characteristics and/or natural history",
        "color": "#318CC2"
    },
    {
        "order": 8, "category":
        "CMG Discovery Tags",
        "tag_name": "Tier 2 - Phenotype not delineated",
        "color": "#318CC2",
        "description": "Phenotype not previously delineated (i.e. no OMIM #)",
    },
    {
        "order": 9,
        "category": "CMG Discovery Tags",
        "tag_name": "Known gene for phenotype",
        "color": "#030A75",
        "description": "The gene overlapping the variant has been previously associated with the same phenotype presented by the patient",
    },
    {
        "order": 10,
        "category": "Collaboration",
        "tag_name": "Review",
        "description": "Variant and/or gene of interest for further review",
        "color": "#668FE3"
    },
    {
        "order": 10.3,
        "category": "Collaboration",
        "tag_name": "Send for Sanger validation",
        "description": "Send for Sanger validation",
        "color": "#f1af5f"
    },
    {
        "order": 10.31,
        "category": "Collaboration",
        "tag_name": "Sanger validated",
        "description": "Confirmed by Sanger sequencing",
        "color": "#b2df8a",
    },
    {
        "order": 10.32,
        "category": "Collaboration",
        "tag_name": "Sanger did not validate",
        "description": "Sanger did not validate",
        "color": "#823a3a",
    },
    {
        "order": 10.5,
        "category": "Collaboration",
        "tag_name": "Excluded",
        "description": "Variant and/or gene you previously reviewed but do not think it contributing to the phenotype in this case. To help other members of your team (and yourself), please consider also adding a note with details of why you reprioritized this variant.",
        "color": "#555555"
    },
    {
        "order": 11, 
        "category": "ACMG Variant Classification",
        "tag_name": "Pathogenic",
        "description": "",
        "color": "#B92732"
    },
    {
        "order": 12, 
        "category": "ACMG Variant Classification",
        "tag_name": "Likely Pathogenic",
        "description": "",
        "color": "#E48065"
    },
    {
        "order": 13, 
        "category": "ACMG Variant Classification",
        "tag_name": "VUS",
        "description": "Variant of uncertain significance",
        "color": "#FACCB4"
    },
    {
        "order": 14, 
        "category": "ACMG Variant Classification",
        "tag_name": "Likely Benign",
        "description": "",
        "color": "#6BACD0"
    },
    {
        "order": 15,
        "category": "ACMG Variant Classification",
        "tag_name": "Benign",
        "description": "",
        "color": "#2971B1"
    },
    {
        "order": 16, 
        "category": "ACMG Variant Classification",
        "tag_name": "Secondary finding",
        "color": "#FED82F",
        "description": "The variant was found during the course of searching for candidate disease genes and can be described as pathogenic or likely pathogenic according to ACMG criteria and overlaps a gene known to cause a disease that differs from the patient's primary indication for sequencing."
    },
    {
        "order": 17, 
        "category": "Data Sharing",
        "tag_name": "MatchBox (MME)",
        "description": "Gene, variant, and phenotype to be submitted to Matchmaker Exchange",
        "color": "#531B86"
    },
    {
        "order": 18, 
        "category": "Data Sharing",
        "tag_name": "Submit to Clinvar",
        "description": "By selecting this tag, you are notifying CMG staff that this variant should be submitted to ClinVar. Generally, this is for pathogenic or likely pathogenic variants in known disease genes or for any benign or likely benign variants that are incorrectly annotated in ClinVar. Please also add a note that describes supporting evidence for how you interpreted this variant.",
        "color": "#8A62AE"
    },
    {
        "order": 19,
        "category": "Data Sharing",
        "tag_name": "Share with KOMP",
        "description": "To mark a variant/gene that you would like us to share with the Mouse Knockout Project for their knockout and phenotyping pipeline. Add additional notes to comments as needed.",
        "color": "#ad627a"
    },
]


def _deprecated_add_default_tags_to_original_project(project):
    base_project = BaseProject.objects.get(project_id=project.deprecated_project_id)
    for r in DEFAULT_VARIANT_TAGS:
        t, created = ProjectTag.objects.get_or_create(project=base_project, tag=r['tag_name'])
        t.order = r['order']
        t.category = r['category']
        t.title = r['description']
        t.color = r['color']
        t.save()


def _add_default_variant_tag_types(project):
    """
    name = models.TextField()
    category = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    color = models.CharField(max_length=20, default="#1f78b4")
    order = models.FloatField(null=True)
    is_built_in = models.BooleanField(default=False)  # built-in tags (eg. "Pathogenic") can't be modified by users through the UI
    """
    for r in DEFAULT_VARIANT_TAGS:
        vtt, created = VariantTagType.objects.get_or_create(project=project, name=r['tag_name'])
        if created:
            logger.info("Created variant tag: %(tag_name)s" % r)
        vtt.order = r['order']
        vtt.category = r['category']
        vtt.description = r['description']
        vtt.color = r['color']
        vtt.save()

    _deprecated_add_default_tags_to_original_project(project)
