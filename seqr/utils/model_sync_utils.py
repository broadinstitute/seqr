import json
import logging
from bs4 import BeautifulSoup
from django.contrib.auth.models import User

from seqr.models import SavedVariant as SeqrSavedVariant
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
    saved_variant.saved_variant_json = json.dumps(saved_variant_json)
    saved_variant.save()


def convert_html_to_plain_text(html_string, remove_line_breaks=False):
    """Returns string after removing all HTML markup.

    Args:
        html_string (str): string with HTML markup
        remove_line_breaks (bool): whether to also remove line breaks and extra white space from string
    """
    if not html_string:
        return ''

    text = BeautifulSoup(html_string, "html.parser").get_text()

    # remove empty lines as well leading and trailing space on non-empty lines
    if remove_line_breaks:
        text = ' '.join(line.strip() for line in text.splitlines() if line.strip())

    return text