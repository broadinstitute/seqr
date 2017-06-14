from collections import OrderedDict, defaultdict
import logging

from django.core.management.base import BaseCommand
from guardian.shortcuts import assign_perm, get_objects_for_group

from seqr.management.commands.utils.combine_utils import choose_one
from seqr.models import Project, Family, Individual, VariantTagType, VariantTag, VariantNote, Sample, SampleBatch, LocusList, CAN_VIEW, CAN_EDIT

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Transfer projects to the new seqr schema'

    def add_arguments(self, parser):
        parser.add_argument('--project-name', help='new project name')
        parser.add_argument('--project-description', help='new project description')
        parser.add_argument('project_id_a', help='Data will be combined into this project. It this project doesn\'t exist, it will be created.')
        parser.add_argument('project_id_b', help='Data will be parsed from this project, and this project will be deleted')

    def handle(self, *args, **options):
        """transfer project"""

        raise NotImplementedError("This script is not complete. combine_base_projects.py and update_projects_in_new_schema.py are being used instead - likely until the transition to the new schema is complete")


        print("Starting")
        counter = defaultdict(int)

        destination_project, created = Project.objects.get_or_create(deprecated_project_id=options['project_id_a'])
        source_project = Project.objects.get(deprecated_project_id=options['project_id_b'])

        if created:
            print("Destination project created: " + str(destination_project))

        # transfer Project metadata
        transfer_project_info(source_project, destination_project)

        if options['project_name']:
            destination_project.name = options['project_name']
        if options['project_description']:
            destination_project.description = options['project_description']
        destination_project.save()

        # transfer Families and Individuals
        for source_family in Family.objects.filter(project=source_project):
            destination_families = Family.objects.filter(
                project=destination_project,
                family_id=source_family.family_id
            )

            if not destination_families:
                # just move the family to the destination project. Its descendent individuals, samples and sample batches will move along with it.
                source_family.project = destination_project
                source_family.save()
                counter['reparented source_family'] += 1
                continue

            # the destination project contains a family with the same family_id as the source_family
            destination_family = destination_families[0]
            transfer_family_info(source_family, destination_family)
            counter['copied attributes from source_family'] += 1

            for source_individual in Individual.objects.filter(family=source_family):
                destination_individuals = Individual.objects.filter(
                    family=destination_family,
                    individual_id=source_individual.individual_id
                )
                if not destination_individuals:
                    # just move the individual to the destination family. Its descendent samples and sample batches will move along with it.
                    source_individual.family = destination_family
                    source_individual.save()
                    counter['reparented source_individual'] += 1
                    continue

                # the destination family contains an individual with the same individual_id as the source project
                destination_individual = destination_individuals[0]
                transfer_individual_info(source_individual, destination_individual)
                counter['copied attributes from source_individual'] += 1

                # Assume samples and sample batches are not duplicated between the 2 projects

        for source_variant_tag_type in VariantTagType.objects.filter(project=source_project):
            # if the same VariantTagType doesn't already exist in the destination project,
            # move the tag type to the destination project. Its descendent VariantTags will move along with it.
            destination_variant_tag_types = VariantTagType.objects.filter(
                project=destination_project,
                name=source_variant_tag_type.name
            )
            if not destination_variant_tag_types:
                source_variant_tag_type.project = destination_project
                counter['reparented variant_tag_type'] += 1
                source_variant_tag_type.save()
                continue

            destination_variant_tag_type = destination_variant_tag_types[0]
            destination_variant_tag_type.description = choose_one(destination_variant_tag_type, 'description', source_variant_tag_type.description, destination_variant_tag_type.description)
            destination_variant_tag_type.color = choose_one(destination_variant_tag_type, 'color', source_variant_tag_type.color, destination_variant_tag_type.color)
            destination_variant_tag_type.save()
            counter['copied attributes from variant_tag_type'] += 1

            for source_variant_tag in VariantTag.objects.filter(variant_tag_type=source_variant_tag_type):
                destination_variant_tag, created = VariantTag.objects.get_or_create(
                    variant_tag_type=destination_variant_tag_type,
                    xpos_start=source_variant_tag.xpos_start,
                    xpos_end=source_variant_tag.xpos_end,
                    ref=source_variant_tag.ref,
                    alt=source_variant_tag.alt,
                )
                if created:
                    counter['VariantTag created'] += 1

                if source_variant_tag.family and not destination_variant_tag.family:
                    destination_variant_tag.family = source_variant_tag.family
                destination_variant_tag.search_parameters = choose_one(destination_variant_tag, 'search_parameters', source_variant_tag.search_parameters, destination_variant_tag.search_parameters)
                counter['updated VariantTag'] += 1
                destination_variant_tag.save()

        for source_variant_note in VariantNote.objects.filter(project=source_project):
            # if the same VariantNote doesn't already exist in the destination project,
            # move the note to the destination project
            if not VariantNote.objects.filter(
                    project=destination_project,
                    note=source_variant_note.note,
                    created_by=source_variant_note.created_by):
                source_variant_note.project = destination_project
                counter['saved VariantNote'] += 1
                source_variant_note.save()

        # all data has been transferred to the destination so delete the source project
        print("Deleting project " + str(source_project) )
        for source_family in Family.objects.filter(project=source_project):
            for source_individual in Individual.objects.filter(family=source_family):
                source_individual.delete()
            source_family.delete()
        source_project.delete()

        for source_variant_tag_type in VariantTagType.objects.filter(project=source_project):
            for source_variant_tag in VariantTag.objects.filter(variant_tag_type=source_variant_tag_type):
                source_variant_tag.delete()
            source_variant_tag_type.delete()

        for source_variant_note in VariantNote.objects.filter(project=source_project):
            source_variant_note.delete()

        for key, value in counter.items():
            print("%15s: %s" % (key, value))


def transfer_project_info(source_project, destination_project):
    """Transfers the given project"""

    # destination_project.name - keep project name as is
    # destination_project.deprecated_project_id - keep as is
    destination_project.description = choose_one(destination_project, "description", source_project.description, destination_project.description)

    # update permissions - transfer source project users
    for user in source_project.can_edit_group.user_set.all():
        destination_project.can_edit_group.user_set.add(user)

    for user in source_project.can_view_group.user_set.all():
        destination_project.can_view_group.user_set.add(user)

    # update permissions - transfer source project gene lists
    for locus_list in get_objects_for_group(source_project.can_view_group, CAN_VIEW, LocusList):
        assign_perm(user_or_group=destination_project.can_view_group, perm=CAN_VIEW, obj=locus_list)

    # update permissions - transfer SampleBatches
    for sample_batch in SampleBatch.objects.filter(sample__individual__family__project=source_project):
        assign_perm(user_or_group=destination_project.can_edit_group, perm=CAN_EDIT, obj=sample_batch)
        assign_perm(user_or_group=destination_project.can_view_group, perm=CAN_VIEW, obj=sample_batch)

    # transfer custom reference populations
    for p in source_project.custom_reference_populations.all():
        destination_project.custom_reference_populations.add(p)

    # phenotips and MME
    destination_project.is_phenotips_enabled = True

    # TODO check for each individual whether the source project has phenotips data
    destination_project.phenotips_user_id = source_project.phenotips_user_id

    destination_project.is_mme_enabled = source_project.is_mme_enabled or destination_project.is_mme_enabled
    destination_project.mme_primary_data_owner = choose_one(destination_project, "mme_primary_data_owner",
        source_project.mme_primary_data_owner,
        destination_project.mme_primary_data_owner
    )

    destination_project.save()


def transfer_family_info(source_family, destination_family):
    """Transfers the given family and returns the new family"""

    print("Transferring " + str(source_family) + " to " + str(destination_family))
    assert source_family.family_id == destination_family.family_id

    destination_family.description = choose_one(
        destination_family, 'description', source_family.description, destination_family.description
    )

    #destination_family.project - keep this since source_family.project will be deleted
    destination_family.display_name = choose_one(
        destination_family, "display_name", source_family.display_name, destination_family.display_name
    )

    #new_family.pedigree_image - keep this as is, it will need to be regenerated anyway

    destination_family.analysis_notes = choose_one(
        destination_family, 'analysis_notes', source_family.analysis_notes, destination_family.analysis_notes
    )
    destination_family.analysis_summary = choose_one(
        destination_family, 'analysis_summary', source_family.analysis_summary, destination_family.analysis_summary
    )
    destination_family.causal_inheritance_mode = choose_one(
        destination_family, 'causal_inheritance_mode', source_family.causal_inheritance_mode, destination_family.causal_inheritance_mode
    )

    destination_family.analysis_status = choose_one(
        destination_family, 'analysis_status', source_family.analysis_status, destination_family.analysis_status
    )
    destination_family.internal_case_review_notes = choose_one(
        destination_family, 'internal_case_review_notes', source_family.internal_case_review_notes, destination_family.internal_case_review_notes
    )

    destination_family.internal_case_review_summary = choose_one(
        destination_family, 'internal_case_review_summary', source_family.internal_case_review_summary, destination_family.internal_case_review_summary
    )

    destination_family.internal_analysis_status = choose_one(
        destination_family, 'internal_analysis_status', source_family.internal_analysis_status, destination_family.internal_analysis_status
    )

    destination_family.save()


def transfer_individual_info(source_individual, destination_individual):
    """Transfers the given Individual and returns the new Individual"""

    assert source_individual.individual_id == destination_individual.individual_id

    destination_individual.maternal_id = choose_one(destination_individual, 'maternal_id', source_individual.maternal_id, destination_individual.maternal_id)
    destination_individual.paternal_id = choose_one(destination_individual, 'paternal_id', source_individual.paternal_id, destination_individual.paternal_id)

    destination_individual.sex = choose_one(destination_individual, 'sex', source_individual.sex, destination_individual.sex)
    destination_individual.affected = choose_one(destination_individual, 'affected', source_individual.affected, destination_individual.affected)

    destination_individual.display_name = choose_one(destination_individual, 'display_name', source_individual.display_name, destination_individual.display_name)

    destination_individual.case_review_status = choose_one(destination_individual, 'case_review_status', source_individual.case_review_status, destination_individual.case_review_status)

    # if PhenoTips HPO terms entered for both individuals, prompt user to choose
    destination_individual.phenotips_data = choose_one(
        destination_individual,
        'phenotips_data',
        source_individual.phenotips_data,
        destination_individual.phenotips_data
    )

    destination_individual.mme_id = choose_one(destination_individual, 'mme_id', source_individual.mme_id, destination_individual.mme_id)
    destination_individual.mme_submitted_data = choose_one(destination_individual, 'mme_submitted_data', source_individual.mme_submitted_data, destination_individual.mme_submitted_data)

    destination_individual.save()
