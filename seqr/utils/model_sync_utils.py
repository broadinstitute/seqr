import json
import logging
from django.contrib.auth.models import User

from seqr.models import SavedVariant as SeqrSavedVariant
from seqr.utils.xpos_utils import get_xpos
from xbrowse_server.api.utils import add_extra_info_to_variants_project
from xbrowse_server.mall import get_reference
from xbrowse_server.base.models import Project as BaseProject
from xbrowse_server.base.lookups import get_variants_from_variant_tuples


def get_or_create_saved_variant(xpos=None, ref=None, alt=None, family=None, project=None, **kwargs):
    if not project:
        project = family.project
    saved_variant, _ = SeqrSavedVariant.objects.get_or_create(
        xpos_start=xpos,
        xpos_end=xpos + len(ref) - 1,
        ref=ref,
        alt=alt,
        family=family,
        project=project,
    )
    if not saved_variant.saved_variant_json:
        try:
            saved_variants_json = retrieve_saved_variants_json(project, [(xpos, ref, alt, family.family_id)])
            if len(saved_variants_json):
                update_saved_variant_json(saved_variant, saved_variants_json[0])
        except Exception as e:
            logging.error("Unable to retrieve variant annotations for %s (%s, %s, %s): %s" % (family, xpos, ref, alt, e))
    return saved_variant


def retrieve_saved_variants_json(project, variant_tuples):
    project_id = project.deprecated_project_id
    xbrowse_project = BaseProject.objects.get(project_id=project_id)
    user = User.objects.filter(is_staff=True).first()  # HGMD annotations are only returned for staff users

    variants = get_variants_from_variant_tuples(xbrowse_project, variant_tuples, user=user)
    add_extra_info_to_variants_project(get_reference(), xbrowse_project, variants, add_populations=True)
    return [variant.toJSON() for variant in variants]


def update_saved_variant_json(saved_variant, saved_variant_json):
    extras = saved_variant_json.get('extras', {})
    saved_variant.genome_version = extras.get('genome_version', saved_variant.genome_version)
    if not saved_variant.lifted_over_genome_version:
        saved_variant.lifted_over_genome_version = '37' if saved_variant.genome_version == '38' else '38'
    if not saved_variant.lifted_over_xpos_start:
        coords_field = 'grch%s_coords' % saved_variant.lifted_over_genome_version
        coords = extras.get(coords_field, '').split('-')
        if len(coords) > 1:
            saved_variant.lifted_over_xpos_start = get_xpos(coords[0], coords[1])

    saved_variant.saved_variant_json = json.dumps(saved_variant_json)
    saved_variant.save()