import logging
import json
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from pretty_times import pretty

from seqr.models import SavedVariant, VariantTagType
from seqr.utils.xpos_utils import get_chrom_pos
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.permissions_utils import get_project_and_check_permissions
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


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def saved_variant_data(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)

    variants = []
    for saved_variant in SavedVariant.objects.filter(project=project):
        variant_json = json.loads(saved_variant.saved_variant_json or '{}')
        chrom, pos = get_chrom_pos(saved_variant.xpos)
        genome_version = variant_json.get('extras', {}).get('genome_version', saved_variant.genome_version)
        lifted_over_genome_version = saved_variant.lifted_over_genome_version or ('37' if genome_version == '38' else '38')
        if saved_variant.lifted_over_xpos_start:
            lifted_over_chrom, lifted_over_pos = get_chrom_pos(saved_variant.lifted_over_xpos_start)
        else:
            coords_field = 'grch%s_coords' % lifted_over_genome_version
            coords = variant_json.get('extras', {}).get(coords_field, '').split('-')
            lifted_over_chrom = coords[0].lstrip('chr')
            lifted_over_pos = coords[1] if len(coords) > 1 else ''
        variant = {
            'variantId': saved_variant.guid,
            'xpos': saved_variant.xpos,
            'ref': saved_variant.ref,
            'alt': saved_variant.alt,
            'chrom': chrom,
            'pos': pos,
            'genomeVersion': genome_version,
            'liftedOverGenomeVersion': lifted_over_genome_version,
            'liftedOverChrom': lifted_over_chrom,
            'liftedOverPos': lifted_over_pos,
            'familyGuid': saved_variant.family.guid,
            'tags': [{
                'name': tag.variant_tag_type.name,
                'category': tag.variant_tag_type.category,
                'color': tag.variant_tag_type.color,
                'user': (tag.created_by.get_full_name() or tag.created_by.email) if tag.created_by else None,
                'dateSaved': pretty.date(tag.last_modified_date) if tag.last_modified_date else None,
                'searchParameters': tag.search_parameters,
            } for tag in saved_variant.varianttag_set.all()],
            'functionalData': [{
                'name': tag.functional_data_tag,
                'metadata': tag.metadata,
                'metadataTitle': json.loads(tag.get_functional_data_tag_display()).get('metadata_title'),
                'color': json.loads(tag.get_functional_data_tag_display())['color'],
                'user': (tag.created_by.get_full_name() or tag.created_by.email) if tag.created_by else None,
                'dateSaved': pretty.date(tag.last_modified_date) if tag.last_modified_date else None,
            } for tag in saved_variant.variantfunctionaldata_set.all()],
            'notes': [{
                'noteGuid': tag.guid,
                'note': tag.note,
                'submitToClinvar': tag.submit_to_clinvar,
                'user': (tag.created_by.get_full_name() or tag.created_by.email) if tag.created_by else None,
                'dateSaved': pretty.date(tag.last_modified_date) if tag.last_modified_date else None,
            } for tag in saved_variant.variantnote_set.all()],
        }
        if variant['tags'] or variant['notes']:
            variant.update(_variant_details(variant_json))
            variants.append(variant)

    return create_json_response({'savedVariants': variants})


def _variant_details(variant_json):
    annotation = variant_json.get('annotation', {})
    extras = variant_json.get('extras', {})
    worst_vep_annotation = annotation['vep_annotation'][annotation['worst_vep_annotation_index']] if annotation.get('worst_vep_annotation_index') is not None else None
    is_es_variant = annotation.get('db') == 'elasticsearch'
    return {
        'annotation': {
            'cadd_phred': annotation.get('cadd_phred'),
            'dann_score': annotation.get('dann_score'),
            'eigen_phred': annotation.get('eigen_phred'),
            'fathmm': annotation.get('fathmm'),
            'freqs': {
                'AF': annotation.get('freqs', {}).get('AF'),
                'topmedAF': annotation.get('freqs', {}).get('topmed_AF'),
                'g1k': annotation.get('freqs', {}).get('1kg_wgs_popmax_AF', annotation.get('freqs', {}).get(
                    '1kg_wgs_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    '1kg_wgs_phase3_popmax', annotation.get('freqs', {}).get('1kg_wgs_phase3', 0)),
                'exac': annotation.get('freqs', {}).get(
                    'exac_v3_popmax_AF', annotation.get('freqs', {}).get(
                        'exac_v3_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    'exac_v3_popmax', annotation.get('freqs', {}).get('exac_v3', 0)),
                'gnomad_exomes': annotation.get('freqs', {}).get(
                    'gnomad_exomes_popmax_AF', annotation.get('freqs', {}).get(
                        'gnomad_exomes_AF', 0)) if is_es_variant else annotation.get(
                    'freqs', {}).get('gnomad-exomes2_popmax', annotation.get('freqs', {}).get('gnomad-exomes2', None)),
                'gnomad_genomes': annotation.get('freqs', {}).get('gnomad_genomes_popmax_AF', annotation.get(
                    'freqs', {}).get('gnomad_genomes_AF', 0)) if is_es_variant else annotation.get('freqs', {}).get(
                    'gnomad-gnomad-genomes2_popmax', annotation.get('freqs', {}).get('gnomad-genomes2', None)),
            },
            'mpc_score': annotation.get('mpc_score'),
            'mut_taster': annotation.get('muttaster'),
            'polyphen': annotation.get('polyphen'),
            'popCounts': {
                'AC': annotation.get('pop_counts', {}).get('AC'),
                'AN': annotation.get('pop_counts', {}).get('AN'),
                'topmedAC': annotation.get('pop_counts', {}).get('topmed_AC'),
                'gnomadExomesAC': annotation.get('pop_counts', {}).get('gnomad_exomes_AC'),
                'gnomadGenomesAC': annotation.get('pop_counts', {}).get('gnomad_genomes_AC'),
                'exac_hom': annotation.get('pop_counts', {}).get('exac_v3_Hom'),
                'exac_hemi': annotation.get('pop_counts', {}).get('exac_v3_Hemi'),
                'gnomad_exomes_hom': annotation.get('pop_counts', {}).get('gnomad_exomes_Hom'),
                'gnomad_exomes_hemi': annotation.get('pop_counts', {}).get('gnomad_exomes_Hemi'),
                'gnomad_genomes_hom': annotation.get('pop_counts', {}).get('gnomad_genomes_Hom'),
                'gnomad_genomes_hemi': annotation.get('pop_counts', {}).get('gnomad_genomes_Hemi'),
            },
            'revel_score': annotation.get('revel_score'),
            'rsid': annotation.get('rsid'),
            'sift': annotation.get('sift'),
            'vepGroup': annotation.get('vep_group'),
            'worstVepAnnotation': {
                'symbol': worst_vep_annotation.get('gene_symbol') or worst_vep_annotation.get('symbol'),
                'lof': worst_vep_annotation.get('lof'),
                'lofFlags': worst_vep_annotation.get('lof_flags'),
                'lofFilter': worst_vep_annotation.get('lof_filter'),
                'hgvsc': worst_vep_annotation.get('hgvsc'),
                'hgvsp': worst_vep_annotation.get('hgvsp'),
                'aminoAcids': worst_vep_annotation.get('amino_acids'),
                'proteinPosition': worst_vep_annotation.get('protein_position'),
            } if worst_vep_annotation else None,
        },
        'clinvar': {
            'clinsig': extras.get('clinvar_clinsig'),
            'variantId': extras.get('clinvar_variant_id'),
        },
        'genes': [{
            'constraints': {
                'lof': {
                    'constraint': (gene or {}).get('lof_constraint'),
                    'rank': (gene or {}).get('lof_constraint_rank') and gene['lof_constraint_rank'][0],
                    'totalGenes': (gene or {}).get('lof_constraint_rank') and gene['lof_constraint_rank'][1],
                },
                'missense': {
                    'constraint': (gene or {}).get('missense_constraint'),
                    'rank': (gene or {}).get('missense_constraint_rank') and gene['missense_constraint_rank'][0],
                    'totalGenes': (gene or {}).get('missense_constraint_rank') and gene['missense_constraint_rank'][1],
                },
            },
            'diseaseGeneLists': (gene or {}).get('disease_gene_lists', []),
            'geneId': gene_id,
            'inDiseaseDb': (gene or {}).get('in_disease_db'),
            'symbol': (gene or {}).get('symbol') or extras.get('gene_names', {}).get(gene_id),
        } for gene_id, gene in extras.get('genes', {}).items()],
        'genotypes': {
            individual_id: {
                'ab': genotype.get('ab'),
                'ad': genotype.get('extras', {}).get('ad'),
                'alleles': genotype.get('alleles', []),
                'cnvs': {
                    'array': genotype.get('extras', {}).get('cnvs', {}).get('array'),
                    'caller': genotype.get('extras', {}).get('cnvs', {}).get('caller'),
                    'cn': genotype.get('extras', {}).get('cnvs', {}).get('cn'),
                    'freq': genotype.get('extras', {}).get('cnvs', {}).get('freq'),
                    'LRR_median': genotype.get('extras', {}).get('cnvs', {}).get('LRR_median'),
                    'LRR_sd': genotype.get('extras', {}).get('cnvs', {}).get('LRR_sd'),
                    'size': genotype.get('extras', {}).get('cnvs', {}).get('size'),
                    'snps': genotype.get('extras', {}).get('cnvs', {}).get('snps'),
                    'type': genotype.get('extras', {}).get('cnvs', {}).get('type'),
                },
                'dp': genotype.get('extras', {}).get('dp'),
                'filter': genotype.get('filter'),
                'gq': genotype.get('gq'),
                'numAlt': genotype.get('num_alt'),
                'pl': genotype.get('extras', {}).get('pl'),
            } for individual_id, genotype in variant_json.get('genotypes', {}).items()
        },
        'origAltAlleles': extras.get('orig_alt_alleles', []),
    }


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
