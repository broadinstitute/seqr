from django.conf import settings
from xbrowse import Variant

from xbrowse_server.base.models import FamilySearchFlag, VariantNote, VariantTag, ProjectTag, CausalVariant
from xbrowse_server.mall import get_datastore, get_annotator


def get_saved_variants_for_family(family):
    """
    Returns:
        List of variants that were saved in this family
        List of variant tuples where no variants were in the datastore
    """

    search_flags = FamilySearchFlag.objects.filter(family=family).order_by('-date_saved')
    variants = []
    couldntfind = []
    variant_tuples = {(v.xpos, v.ref, v.alt) for v in search_flags}
    for variant_t in variant_tuples:
        variant = get_datastore(family.project.project_id).get_single_variant(
            family.project.project_id,
            family.family_id,
            variant_t[0],
            variant_t[1],
            variant_t[2]
        )
        if variant:
            variants.append(variant)
        else:
            couldntfind.append(variant_t)

    return variants, couldntfind



def get_variants_from_variant_tuples(project, variant_tuples):
    variants = []
    for t in variant_tuples:
        variant = get_datastore(project.project_id).get_single_variant(
            project.project_id,
            t[3],
            t[0],
            t[1],
            t[2]
        )
        if not variant:
            variant = Variant(t[0], t[1], t[2])
            get_annotator().annotate_variant(variant, project.get_reference_population_slugs())
            
        variant.set_extra('family_id', t[3])
        variant.set_extra('project_id', project.project_id)
        variants.append(variant)
    return variants


def get_all_saved_variants_for_project(project):
    all_tuples = set()
    notes = VariantNote.objects.filter(project=project).order_by('-date_saved')
    all_tuples |= {(n.xpos, n.ref, n.alt, n.family.family_id) for n in notes}
    
    for project_tag in ProjectTag.objects.filter(project=project):
        tags = VariantTag.objects.filter(project_tag=project_tag)
        all_tuples |= {(t.xpos, t.ref, t.alt, t.family.family_id) for t in tags}
    
    variants = get_variants_from_variant_tuples(project, all_tuples)
    return variants


def get_variants_with_notes_for_project(project):
    notes = VariantNote.objects.filter(project=project).order_by('-date_saved')
    note_tuples = {(n.xpos, n.ref, n.alt, n.family.family_id) for n in notes}
    variants = get_variants_from_variant_tuples(project, note_tuples)
    return variants


def get_variants_by_tag(project, tag_slug):
    project_tag = ProjectTag.objects.get(project=project, tag=tag_slug)
    tags = VariantTag.objects.filter(project_tag=project_tag)
    tag_tuples = {(t.xpos, t.ref, t.alt, t.family.family_id) for t in tags}
    variants = get_variants_from_variant_tuples(project, tag_tuples)
    return variants


def get_causal_variants_for_project(project):
    variant_t_list = [(v.xpos, v.ref, v.alt, v.family.family_id) for v in CausalVariant.objects.filter(family__project=project)]
    variants = []
    for xpos, ref, alt, family_id in variant_t_list:
        variant = get_datastore(project.project_id).get_single_variant(
            project.project_id,
            family_id,
            xpos,
            ref,
            alt
        )
        if variant:
            variant.set_extra('family_id', family_id)
            variant.set_extra('project_id', project.project_id)
            variants.append(variant)

    return variants