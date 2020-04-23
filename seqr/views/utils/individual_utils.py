"""
APIs for retrieving, updating, creating, and deleting Individual records
"""

import logging

from seqr.models import Sample, IgvSample, Individual
from seqr.views.utils.pedigree_image_utils import update_pedigree_images
from seqr.views.utils.phenotips_utils import delete_phenotips_patient, PhenotipsException


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

    families = {}
    for individual in individuals_to_delete:
        families[individual.family.family_id] = individual.family

        # delete phenotips records
        try:
            delete_phenotips_patient(project, individual)
        except (PhenotipsException, ValueError) as e:
            logger.error("Error: couldn't delete patient from phenotips: {} {} ({})".format(
                individual.phenotips_eid, individual, e))

    individuals_to_delete.delete()

    update_pedigree_images(families.values())

    families_with_deleted_individuals = list(families.values())

    return families_with_deleted_individuals


def _user_to_string(user):
    """Takes a Django User object and returns a string representation"""
    if not user:
        return ''

    return user.email or user.username
