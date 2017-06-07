from bson import json_util
import json
import logging
import pymongo
from tqdm import tqdm
import settings


from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Q
from guardian.shortcuts import assign_perm

from reference_data.models import GENOME_BUILD_GRCh37
from seqr.views.apis import phenotips_api
from seqr.views.apis.phenotips_api import _update_individual_phenotips_data
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
    Sample as SeqrSample, \
    SampleBatch as SeqrSampleBatch, \
    LocusList, \
    CAN_EDIT, CAN_VIEW, ModelWithGUID

from xbrowse_server.mall import get_datastore, get_annotator


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
        parser.add_argument('--reset-all-models', help='This flag causes all records to be cleared from the seqr schema\'s Project, Family, and Individual models before transferring data', action='store_true')
        parser.add_argument('--dont-connect-to-phenotips', help='dont retrieve phenotips internal id and latest data', action='store_true')
        parser.add_argument('-w', '--wgs-projects', help='text file that lists WGS project-ids - one per line')

        parser.add_argument('project_id', nargs="*", help='Project(s) to transfer. If not specified, defaults to all projects.')

    def handle(self, *args, **options):
        """transfer project"""
        reset_all_models = options['reset_all_models']
        connect_to_phenotips = not options['dont_connect_to_phenotips']
        project_ids_to_process = options['project_id']

        counters = OrderedDefaultDict(int)

        if reset_all_models:
            print("Dropping all records from SeqrProject, SeqrFamily, SeqrIndividual")
            SeqrIndividual.objects.all().delete()
            SeqrFamily.objects.all().delete()
            SeqrProject.objects.all().delete()

        # reset models that'll be regenerated
        SeqrVariantTagType.objects.all().delete()
        SeqrVariantTag.objects.all().delete()
        SeqrVariantNote.objects.all().delete()
        SeqrSample.objects.all().delete()
        SeqrSampleBatch.objects.all().delete()


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

        updated_seqr_project_guids = set()
        updated_seqr_family_guids = set()
        updated_seqr_individual_guids = set()

        for source_project in tqdm(projects, unit=" projects"):
            counters['source_projects'] += 1

            print("Project: " + source_project.project_id)


            # compute sample_type for this project
            project_names = ("%s|%s" % (source_project.project_id, source_project.project_name)).lower()
            if "wgs" in project_names or "genome" in source_project.project_id.lower() or source_project.project_id.lower() in wgs_project_ids:
                sample_type = SeqrSampleBatch.SAMPLE_TYPE_WGS
                counters['wgs_projects'] += 1
            elif "rna-seq" in project_names:
                sample_type = SeqrSampleBatch.SAMPLE_TYPE_RNA
                counters['rna_projects'] += 1
            else:
                sample_type = SeqrSampleBatch.SAMPLE_TYPE_WES
                counters['wes_projects'] += 1


            # transfer Project data
            new_project, project_created = transfer_project(source_project)
            updated_seqr_project_guids.add(new_project.guid)
            if project_created: counters['projects_created'] += 1

            # transfer Families and Individuals
            source_family_id_to_new_family = {}
            for source_family in Family.objects.filter(project=source_project):
                new_family, family_created = transfer_family(
                    source_family, new_project)

                updated_seqr_family_guids.add(new_family.guid)

                if family_created: counters['families_created'] += 1

                source_family_id_to_new_family[source_family.id] = new_family

                for source_individual in Individual.objects.filter(family=source_family):

                    new_individual, individual_created, phenotips_data_retrieved = transfer_individual(
                        source_individual, new_family, new_project, connect_to_phenotips
                    )

                    updated_seqr_individual_guids.add(new_individual.guid)

                    if individual_created: counters['individuals_created'] += 1
                    if phenotips_data_retrieved: counters['individuals_data_retrieved_from_phenotips'] += 1


                    if source_individual.combined_individuals_info:
                        combined_individuals_info = json.loads(source_individual.combined_individuals_info)
                        """
                        combined_individuals_info json is expected to look like:
                        {
                            'WES' : {
                                'project_id': from_project.project_id,
                                'family_id': from_f.family_id,
                                'indiv_id': from_i.indiv_id
                            },
                            'WGS' : {
                                'project_id': from_project.project_id,
                                'family_id': from_f.family_id,
                                'indiv_id': from_i.indiv_id
                            },
                            'RNA' : {
                                'project_id': from_project.project_id,
                                'family_id': from_f.family_id,
                                'indiv_id': from_i.indiv_id
                            },
                        }
                        """
                        for i, sample_type_i, combined_individuals_info_i in enumerate(combined_individuals_info.items()):
                            source_project_i = Project.objects.get(project_id=combined_individuals_info_i['project_id'])
                            #source_family_i = Project.objects.get(project_id=combined_individuals_info_i['family_id'])
                            source_individual_i = Project.objects.get(project_id=combined_individuals_info_i['indiv_id'])

                            create_sample_records(sample_type_i, source_project_i, source_individual_i, new_project, new_individual, counters)
                    else:
                        create_sample_records(sample_type, source_project, source_individual, new_project, new_individual, counters)
                        #combined_families_info.update({from_project_datatype: {'project_id': from_project.project_id, 'family_id': from_f.family_id}})

            # TODO family groups, cohorts
            for source_variant_tag_type in ProjectTag.objects.filter(project=source_project).order_by('order'):
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


        # delete projects that are in SeqrIndividual table, but not in BaseProject table
        if not project_ids_to_process:
            for indiv in SeqrIndividual.objects.all():
                if indiv.guid not in updated_seqr_individual_guids:
                    print("Deleting SeqrIndividual: %s" % indiv)
                    indiv.delete()

            # delete projects that are in SeqrFamily table, but not in BaseProject table
            for f in SeqrFamily.objects.all():
                if f.guid not in updated_seqr_family_guids:
                    print("Deleting SeqrFamily: %s" % f)
                    f.delete()

            # delete projects that are in SeqrProject table, but not in BaseProject table
            for p in SeqrProject.objects.all():
                if p.guid not in updated_seqr_project_guids:
                    while True:
                        i = raw_input('Delete SeqrProject %s? [Y/n]' % p.guid)
                        if i == 'Y':
                            p.delete()
                        else:
                            print("Keeping %s .." % p.guid)
                        break

        logger.info("Done")
        logger.info("Stats: ")
        for k, v in counters.items():
            logger.info("  %s: %s" % (k, v))


def create_sample_records(sample_type, source_project, source_individual, new_project, new_individual, counters):

    vcf_files = [f for f in source_individual.vcf_files.all()]
    vcf_path = None
    if len(vcf_files) > 0:
        # get the most recent VCF file (the one with the highest primary key
        vcf_files_max_pk = max([f.pk for f in vcf_files])
        vcf_path = [f.file_path for f in vcf_files if f.pk == vcf_files_max_pk][0]

    if vcf_path:
        new_sample_batch, sample_batch_created = get_or_create_sample_batch(
            new_project,
            sample_type=sample_type,
            genome_build_id=GENOME_BUILD_GRCh37,
        )

        sample, sample_created = get_or_create_sample(
            source_individual,
            new_sample_batch,
            new_individual,
        )

        sample.deprecated_base_project = source_project
        sample.save()

        if sample_created: counters['samples_created'] += 1


def update_model_field(model, field_name, new_value):
    """Updates the given field if the new value is different from it's current value.
    Args:
        model: django ORM model
        field_name: name of field to update
        new_value: The new value to set the field to
    """
    if not hasattr(model, field_name):
        raise ValueError("model %s doesn't have the field %s" % (model, field_name))

    if getattr(model, field_name) != new_value:
        setattr(model, field_name, new_value)
        if field_name != 'phenotips_data':
            print("Setting %s.%s = %s" % (model.__class__.__name__.encode('utf-8'), field_name.encode('utf-8'), unicode(new_value).encode('utf-8')))
        model.save()


def transfer_project(source_project):
    """Transfers the given project and returns the new project"""

    # create project
    new_project, created = SeqrProject.objects.get_or_create(
        deprecated_project_id=source_project.project_id.strip(),
    )
    if created:
        print("Created SeqrSample", new_project)

    update_model_field(new_project, 'guid', new_project._compute_guid()[:ModelWithGUID.MAX_GUID_SIZE])
    update_model_field(new_project, 'name', (source_project.project_name or source_project.project_id).strip())
    update_model_field(new_project, 'description', source_project.description)
    update_model_field(new_project, 'deprecated_last_accessed_date', source_project.last_accessed_date)

    for p in source_project.private_reference_populations.all():
        new_project.custom_reference_populations.add(p)

    if source_project.project_id not in settings.PROJECTS_WITHOUT_PHENOTIPS:
        update_model_field(new_project, 'is_phenotips_enabled', True)
        update_model_field(new_project, 'phenotips_user_id', source_project.project_id)
    else:
        new_project.is_phenotips_enabled = False

    if source_project.project_id in settings.PROJECTS_WITH_MATCHMAKER:
        update_model_field(new_project, 'is_mme_enabled', True)
        update_model_field(new_project, 'mme_primary_data_owner', settings.MME_PATIENT_PRIMARY_DATA_OWNER[source_project.project_id])
    else:
        new_project.is_mme_enabled = False

    new_project.save()

    # grant gene list CAN_VIEW permissions to project collaborators
    for source_gene_list in source_project.gene_lists.all():
        try:
            locus_list = LocusList.objects.get(
                created_by=source_gene_list.owner,
                name=source_gene_list.name or source_gene_list.slug,
                is_public=source_gene_list.is_public,
            )
        except ObjectDoesNotExist as e:
            raise Exception('LocusList "%s" not found. Please run `python manage.py transfer_gene_lists`' % (
                source_gene_list.name or source_gene_list.slug))
        except MultipleObjectsReturned as e:
            logger.error("Multiple LocusLists with  owner '%s' and name '%s'" % (
                source_gene_list.owner, (source_gene_list.name or source_gene_list.slug))
            )
            continue

        assign_perm(user_or_group=new_project.can_view_group, perm=CAN_VIEW, obj=locus_list)

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

    new_family, created = SeqrFamily.objects.get_or_create(project=new_project, family_id=source_family.family_id)
    if created:
        print("Created SeqrSample", new_family)

    update_model_field(new_family, 'display_name', source_family.family_name or source_family.family_id)
    update_model_field(new_family, 'description', source_family.short_description)
    update_model_field(new_family, 'pedigree_image', source_family.pedigree_image)
    update_model_field(new_family, 'analysis_notes', source_family.about_family_content)
    update_model_field(new_family, 'analysis_summary', source_family.analysis_summary_content)
    update_model_field(new_family, 'causal_inheritance_mode', source_family.causal_inheritance_mode)
    update_model_field(new_family, 'analysis_status', source_family.analysis_status)
    update_model_field(new_family, 'internal_case_review_notes', source_family.internal_case_review_notes)
    update_model_field(new_family, 'internal_case_review_summary', source_family.internal_case_review_summary)

    return new_family, created


def transfer_individual(source_individual, new_family, new_project, connect_to_phenotips):
    """Transfers the given Individual and returns the new Individual"""

    new_individual, created = SeqrIndividual.objects.get_or_create(family=new_family, individual_id=source_individual.indiv_id)
    if created:
        print("Created SeqrSample", new_individual)

    update_model_field(new_individual, 'created_date', source_individual.created_date)
    update_model_field(new_individual, 'maternal_id',  source_individual.maternal_id)
    update_model_field(new_individual, 'paternal_id',  source_individual.paternal_id)
    update_model_field(new_individual, 'sex',  source_individual.gender)
    update_model_field(new_individual, 'affected',  source_individual.affected)
    update_model_field(new_individual, 'display_name', source_individual.nickname or source_individual.indiv_id)
    #update_model_field(new_individual, 'notes',  source_individual.notes) <-- notes exist only in the new SeqrIndividual schema. other_notes was never really used
    update_model_field(new_individual, 'case_review_status',  source_individual.case_review_status)
    update_model_field(new_individual, 'case_review_status_accepted_for',  source_individual.case_review_status_accepted_for)
    update_model_field(new_individual, 'phenotips_eid',  source_individual.phenotips_id)
    update_model_field(new_individual, 'phenotips_data',  source_individual.phenotips_data)

    # transfer PhenoTips data
    phenotips_data_retrieved = False
    if connect_to_phenotips and new_project.is_phenotips_enabled:
        _retrieve_and_update_individual_phenotips_data(new_project, new_individual)
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


def _retrieve_and_update_individual_phenotips_data(project, individual):
    """Retrieve and update the phenotips_data and phenotips_patient_id fields for the given Individual

    Args:
        project (Model): Project model
        individual (Model): Individual model
    """
    try:
        latest_phenotips_json = phenotips_api.get_patient_data(
            project,
            individual.phenotips_eid,
            is_external_id=True
        )

    except phenotips_api.PhenotipsException as e:
        print("Couldn't retrieve latest data from phenotips for %s: %s" % (individual, e))
        return

    _update_individual_phenotips_data(individual, latest_phenotips_json)


def get_or_create_sample(source_individual, new_sample_batch, new_individual):
    """Creates and returns a new Sample based on the provided models."""

    loaded_date = look_up_loaded_date(source_individual)

    new_sample, created = SeqrSample.objects.get_or_create(
        sample_batch=new_sample_batch,
        sample_id=(source_individual.vcf_id or source_individual.indiv_id).strip(),
        created_date=new_individual.created_date,

        individual_id=source_individual.indiv_id.strip(),
        sample_status=source_individual.coverage_status,

        source_file_path=source_individual.bam_file_path,
    )

    new_sample.deprecated_base_project=source_individual.family.project
    new_sample.is_loaded=source_individual.is_loaded()

    new_sample.loaded_date=loaded_date
    new_sample.save()

    new_individual.samples.add(new_sample)

    return new_sample, created


def get_or_create_sample_batch(new_project, sample_type, genome_build_id):
    new_sample_batch, created = SeqrSampleBatch.objects.get_or_create(
        name=new_project.name,
        description=new_project.description,
        created_date=new_project.created_date,
        sample_type=sample_type,
        genome_build_id=genome_build_id,
    )

    if created:
        # SampleBatch permissions - handled same way as for gene lists, except - since SampleBatch
        # currently can't be shared with more than one project, allow SampleBatch metadata to be
        # edited by users with project CAN_EDIT permissions
        assign_perm(user_or_group=new_project.can_edit_group, perm=CAN_EDIT, obj=new_sample_batch)
        assign_perm(user_or_group=new_project.can_view_group, perm=CAN_VIEW, obj=new_sample_batch)

    return new_sample_batch, created


def get_or_create_variant_tag_type(source_variant_tag_type, new_project):

    new_variant_tag_type, created = SeqrVariantTagType.objects.get_or_create(
        project=new_project,
        name=source_variant_tag_type.tag,
        description=source_variant_tag_type.title,
        color=source_variant_tag_type.color,
        order=source_variant_tag_type.order,
        is_built_in=(source_variant_tag_type.order is not None),
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
        # TODO populate variant_annotation, variant_genotypes

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
        ) # TODO populate variant_annotation, variant_genotypes

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
    )  # TODO populate variant_annotation, variant_genotypes

    return new_variant_note, created


def look_up_loaded_date(source_individual):
    """Retrieve the data-loaded time for the given individual"""

    # decode data loaded time
    loaded_date = None
    try:
        datastore = get_datastore(source_individual.project.project_id)
        family_collection = datastore._get_family_collection(
            source_individual.project.project_id,
            source_individual.family.family_id
        )
        if not family_collection:
            logger.error("mongodb family collection not found for %s %s" % (
                source_individual.project.project_id,
                source_individual.family.family_id))
            return
        record = family_collection.find_one()
        if record:
            loaded_date = record['_id'].generation_time
            logger.info("%s data-loaded date: %s" % (source_individual.project.project_id, loaded_date))
    except Exception as e:
        logger.error('Unable to look up loaded_date for %s' % str(source_individual))
        logger.error(e)

    return loaded_date

