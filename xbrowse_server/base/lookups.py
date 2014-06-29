from django.conf import settings

from xbrowse_server.base.models import FamilySearchFlag


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
        variant = settings.DATASTORE.get_single_variant(
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

def get_saved_variants_for_project(project):
    """
    Returns:
        List of variants that were saved in this project, with family_id and project_id in variant.extras
    """

    search_flags = FamilySearchFlag.objects.filter(family__project=project).order_by('-date_saved')
    familyvariant_tuples = {(v.xpos, v.ref, v.alt, v.family.family_id) for v in search_flags}
    variants = []
    for familyvariant_t in familyvariant_tuples:
        variant = settings.DATASTORE.get_single_variant(
            project.project_id,
            familyvariant_t[3],
            familyvariant_t[0],
            familyvariant_t[1],
            familyvariant_t[2]
        )
        if variant:
            variant.set_extra('family_id', familyvariant_t[3])
            variant.set_extra('project_id', project.project_id)
            variants.append(variant)

    return variants