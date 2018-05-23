import json
import logging
from django.contrib.auth.models import User

from seqr.models import SavedVariant as SeqrSavedVariant
from xbrowse_server.api.utils import add_extra_info_to_variants_project
from xbrowse_server.mall import get_datastore, get_reference
from xbrowse_server.base.models import Project


def get_or_create_saved_variant(xpos=None, ref=None, alt=None, family=None, project=None, **kwargs):
    new_saved_variant, created = SeqrSavedVariant.objects.get_or_create(
        xpos_start=xpos,
        xpos_end=xpos + len(ref) - 1,
        ref=ref,
        alt=alt,
        family=family,
        project=project or family.project,
    )
    if not new_saved_variant.saved_variant_json:
        saved_variant_json = get_saved_variant_json(xpos, ref, alt, family, project)
        if saved_variant_json:
            new_saved_variant.saved_variant_json = saved_variant_json
            new_saved_variant.save()

    return new_saved_variant


def get_saved_variant_json(xpos, ref, alt, new_family, new_project):
    if new_family is None and new_project is None:
        return None

    project_id = new_project.deprecated_project_id if new_project else new_family.project.deprecated_project_id
    project = Project.objects.get(project_id=project_id)
    user = User.objects.filter(is_staff=True).first(),  # HGMD annotations are only returned for staff users
    try:
        variant_info = get_datastore(project).get_single_variant(
            project_id, new_family.family_id, xpos, ref, alt, user=user
        )
    except Exception as e:
        logging.error("Unable to retrieve variant annotations for %s (%s, %s, %s): %s" % (
            new_family, xpos, ref, alt, e))
        return None

    if variant_info:
        add_extra_info_to_variants_project(get_reference(), project, [variant_info], add_populations=True)
        variant_json = variant_info.toJSON()

        return json.dumps(variant_json)