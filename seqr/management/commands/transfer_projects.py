from bson import json_util
import json
import logging
import pymongo
import random
from tqdm import tqdm

import settings
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from guardian.shortcuts import assign_perm

from reference_data.models import HumanPhenotypeOntology, GENOME_BUILD_GRCh37
from seqr.views import phenotips_api
from xbrowse_server.base.models import \
    Project, \
    Family, \
    FamilyGroup, \
    Individual, \
    VariantNote, \
    ProjectTag, \
    VariantTag, \
    ProjectCollaborator, \
    ReferencePopulation

from seqr.models import \
    Project as SeqrProject, \
    Family as SeqrFamily, \
    Individual as SeqrIndividual, \
    VariantTagType as SeqrVariantTagType, \
    VariantTag as SeqrVariantTag, \
    VariantNote as SeqrVariantNote, \
    SequencingSample as SeqrSequencingSample, \
    Dataset as SeqrDataset, \
    LocusList, \
    CAN_EDIT, CAN_VIEW

logger = logging.getLogger(__name__)

# switching to python3.6 will make this unnecessary as built-in python dictionaries will be ordered
from collections import OrderedDict, defaultdict
class OrderedDefaultDict(OrderedDict, defaultdict):
    def __init__(self, default_factory=None, *args, **kwargs):
        super(OrderedDefaultDict, self).__init__(*args, **kwargs)
        self.default_factory = default_factory


class Command(BaseCommand):
    help = 'Transfer projects to the new seqr schema'

    def add_arguments(self, parser):
        parser.add_argument('--dont-connect-to-phenotips', help='dont retrieve phenotips internal id and latest data', action='store_true')
        parser.add_argument('-w', '--wgs-projects', help='text file that lists WGS project-ids - one per line')

        parser.add_argument('project_id', nargs="*", help='Project(s) to transfer. If not specified, defaults to all projects.')

    def handle(self, *args, **options):
        """transfer project"""
        connect_to_phenotips = not options['dont_connect_to_phenotips']
        project_ids_to_process = options['project_id']

        counters = OrderedDefaultDict(int)

        # reset all models
        SeqrProject.objects.all().delete()
        SeqrFamily.objects.all().delete()
        SeqrIndividual.objects.all().delete()
        SeqrVariantTagType.objects.all().delete()
        SeqrVariantTag.objects.all().delete()
        SeqrVariantNote.objects.all().delete()
        SeqrSequencingSample.objects.all().delete()
        SeqrDataset.objects.all().delete()

        if project_ids_to_process:
            projects = Project.objects.filter(project_id__in=project_ids_to_process)
            logging.info("Processing %s projects" % len(projects))
        else:
            projects = Project.objects.filter(
                ~Q(project_id__contains="DEPRECATED") &
                ~Q(project_name__contains="DEPRECATED") &
                ~Q(project_id__istartswith="temp") &
                ~Q(project_id__istartswith="test_")
            )
            logging.info("Processing all %s projects" % len(projects))

        wgs_project_ids = {}
        if options['wgs_projects']:
            with open(options['wgs_projects']) as f:
                wgs_project_ids = {line.strip().lower() for line in f if len(line.strip()) > 0}

        for source_project in tqdm(projects, unit=" projects"):
            counters['source_projects'] += 1

            # compute sequencing_type for this project
            project_id_lowercase = source_project.project_id.lower()
            if "wgs" in project_id_lowercase or "genome" in project_id_lowercase or project_id_lowercase in wgs_project_ids:
                sequencing_type = SeqrDataset.SEQUENCING_TYPE_WGS
                counters['wgs_projects'] += 1
            elif "rna-seq" in project_id_lowercase:
                sequencing_type = SeqrDataset.SEQUENCING_TYPE_RNA
                counters['rna_projects'] += 1
            else:
                sequencing_type = SeqrDataset.SEQUENCING_TYPE_WES
                counters['wes_projects'] += 1

            # transfer Project data
            new_project, project_created = transfer_project(source_project)
            if project_created: counters['projects_created'] += 1

            # transfer Families and Individuals
            source_family_id_to_new_family = {}
            for source_family in Family.objects.filter(project=source_project):
                new_family, family_created = transfer_family(
                    source_family, new_project)
                if family_created: counters['families_created'] += 1

                source_family_id_to_new_family[source_family.id] = new_family

                for source_individual in Individual.objects.filter(family=source_family):

                    new_individual, individual_created, phenotips_data_retrieved = transfer_individual(
                        source_individual, new_family, new_project, connect_to_phenotips
                    )

                    if individual_created: counters['individuals_created'] += 1
                    if phenotips_data_retrieved: counters['individuals_data_retrieved_from_phenotips'] += 1

                    vcf_files = [f for f in source_individual.vcf_files.all()]
                    vcf_path = None
                    if len(vcf_files) > 0:
                        # get the most recent VCF file (the one with the highest primary key
                        vcf_files_max_pk = max([f.pk for f in vcf_files])
                        vcf_path = [f.file_path for f in vcf_files if f.pk == vcf_files_max_pk][0]

                    if vcf_path:
                        new_dataset, dataset_created = get_or_create_dataset(
                            new_project,
                            dataset_path=vcf_path,
                            sequencing_type=sequencing_type
                        )

                        sample, sample_created = get_or_create_sample(
                            source_individual,
                            new_dataset,
                            new_individual,
                        )

                    if sample_created: counters['samples_created'] += 1

            # TODO family groups, cohorts
            for source_variant_tag_type in ProjectTag.objects.filter(project=source_project):
                new_variant_tag_type, created = get_or_create_variant_tag_type(
                    source_variant_tag_type, new_project)

                for source_variant_tag in VariantTag.objects.filter(project_tag=source_variant_tag_type):
                    new_family = source_family_id_to_new_family.get(source_variant_tag.family.id if source_variant_tag.family else None)
                    new_variant_tag, variant_tag_created = get_or_create_variant_tag(
                        source_variant_tag,
                        new_family,
                        new_variant_tag_type
                    )

                    if variant_tag_created: counters['variant_tags_created'] += 1

            for source_variant_note in VariantNote.objects.filter(project=source_project):
                new_family = source_family_id_to_new_family.get(source_variant_note.family.id if source_variant_note.family else None)

                new_variant_note, variant_note_created = get_or_create_variant_note(
                    source_variant_note,
                    new_project,
                    new_family
                )

                if variant_note_created:   counters['variant_notes_created'] += 1

        # TODO TravisCI
        # TODO create README: how to load data
        # TODO create new data loading scripts
        # TODO load coverage, readviz

        logger.info("Done")
        logger.info("Stats: ")
        for k, v in counters.items():
            logger.info("  %s: %s" % (k, v))


def transfer_project(source_project):
    """Transfers the given project and returns the new project"""

    # create project
    new_project, created = SeqrProject.objects.get_or_create(
        name=(source_project.project_name or source_project.project_id).strip(),
        created_date=source_project.created_date,
        deprecated_project_id=source_project.project_id.strip(),
    )

    new_project.description = source_project.description
    for p in source_project.private_reference_populations.all():
        new_project.custom_reference_populations.add(p)

    if source_project.project_id not in settings.PROJECTS_WITHOUT_PHENOTIPS:
        new_project.is_phenotips_enabled = True
        new_project.phenotips_user_id = source_project.project_id
    else:
        new_project.is_phenotips_enabled = False

    if source_project.project_id in settings.PROJECTS_WITH_MATCHMAKER:
        new_project.is_mme_enabled = True
        new_project.mme_primary_data_owner = settings.MME_PATIENT_PRIMARY_DATA_OWNER[source_project.project_id]
    else:
        new_project.is_mme_enabled = False

    new_project.save()

    # grant gene list CAN_VIEW permissions to project collaborators
    for source_gene_list in source_project.gene_lists.all():
        try:
            new_list = LocusList.objects.get(
                created_by=source_gene_list.owner,
                name=source_gene_list.name or source_gene_list.slug
            )
        except ObjectDoesNotExist as e:
            raise Exception('LocusList "%s" not found. Please run `python manage.py transfer_gene_lists`' % (
                source_gene_list.name or source_gene_list.slug))
        assign_perm(user_or_group=new_project.can_view_group, perm=CAN_VIEW, obj=new_list)

    # add collaborators to new_project.can_view_group and/or can_edit_group
    for collaborator in ProjectCollaborator.objects.filter(project=source_project):
        if collaborator.collaborator_type == 'manager':
            new_project.can_edit_group.user_set.add(collaborator.user)
            new_project.can_view_group.user_set.add(collaborator.user)
        elif collaborator.collaborator_type == 'collaborator':
            new_project.can_view_group.user_set.add(collaborator.user)
        else:
            raise ValueError("Unexpected collaborator_type: %s" % collaborator.collaborator_type)

    return new_project, created


def transfer_family(source_family, new_project):
    """Transfers the given family and returns the new family"""
    #new_project.created_date.microsecond = random.randint(0, 10**6 - 1)

    new_family, created = SeqrFamily.objects.get_or_create(
        project=new_project,
        family_id=source_family.family_id,
        display_name=source_family.family_name or source_family.family_id,
        created_date=new_project.created_date,  #.replace(microsecond=random.randint(0, 10**6 - 1))
        description=source_family.short_description,
        pedigree_image = source_family.pedigree_image,
        analysis_status = source_family.analysis_status,
        analysis_summary = source_family.analysis_summary_content,
        analysis_notes = source_family.about_family_content,
        causal_inheritance_mode = source_family.causal_inheritance_mode,
        internal_case_review_notes = source_family.internal_case_review_notes,
        internal_case_review_brief_summary = source_family.internal_case_review_brief_summary,
    )


    #new_family.internal_analysis_status =
    return new_family, created


def transfer_individual(source_individual, new_family, new_project, connect_to_phenotips):
    """Transfers the given Individual and returns the new Individual"""
    new_individual, created = SeqrIndividual.objects.get_or_create(
        family=new_family,
        individual_id=source_individual.indiv_id,
        display_name=source_individual.nickname,
        created_date=source_individual.created_date, #.replace(microsecond=random.randint(0, 10**6 - 1))
        maternal_id  = source_individual.maternal_id,
        paternal_id  = source_individual.paternal_id,
        sex          = source_individual.gender,
        affected     = source_individual.affected,
        case_review_status = source_individual.case_review_status,
        phenotips_eid      = source_individual.phenotips_id,
        phenotips_data     = source_individual.phenotips_data,
    )

    #new_individual.case_review_requested_info =

    # transfer PhenoTips data
    phenotips_data_retrieved = False
    if connect_to_phenotips and new_project.is_phenotips_enabled:
        _update_individual_phenotips_data(new_project, new_individual)
        phenotips_data_retrieved = True

    # transfer MME data
    if new_project.is_mme_enabled:
        mme_data_for_individual = list(
            settings.SEQR_ID_TO_MME_ID_MAP.find(
                {'seqr_id': new_individual.individual_id}
            ).sort(
                'insertion_date', pymongo.DESCENDING
            )
        )

        if mme_data_for_individual:
            submitted_data = mme_data_for_individual[0]['submitted_data']
            if submitted_data:
                new_individual.mme_submitted_data = json.dumps(submitted_data, default=json_util.default)
                new_individual.mme_id = submitted_data['patient']['id']
                new_individual.save()

    return new_individual, created, phenotips_data_retrieved


def _update_individual_phenotips_data(project, individual):
    """Update the phenotips_data and phenotips_patient_id fields for the given Individual

    Args:
        project (Model): Project model
        individual (Model): Individual model
    """
    latest_phenotips_data = phenotips_api.get_patient_data(
        project,
        individual.phenotips_eid,
        is_external_id=True
    )

    if 'features' in latest_phenotips_data:
        for feature in latest_phenotips_data['features']:
            hpo_id = feature['id']
            try:
                feature['category'] = HumanPhenotypeOntology.objects.get(hpo_id=hpo_id).category_id
            except ObjectDoesNotExist as e:
                logging.error("project %s, individual %s: %s not found in HPO table" % (project, individual, hpo_id))

    individual.phenotips_data = json.dumps(latest_phenotips_data)
    individual.phenotips_patient_id = latest_phenotips_data['id']  # internal id
    individual.save()


def get_or_create_sample(source_individual, new_dataset, new_individual):
    """Creates and returns a new SequencingSample based on the provided models."""

    new_sample, created = SeqrSequencingSample.objects.get_or_create(
        dataset=new_dataset,
        sample_id=(source_individual.vcf_id or source_individual.indiv_id).strip(),
        created_date=new_individual.created_date,

        individual_id=source_individual.indiv_id.strip(),
        sample_status=source_individual.coverage_status,
        bam_path=source_individual.bam_file_path,
        #picard fields=
    )

    new_individual.sequencing_samples.add(new_sample)

    return new_sample, created


def get_or_create_dataset(new_project, dataset_path, sequencing_type):
    new_dataset, created = SeqrDataset.objects.get_or_create(
        name=new_project.name,
        description=new_project.description,
        created_date=new_project.created_date,
        sequencing_type=sequencing_type,
    )

    if dataset_path is not None:
        new_dataset.path = dataset_path
        new_dataset.save()
    # TODO populate dataset is_loaded, load time

    if created:
        # dataset permissions - handled same way as for gene lists, except - since dataset currently
        # can't be shared with more than one project, allow dataset metadata to be edited by users
        # with project CAN_EDIT permissions
        assign_perm(user_or_group=new_project.can_edit_group, perm=CAN_EDIT, obj=new_dataset)
        assign_perm(user_or_group=new_project.can_view_group, perm=CAN_VIEW, obj=new_dataset)



    return new_dataset, created


def get_or_create_variant_tag_type(source_variant_tag_type, new_project):

    new_variant_tag_type, created = SeqrVariantTagType.objects.get_or_create(
        project=new_project,
        name=source_variant_tag_type.tag,
        description=source_variant_tag_type.title,
        color=source_variant_tag_type.color,
    )

    return new_variant_tag_type, created


def get_or_create_variant_tag(source_variant_tag, new_family, new_variant_tag_type):
    try:
        # seqr allowed a user to tag the same variant multiple times, so check if
        created = False
        new_variant_tag = SeqrVariantTag.objects.get(
            variant_tag_type=new_variant_tag_type,
            genome_build_id=GENOME_BUILD_GRCh37,
            xpos_start=source_variant_tag.xpos,
            xpos_end=source_variant_tag.xpos,
            ref=source_variant_tag.ref,
            alt=source_variant_tag.alt,
            family=new_family,
        )

        new_variant_tag.search_parameters = source_variant_tag.search_url
        new_variant_tag.save()
    except ObjectDoesNotExist as e:
        created = True
        new_variant_tag=SeqrVariantTag.objects.create(
            created_date=source_variant_tag.date_saved,
            created_by=source_variant_tag.user,
            variant_tag_type=new_variant_tag_type,
            genome_build_id=GENOME_BUILD_GRCh37,
            xpos_start=source_variant_tag.xpos,
            xpos_end=source_variant_tag.xpos,
            ref=source_variant_tag.ref,
            alt=source_variant_tag.alt,
            family=new_family,
            #gene_id=,
            #transcript_id=, # TODO update gene_id, transcript_id, molecular_consequence
            #molecular_consequence=
        )


    return new_variant_tag, created


def get_or_create_variant_note(source_variant_note, new_project, new_family):

    new_variant_note, created = SeqrVariantNote.objects.get_or_create(
        created_date=source_variant_note.date_saved,
        created_by=source_variant_note.user,
        project=new_project,
        note=source_variant_note.note,
        genome_build_id=GENOME_BUILD_GRCh37,
        xpos_start=source_variant_note.xpos,
        xpos_end=source_variant_note.xpos,
        ref=source_variant_note.ref,
        alt=source_variant_note.alt,
        search_parameters=source_variant_note.search_url,
        family=new_family,
        #gene_id=,
        #transcript_id=, # TODO update gene_id, transcript_id, molecular_consequence
        #molecular_consequence=,
    )

    return new_variant_note, created