"""API for (re)generating a static pedigree image using HaploPainter

1. Writing out a slightly-specialized .ped file for just this family
2. Running the HaploPainter1.043.pl tool on this .ped file to generate a .png image
3. If the pedigree image was generated successfully, set this image as the family.pedigree_image file.
4. Delete the .ped file and other temp files.

"""
from __future__ import unicode_literals

import collections
import logging
import os
import random
import tempfile

from django.core.files import File

from seqr.models import Individual
from seqr.views.utils.orm_to_json_utils import _get_json_for_individuals
from settings import BASE_DIR

logger = logging.getLogger(__name__)


def update_pedigree_images(families, project_guid=None):
    """Regenerate pedigree image for one or more families

    Args:
         families (list): List of Django ORM models for families to update.
    """

    for family in families:
        _update_pedigree_image(family, project_guid=project_guid)


def _get_parsed_individuals(family, project_guid=None):
    """Uses HaploPainter to (re)generate the pedigree image for the given family.

    Args:
         family (object): seqr Family model.
    """
    individuals = Individual.objects.filter(family=family)

    if len(individuals) < 2:
        family.pedigree_image = None
        family.save()
        return None

    # convert individuals to json
    individual_records = {
        individual['individualId']: individual for individual in
        _get_json_for_individuals(individuals, project_guid=project_guid, family_guid=family.guid)
    }

    # compute a map of parent ids to list of children
    parent_ids_to_children_map = collections.defaultdict(list)
    for individual_id, individual_json in individual_records.items():
        if not individual_json['paternalId'] and not individual_json['maternalId']:
            continue
        key = (individual_json['paternalId'], individual_json['maternalId'])
        parent_ids_to_children_map[key].append(individual_json)

    # generate placeholder individuals as needed, since HaploPainter1.043.pl doesn't support families with only 1 parent
    for ((paternal_id, maternal_id), children) in parent_ids_to_children_map.items():

        for parent_id_key, parent_id, sex in [
            ('paternalId', paternal_id, 'M'),
            ('maternalId', maternal_id, 'F')
        ]:

            if not parent_id or parent_id not in individual_records:
                placeholder_parent_id = 'placeholder_%s'% _random_string(10)
                placeholder_parent_json = {
                    'individualId': placeholder_parent_id,  # fake indiv id
                    'paternalId': '',
                    'maternalId': '',
                    'sex': sex,
                    'affected': 'INVISIBLE',  # use a special value to tell HaploPainter to draw this individual as '?'
                }

                for child_json in children:
                    child_json[parent_id_key] = placeholder_parent_id

                individual_records[placeholder_parent_id] = placeholder_parent_json

    # convert to FAM file values
    SEX_TO_FAM_FILE_VALUE = {"M": "1", "F": "2", "U": "0"}
    AFFECTED_STATUS_TO_FAM_FILE_VALUE = {"A": "2", "N": "1", "U": "0", "INVISIBLE": "9"}   # HaploPainter1.043.pl has been modified to hide individuals with affected-status='9'

    return {
        individual_id: {
            'individualId': individual_id,
            'paternalId': individual_json['paternalId'] or '0',
            'maternalId': individual_json['maternalId'] or '0',
            'sex': SEX_TO_FAM_FILE_VALUE[individual_json['sex']],
            'affected': AFFECTED_STATUS_TO_FAM_FILE_VALUE[individual_json['affected']],
        } for individual_id, individual_json in individual_records.items()
    }


def _update_pedigree_image(family, project_guid=None):
    """Uses HaploPainter to (re)generate the pedigree image for the given family.

    Args:
         family (object): seqr Family model.
    """

    individual_records = _get_parsed_individuals(family, project_guid)
    if not individual_records:
        return

    # run HaploPainter to generate the pedigree image
    png_file_path = os.path.join(tempfile.gettempdir(), "pedigree_image_%s.png" % _random_string(10))
    family_id = family.family_id
    with tempfile.NamedTemporaryFile('w', suffix=".fam", delete=True) as fam_file:

        # columns: family, individual id, paternal id, maternal id, sex, affected
        for i in individual_records.values():
            row = [family_id] + [i[key] for key in ['individualId', 'paternalId', 'maternalId', 'sex', 'affected']]
            fam_file.write("\t".join(row).encode('UTF-8'))
            fam_file.write("\n")
        fam_file.flush()

        fam_file_path = fam_file.name
        haplopainter_command = "perl " + os.path.join(BASE_DIR, "seqr/management/commands/HaploPainter1.043.pl")
        haplopainter_command += " -b -outformat png -pedfile {fam_file_path} -family {family_id} -outfile {png_file_path}".format(
            fam_file_path=fam_file_path, family_id=family_id, png_file_path=png_file_path)
        os.system(haplopainter_command)

    if not os.path.isfile(png_file_path):
        logger.error("Failed to generated pedigree image for family: %s" % family_id)
        family.pedigree_image = None
        family.save()
        return

    _save_pedigree_image_file(family, png_file_path)

    os.remove(png_file_path)


def _save_pedigree_image_file(family, png_file_path):
    with open(png_file_path) as pedigree_image_file:
        family.pedigree_image.save(os.path.basename(png_file_path), File(pedigree_image_file))
        family.save()


def _random_string(size=10):
    return str(random.randint(10**size, 10**(size+1) - 1))
