"""
APIs for retrieving, updating, creating, and deleting Individual records
"""

from __future__ import unicode_literals

import logging

from seqr.models import Sample, IgvSample, Individual
from seqr.views.utils.pedigree_image_utils import update_pedigree_images

logger = logging.getLogger(__name__)

_SEX_TO_EXPORTED_VALUE = dict(Individual.SEX_LOOKUP)
_SEX_TO_EXPORTED_VALUE['U'] = ''

__AFFECTED_TO_EXPORTED_VALUE = dict(Individual.AFFECTED_STATUS_LOOKUP)
__AFFECTED_TO_EXPORTED_VALUE['U'] = ''


def delete_individuals(project, individual_guids):
    """Delete one or more individuals

    Args:
        project (object): Django ORM model for project
        individual_guids (list): GUIDs of individuals to delete

    Returns:
        list: Family objects for families with deleted individuals
    """

    individuals_to_delete = Individual.objects.filter(
        family__project=project, guid__in=individual_guids)

    Sample.objects.filter(individual__family__project=project, individual__guid__in=individual_guids).delete()
    IgvSample.objects.filter(individual__family__project=project, individual__guid__in=individual_guids).delete()

    families = {individual.family for individual in individuals_to_delete}

    individuals_to_delete.delete()

    update_pedigree_images(families)

    families_with_deleted_individuals = list(families)

    return families_with_deleted_individuals


def get_parsed_feature(feature):
    optional_fields = ['notes', 'qualifiers']
    feature_json = {'id': feature['id']}

    for field in optional_fields:
        if field in feature:
            feature_json[field] = feature[field]

    return feature_json
