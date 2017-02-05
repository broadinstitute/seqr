

import logging

from django.core.management.base import BaseCommand
from guardian.shortcuts import assign_perm, get_objects_for_group

from seqr.models import Project, Family, Individual, VariantTagType, VariantTag, VariantNote, SequencingSample, Dataset, LocusList, CAN_VIEW, CAN_EDIT

logger = logging.getLogger(__name__)

# switching to python3.6 will make dictionaries ordered by default
from collections import OrderedDict, defaultdict
class OrderedDefaultDict(OrderedDict, defaultdict):
    def __init__(self, default_factory=None, *args, **kwargs):
        #in python3 you can omit the args to super
        super(OrderedDefaultDict, self).__init__(*args, **kwargs)
        self.default_factory = default_factory


class Command(BaseCommand):
    help = 'Transfer projects to the new seqr schema'

    def add_arguments(self, parser):
        parser.add_argument('--project-name', help='new project name')
        parser.add_argument('--project-description', help='new project description')
        parser.add_argument('project_id_a', help='Data will be combined into this project.')
        parser.add_argument('project_id_b', help='Data will be parsed from this project, and this project will be deleted')

    def handle(self, *args, **options):
        """transfer project"""

        destination_project = Project.objects.get(deprecated_project_id=options['project_id_a'])
        source_project = Project.objects.get(deprecated_project_id=options['project_id_b'])

        # transfer Project data
        transfer_project_data(source_project, destination_project)

        if options['project_name']:
            destination_project.name = options['project_name']
        if options['project_description']:
            destination_project.name = options['project_description']
        destination_project.save()

        # transfer Families and Individuals
        for source_family in Family.objects.filter(project=source_project):
            destination_family = Family.objects.filter(
                project=destination_project,
                family_id=source_project.family_id
            )

            if not destination_family:
                # just move the family to the destination project. Its descendent individuals, samples and datasets will move along with it.
                source_family.project = destination_project
                source_family.save()
                continue

            # the destination project contains a family with the same family_id as the source_family
            destination_family = destination_family[0]
            transfer_family_data(source_family, destination_family)

            for source_individual in Individual.objects.filter(family=source_family):
                destination_individual = Individual.objects.filter(
                    family=destination_family,
                    individual_id=source_individual.individual_id
                )
                if not destination_individual:
                    # just move the individual to the destination family. Its descendent samples and datasets will move along with it.
                    source_individual.family = destination_family
                    source_individual.save()
                    continue

                # the destination family contains an individual with the same individual_id as the source project
                transfer_individual_data(source_individual, destination_individual)

                # Assume samples and datasets are not duplicated between the 2 projects

        for source_variant_tag_type in VariantTagType.objects.filter(project=source_project):
            # if the same VariantTagType doesn't already exist in the destination project,
            # move the tag type to the destination project. Its descendent VariantTags will move along with it.
            if not VariantTagType.objects.filter(
                    project=destination_project,
                    name=source_variant_tag_type.name):
                source_variant_tag_type.project = destination_project
                source_variant_tag_type.save()

        for source_variant_note in VariantNote.objects.filter(project=source_project):
            # if the same VariantNote doesn't already exist in the destination project,
            # move the note to the destination project
            if not VariantNote.objects.filter(
                    project=destination_project,
                    note=source_variant_note.note,
                    created_by=source_variant_note.created_by):
                source_variant_note.project = destination_project
                source_variant_note.save()


def choose_one(model, field_name, version_a, version_b):
    if version_a == version_b:
        return version_a
    if version_a is None:
        return version_b
    if version_b is None:
        return version_a

    while True:
        i = input("select %s.%s (enter a or b, or "
                  "cs to concatenate with space in between, or "
                  "cn to concatenate with new line):\n   a: %s\n   b: %s\n[a/b/cs/cn]: " % (
            model, field_name, version_a, version_b))
        if i == 'a':
            result = version_a
        elif i == 'b':
            result = version_b
        elif i == 'cs' or i == 'cn':
            result = "%s%s%s" % (version_a, ' ' if i == 'cs' else '\n', version_b)
        else:
            continue
        logger.info("setting %s.%s = %s" % (model, field_name, result))


def transfer_project_data(source_project, destination_project):
    """Transfers the given project"""

    # destination_project.name - keep project name as is
    # destination_project.deprecated_project_id - keep as is
    destination_project.description = choose_one(destination_project, "description", source_project.description, destination_project.description)

    # update permissions - transfer source project users
    for user in source_project.can_edit_group.objects.all():
        destination_project.can_edit_group.add(user)

    for user in source_project.can_view_group.objects.all():
        destination_project.can_view_group.add(user)

    # update permissions - transfer source project gene lists
    for locus_list in get_objects_for_group(source_project.can_view_group, CAN_VIEW, LocusList):
        assign_perm(user_or_group=destination_project.can_view_group, perm=CAN_VIEW, obj=locus_list)

    # update permissions - transfer datasets
    for dataset in Dataset.objects.filter(sequencingsample__individual__family__project=source_project):
        assign_perm(user_or_group=destination_project.can_edit_group, perm=CAN_EDIT, obj=dataset)
        assign_perm(user_or_group=destination_project.can_view_group, perm=CAN_VIEW, obj=dataset)

    # transfer custom reference populations
    for p in source_project.private_reference_populations.all():
        destination_project.custom_reference_populations.add(p)

    # phenotips and MME
    destination_project.is_phenotips_enabled = True
    #destination_project.phenotips_user_id  - will later check for each individual is source project has any data worth keeping

    destination_project.is_mme_enabled = source_project.is_mme_enabled or destination_project.is_mme_enabled
    destination_project.mme_primary_data_owner = choose_one(destination_project, "mme_primary_data_owner",
        source_project.mme_primary_data_owner,
        destination_project.mme_primary_data_owner
    )

    destination_project.save()


def transfer_family_data(source_family, destination_family):
    """Transfers the given family and returns the new family"""

    assert source_family.family_id == destination_family.family_id

    #destination_family.project - keep this since source_family.project will be deleted
    destination_family.name = choose_one(
        destination_family, "name", source_family.name, destination_family.name
    )

    destination_family.description = choose_one(
        destination_family, 'description', source_family.description, destination_family.description
    )

    #new_family.pedigree_image - keep this as is

    destination_family.analysis_notes = choose_one(
        destination_family, 'analysis_notes', source_family.analysis_notes, destination_family.analysis_notes
    )
    destination_family.analysis_summary = choose_one(
        destination_family, 'analysis_summary', source_family.analysis_summary, destination_family.analysis_summary
    )
    destination_family.causal_inheritance_mode = choose_one(
        destination_family, 'causal_inheritance_mode', source_family.causal_inheritance_mode, destination_family.causal_inheritance_mode
    )
    if source_family.analysis_status != 'Q':
        destination_family.analysis_status = choose_one(
            destination_family, 'analysis_status', source_family.analysis_status, destination_family.analysis_status
        )

    # new_family.internal_analysis_status
    destination_family.internal_case_review_notes = choose_one(
        destination_family, 'internal_case_review_notes', source_family.internal_case_review_notes, destination_family.internal_case_review_notes
    )

    destination_family.internal_case_review_brief_summary = choose_one(
        destination_family, 'internal_case_review_brief_summary', source_family.internal_case_review_brief_summary, destination_family.internal_case_review_brief_summary
    )

    destination_family.save()


def transfer_individual_data(source_individual, destination_individual):
    """Transfers the given Individual and returns the new Individual"""

    assert source_individual.individual_id == destination_individual.individual_id

    destination_individual.maternal_id = choose_one(destination_individual, 'maternal_id', source_individual.maternal_id, destination_individual.maternal_id)
    destination_individual.paternal_id = choose_one(destination_individual, 'paternal_id', source_individual.paternal_id, destination_individual.paternal_id)

    destination_individual.sex = choose_one(destination_individual, 'sex', source_individual.sex, destination_individual.sex)
    destination_individual.affected = choose_one(destination_individual, 'affected', source_individual.affected, destination_individual.affected)

    destination_individual.display_name = choose_one(destination_individual, 'display_name', source_individual.display_name, destination_individual.display_name)

    destination_individual.case_review_status = choose_one(destination_individual, 'case_review_status', source_individual.case_review_status, destination_individual.case_review_status)
    #new_individual.case_review_requested_info =

    # if PhenoTips HPO terms entered for both individuals, prompt user to choose
    features = choose_one(
        destination_individual, 'phenotips_data features',
        source_individual.phenotips_data.get('features'),
        destination_individual.phenotips_data.get('features')
    )

    if features == source_individual.phenotips_data.get('features'):
        destination_individual.phenotips_patient_id = source_individual.phenotips_patient_id
        destination_individual.phenotips_eid  = source_individual.phenotips_eid
        destination_individual.phenotips_data = source_individual.phenotips_data

    destination_individual.mme_id = choose_one(destination_individual, 'mme_id', source_individual.mme_id, destination_individual.mme_id)
    destination_individual.mme_submitted_data = choose_one(destination_individual, 'mme_submitted_data', source_individual.mme_submitted_data, destination_individual.mme_submitted_data)

    destination_individual.save()
