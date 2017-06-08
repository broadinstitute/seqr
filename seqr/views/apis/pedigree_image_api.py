"""API for (re)generating a static pedigree image using HaploPainter

1. Writing out a slightly-specialized .ped file for just this family
2. Running the HaploPainter1.043.pl tool on this .ped file to generate a .png image
3. If the pedigree image was generated successfully, set this image as the family.pedigree_image file.
4. Delete the .ped file and other temp files.

"""
import collections
import logging
import os
import random
import tempfile

from django.core.files import File
from seqr.models import Individual
from seqr.views.utils.orm_to_json_utils import _get_json_for_individual
from settings import BASE_DIR

from xbrowse_server.base.models import Family as BaseFamily

logger = logging.getLogger(__name__)


def update_pedigree_image(family):
    """Uses HaploPainter to (re)generate the pedigree image for the given family.

    Args:
         family (object): seqr Family model.
    """
    family_id = family.family_id
    individuals = Individual.objects.filter(family=family)
    if len(individuals) < 2:
        _clear_pedigree_image(family)
        return

    # convert individuals to json
    individual_records = {}
    for i in individuals:
        individual_records[i.individual_id] = _get_json_for_individual(i)
        individual_records[i.individual_id]['familyId'] = i.family.family_id


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
                    'familyId': family_id,
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
    for individual_json in individual_records.values():
        if not individual_json['paternalId']:
            individual_json['paternalId'] = '0'
        if not individual_json['maternalId']:
            individual_json['maternalId'] = '0'
        individual_json['sex'] = SEX_TO_FAM_FILE_VALUE[individual_json['sex']]
        individual_json['affected'] = AFFECTED_STATUS_TO_FAM_FILE_VALUE[individual_json['affected']]

    # run HaploPainter to generate the pedigree image
    png_file_path = os.path.join(tempfile.gettempdir(), "pedigree_image_%s.png" % _random_string(10))
    with tempfile.NamedTemporaryFile('w', suffix=".fam", delete=True) as fam_file:

        # columns: family, individual id, paternal id, maternal id, sex, affected
        for i in individual_records.values():
            row = [i[key] for key in ['familyId', 'individualId', 'paternalId', 'maternalId', 'sex', 'affected']]
            fam_file.write("\t".join(row))
            fam_file.write("\n")
        fam_file.flush()

        fam_file_path = fam_file.name
        haplopainter_command = "/usr/bin/perl " + os.path.join(BASE_DIR, "xbrowse_server/base/management/commands/HaploPainter1.043.pl")
        haplopainter_command += " -b -outformat png -pedfile %(fam_file_path)s -family %(family_id)s -outfile %(png_file_path)s" % locals()
        os.system(haplopainter_command)

    if not os.path.isfile(png_file_path):
        logger.error("Failed to generated pedigree image for family: %s" % family_id)
        _clear_pedigree_image(family)
        return

    _save_pedigree_image_file(family, png_file_path)

    os.remove(png_file_path)


def _save_pedigree_image_file(family, png_file_path):
    with open(png_file_path) as pedigree_image_file:
        family.pedigree_image.save(os.path.basename(png_file_path), File(pedigree_image_file))
        family.save()

    # update deprecated model
    try:
        base_families = BaseFamily.objects.filter(family=family, project__project_id=family.project.deprecated_project_id)
        if base_families:
            base_family = base_families[0]
            base_family.pedigree_image.save(os.path.basename(png_file_path), File(pedigree_image_file))
            base_family.save()
    except Exception as e:
        logger.error("Couldn't sync pedigree image to BaseFamily: " + str(e))

    #print("saving "+os.path.abspath(os.path.join(settings.MEDIA_ROOT, family.pedigree_image.name)))


def _clear_pedigree_image(family):
    family.pedigree_image = None
    family.save()

    try:
        base_families = BaseFamily.objects.filter(family=family, project__project_id=family.project.deprecated_project_id)
        if base_families:
            base_family = base_families[0]
            base_family.pedigree_image = None
            base_family.save()
    except Exception as e:
        logger.error("Couldn't clear pedigree image from BaseFamily: " + str(e))


def _random_string(size=10):
    return str(random.randint(10**size, 10**(size+1) - 1))