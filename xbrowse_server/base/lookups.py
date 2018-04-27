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
    for variant_t, variant in zip(variant_tuples, get_datastore(family.project).get_multiple_variants(
        family.project.project_id,
        family.family_id,
        variant_tuples,
    )):
        if variant:
            variants.append(variant)
        else:
            couldntfind.append(variant_t)

    return variants, couldntfind


def get_variants_from_variant_tuples(project, variant_tuples):
    datastore = get_datastore(project)
    population_slugs = project.get_reference_population_slugs()

    variant_tuples_by_family_id = {}
    for xpos, ref, alt, family_id in variant_tuples:
        if family_id not in variant_tuples_by_family_id:
            variant_tuples_by_family_id[family_id] = []
        variant_tuples_by_family_id[family_id].append((xpos, ref, alt))

    variants = []
    for family_id, variant_tuples in variant_tuples_by_family_id.items():
        variants_for_family = datastore.get_multiple_variants(
            project.project_id,
            family_id,
            variant_tuples
        )
        for (xpos, ref, alt), variant in zip(variant_tuples, variants_for_family):
            if not variant:
                variant = Variant(xpos, ref, alt)
                get_annotator().annotate_variant(variant, population_slugs)

            variant.set_extra('family_id', family_id)
            variant.set_extra('project_id', project.project_id)
            variants.append(variant)

    return variants


def get_all_saved_variants_for_project(project, family_id=None):
    all_tuples = set()
    notes = VariantNote.objects.filter(project=project).order_by('-date_saved').select_related('family').only('xpos', 'alt', 'ref', 'family__family_id')
    if family_id:
        notes = notes.filter(family__family_id=family_id)
    all_tuples |= {(n.xpos, n.ref, n.alt, n.family.family_id) for n in notes}

    tags = VariantTag.objects.filter(
        project_tag__project=project
    ).exclude(project_tag__tag=None).select_related('project_tag').select_related('family').only(
        'xpos', 'alt', 'ref', 'family__family_id', 'project_tag__tag'
    )
    if family_id:
        tags = tags.filter(family__family_id=family_id)
    all_tuples |= {(t.xpos, t.ref, t.alt, t.family.family_id) for t in tags if t.project_tag.tag.lower() != 'excluded'}

    all_tuples = list(sorted(all_tuples))
    variants = get_variants_from_variant_tuples(project, all_tuples)
    return variants


def get_variants_with_notes_for_project(project):
    notes = VariantNote.objects.filter(project=project).order_by('-date_saved').select_related('family').only('xpos', 'alt', 'ref', 'family__family_id')
    note_tuples = {(n.xpos, n.ref, n.alt, n.family.family_id) for n in notes}
    note_tuples = sorted(list(note_tuples))
    variants = get_variants_from_variant_tuples(project, note_tuples)
    return variants


def get_variants_by_tag(project, tag_slug, family_id=None):
    project_tag = ProjectTag.objects.get(project=project, tag=tag_slug)
    if family_id is not None:
        tags = VariantTag.objects.filter(project_tag=project_tag, family__family_id=family_id)
    else:
        tags = VariantTag.objects.filter(project_tag=project_tag)
    tags = tags.select_related('family').only('xpos', 'alt', 'ref', 'family__family_id')
    for t in tags:
        print("Looking up tag: " + str(t))

    tag_tuples = {(t.xpos, t.ref, t.alt, t.family.family_id) for t in tags}
    tag_tuples = sorted(list(tag_tuples))
    variants = get_variants_from_variant_tuples(project, tag_tuples)
    return variants


def get_causal_variants_for_project(project):
    variant_t_list = [(v.xpos, v.ref, v.alt, v.family.family_id) for v in CausalVariant.objects.filter(family__project=project)]
    variants = []
    for xpos, ref, alt, family_id in variant_t_list:
        variant = get_datastore(project).get_single_variant(
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
