import json
import logging
from django.contrib.auth.models import User

from seqr.models import SavedVariant
from xbrowse_server.api.utils import add_extra_info_to_variants_project
from xbrowse_server.mall import get_reference
from xbrowse_server.base.models import Project as BaseProject
from xbrowse_server.base.lookups import get_variants_from_variant_tuples


def get_or_create_saved_variant(xpos=None, ref=None, alt=None, family=None, project=None, **kwargs):
    if not project:
        project = family.project
    saved_variant, _ = SavedVariant.objects.get_or_create(
        xpos_start=xpos,
        xpos_end=xpos + len(ref) - 1,
        ref=ref,
        alt=alt,
        family=family,
        project=project,
    )
    if not saved_variant.saved_variant_json:
        try:
            saved_variants_json = _retrieve_saved_variants_json(project, [(xpos, ref, alt, family.family_id)], create_if_missing=True)
            if len(saved_variants_json):
                _update_saved_variant_json(saved_variant, saved_variants_json[0])
        except Exception as e:
            logging.error("Unable to retrieve variant annotations for %s (%s, %s, %s): %s" % (family, xpos, ref, alt, e))
    return saved_variant


def update_project_saved_variant_json(project):
    saved_variants = SavedVariant.objects.filter(project=project, family__isnull=False).select_related('family')
    saved_variants_map = {(v.xpos_start, v.ref, v.alt, v.family.family_id): v for v in saved_variants}

    variants_json = _retrieve_saved_variants_json(project, saved_variants_map.keys())

    for var in variants_json:
        saved_variant = saved_variants_map[(var['xpos'], var['ref'], var['alt'], var['extras']['family_id'])]
        _update_saved_variant_json(saved_variant, var)

    return variants_json


def _retrieve_saved_variants_json(project, variant_tuples, create_if_missing=False):
    project_id = project.deprecated_project_id
    xbrowse_project = BaseProject.objects.get(project_id=project_id)
    user = User.objects.filter(is_staff=True).first()  # HGMD annotations are only returned for staff users

    variants = get_variants_from_variant_tuples(xbrowse_project, variant_tuples, user=user)
    if not create_if_missing:
        variants = [var for var in variants if not var.get_extra('created_variant')]
    add_extra_info_to_variants_project(get_reference(), xbrowse_project, variants, add_populations=True)
    return [variant.toJSON() for variant in variants]


def _update_saved_variant_json(saved_variant, saved_variant_json):
    saved_variant.saved_variant_json = json.dumps(saved_variant_json)
    saved_variant.save()



