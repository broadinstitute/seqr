import logging
import json
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from seqr.models import SavedVariant, VariantTagType, VariantTag, VariantNote, CAN_EDIT
from seqr.utils.xpos_utils import get_chrom_pos
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils.json_to_orm_utils import update_model_from_json
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.permissions_utils import get_project_and_check_permissions, check_permissions
from xbrowse_server.base.models import Project as BaseProject, ProjectTag

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def saved_variant_data(request, project_guid):
    project = get_project_and_check_permissions(project_guid, request.user)

    variants = {}
    variant_query = SavedVariant.objects.filter(project=project)\
        .select_related('family')\
        .only('genome_version', 'xpos_start', 'ref', 'alt', 'lifted_over_genome_version', 'lifted_over_xpos_start',
              'saved_variant_json', 'family__guid', 'guid')\
        .prefetch_related('varianttag_set', 'varianttag_set__created_by', 'varianttag_set__variant_tag_type',
                          'variantfunctionaldata_set', 'variantfunctionaldata_set__created_by', 'variantnote_set',
                          'variantnote_set__created_by')
    if request.GET.get('family'):
        variant_query = variant_query.filter(family__guid=request.GET.get('family'))
    for saved_variant in variant_query:
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
            'xpos': saved_variant.xpos_start,
            'ref': saved_variant.ref,
            'alt': saved_variant.alt,
            'chrom': chrom,
            'pos': pos,
            'genomeVersion': genome_version,
            'liftedOverGenomeVersion': lifted_over_genome_version,
            'liftedOverChrom': lifted_over_chrom,
            'liftedOverPos': lifted_over_pos,
            'familyGuid': saved_variant.family.guid,
            'tags': _variant_tags(saved_variant),
            'functionalData': [{
                'name': tag.functional_data_tag,
                'metadata': tag.metadata,
                'metadataTitle': json.loads(tag.get_functional_data_tag_display()).get('metadata_title'),
                'color': json.loads(tag.get_functional_data_tag_display())['color'],
                'user': (tag.created_by.get_full_name() or tag.created_by.email) if tag.created_by else None,
                'dateSaved': tag.last_modified_date,
            } for tag in saved_variant.variantfunctionaldata_set.all()],
            'notes': _variant_notes(saved_variant),
        }
        if variant['tags'] or variant['notes']:
            variant.update(_variant_details(variant_json, request.user))
            variants[variant['variantId']] = variant

    return create_json_response({'savedVariants': variants})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def create_variant_note_handler(request, variant_guid):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_permissions(saved_variant.project, request.user, CAN_EDIT)

    request_json = json.loads(request.body)
    # TODO in xbrowse
    VariantNote.objects.create(
        saved_variant=saved_variant,
        note=request_json.get('note'),
        submit_to_clinvar=request_json.get('submitToClinvar', False),
        search_parameters=request_json.get('searchParameters'),
        created_by=request.user,
    )

    return create_json_response({variant_guid: {'notes': _variant_notes(saved_variant)}})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_variant_note_handler(request, variant_guid, note_guid):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_permissions(saved_variant.project, request.user, CAN_EDIT)
    note = VariantNote.objects.get(guid=note_guid, saved_variant=saved_variant)

    request_json = json.loads(request.body)
    update_model_from_json(note, request_json, allow_unknown_keys=True)

    return create_json_response({variant_guid: {'notes': _variant_notes(saved_variant)}})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def delete_variant_note_handler(request, variant_guid, note_guid):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_permissions(saved_variant.project, request.user, CAN_EDIT)
    note = VariantNote.objects.get(guid=note_guid, saved_variant=saved_variant)
    # TODO in xbrowse
    note.delete()
    return create_json_response({variant_guid: {'notes': _variant_notes(saved_variant)}})


@login_required(login_url=API_LOGIN_REQUIRED_URL)
@csrf_exempt
def update_variant_tags_handler(request, variant_guid):
    saved_variant = SavedVariant.objects.get(guid=variant_guid)
    check_permissions(saved_variant.project, request.user, CAN_EDIT)

    request_json = json.loads(request.body)
    updated_tags = request_json.get('tags')
    if updated_tags is None:
        return create_json_response({}, status=400, reason="'tags' not specified")

    existing_tag_guids = [tag['tagGuid'] for tag in updated_tags if tag.get('tagGuid')]
    new_tags = [tag for tag in updated_tags if not tag.get('tagGuid')]

    variant_tags_to_delete = saved_variant.varianttag_set.exclude(guid__in=existing_tag_guids)
    # TODO in xbrowse
    variant_tags_to_delete.delete()

    for tag in new_tags:
        variant_tag_type = VariantTagType.objects.get(
            Q(name=tag['name']),
            Q(project=saved_variant.project) | Q(project__isnull=True)
        )
        # TODO in xbrowse
        VariantTag.objects.create(
            saved_variant=saved_variant,
            variant_tag_type=variant_tag_type,
            search_parameters=request_json.get('searchParameters'),
            created_by=request.user,
        )

    return create_json_response({variant_guid: {'tags': _variant_tags(saved_variant)}})


def _variant_tags(saved_variant):
    return [{
        'tagGuid': tag.guid,
        'name': tag.variant_tag_type.name,
        'category': tag.variant_tag_type.category,
        'color': tag.variant_tag_type.color,
        'user': (tag.created_by.get_full_name() or tag.created_by.email) if tag.created_by else None,
        'dateSaved': tag.last_modified_date,
        'searchParameters': tag.search_parameters,
    } for tag in saved_variant.varianttag_set.all()]


def _variant_notes(saved_variant):
    return [{
        'noteGuid': tag.guid,
        'note': tag.note,
        'submitToClinvar': tag.submit_to_clinvar,
        'user': (tag.created_by.get_full_name() or tag.created_by.email) if tag.created_by else None,
        'dateSaved': tag.last_modified_date,
    } for tag in saved_variant.variantnote_set.all()]


def _variant_details(variant_json, user):
    annotation = variant_json.get('annotation', {})
    extras = variant_json.get('extras', {})
    worst_vep_annotation = annotation['vep_annotation'][annotation['worst_vep_annotation_index']] if annotation.get('worst_vep_annotation_index') is not None and annotation['vep_annotation'] else None
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
            'vepAnnotations': [{
                'transcriptId': vep_a.get('feature') or vep_a.get('transcript_id'),
                'isChosenTranscript': i == annotation.get('worst_vep_annotation_index'),
                'aminoAcids': vep_a.get('amino_acids'),
                'canonical': vep_a.get('canonical'),
                'cdnaPosition': vep_a.get('cdna_position') or vep_a.get('cdna_start'),
                'cdsPosition': vep_a.get('cds_position'),
                'codons': vep_a.get('codons'),
                'consequence': vep_a.get('consequence') or vep_a.get('major_consequence'),
                'hgvsc': vep_a.get('hgvsc'),
                'hgvsp': vep_a.get('hgvsp'),
            } for i, vep_a in enumerate(annotation.get('vep_annotation') or [])],
            'vepConsequence': annotation.get('vep_consequence'),
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
        'hgmd': {
            'accession': extras.get('hgmd_accession'),
            'class': extras.get('hgmd_class') if user.is_staff else None,
        },
        'genes': [{
            'constraints': {
                'lof': {
                    'constraint': gene.get('lof_constraint'),
                    'rank': gene.get('lof_constraint_rank') and gene['lof_constraint_rank'][0],
                    'totalGenes': gene.get('lof_constraint_rank') and gene['lof_constraint_rank'][1],
                },
                'missense': {
                    'constraint': gene.get('missense_constraint'),
                    'rank': gene.get('missense_constraint_rank') and gene['missense_constraint_rank'][0],
                    'totalGenes': gene.get('missense_constraint_rank') and gene['missense_constraint_rank'][1],
                },
            },
            'diseaseGeneLists': gene.get('disease_gene_lists', []),
            'geneId': gene_id,
            'diseaseDbPheotypes': gene.get('disease_db_pheotypes', []),
            'symbol': gene.get('symbol') or extras.get('gene_names', {}).get(gene_id),
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
    DEFAULT_VARIANT_TAGS = [
        {
            "order": 1,
            "category": "CMG Discovery Tags",
            "tag_name": "Tier 1 - Novel gene and phenotype",
            "color": "#03441E",
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

    base_project = BaseProject.objects.get(project_id=project.deprecated_project_id)
    for r in DEFAULT_VARIANT_TAGS:
        t, created = ProjectTag.objects.get_or_create(project=base_project, tag=r['tag_name'])
        t.order = r['order']
        t.category = r['category']
        t.title = r['description']
        t.color = r['color']
        t.save()
