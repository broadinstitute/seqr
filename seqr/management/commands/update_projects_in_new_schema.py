import logging
from tqdm import tqdm

from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Q
from guardian.shortcuts import assign_perm

from seqr.management.commands.transfer_mme_data import transfer_mme_submission_data
from seqr.views.utils.variant_utils import deprecated_get_or_create_saved_variant
from seqr.views.apis import phenotips_api
from seqr.views.apis.phenotips_api import _get_patient_data, _update_individual_phenotips_data
from xbrowse_server.base.models import \
    Project, \
    Family, \
    Individual, \
    VariantNote, \
    ProjectTag, \
    VariantTag, \
    VariantFunctionalData, \
    ProjectCollaborator, VCFFile, AnalysedBy

from seqr.models import \
    Project as SeqrProject, \
    Family as SeqrFamily, \
    Individual as SeqrIndividual, \
    VariantTagType as SeqrVariantTagType, \
    VariantTag as SeqrVariantTag, \
    VariantNote as SeqrVariantNote, \
    VariantFunctionalData as SeqrVariantFunctionalData, \
    Sample as SeqrSample, \
    LocusList, \
    FamilyAnalysedBy as SeqrAnalysedBy, \
    CAN_VIEW

from xbrowse_server.mall import get_datastore, get_annotator
from xbrowse_server.base.model_utils import _convert_xbrowse_kwargs_to_seqr_kwargs, find_matching_seqr_model, _create_seqr_model

logger = logging.getLogger(__name__)

# switching to python3.6 will make this unnecessary as built-in python dictionaries will be ordered
from collections import OrderedDict, defaultdict
class OrderedDefaultDict(OrderedDict, defaultdict):
    def __init__(self, default_factory=None, *args, **kwargs):
        super(OrderedDefaultDict, self).__init__(*args, **kwargs)
        self.default_factory = default_factory


DEBUG = False   # whether to ask before updating values


class Command(BaseCommand):
    help = 'Transfer projects to the new seqr schema'

    def add_arguments(self, parser):
        parser.add_argument('--reset-all-models', help='This flag causes all records to be cleared from the seqr schema\'s Project, Family, and Individual models before transferring data', action='store_true')
        parser.add_argument('--dont-connect-to-phenotips', help='dont retrieve phenotips internal id and latest data', action='store_true')
        parser.add_argument('project_id', nargs="*", help='Project(s) to transfer. If not specified, defaults to all projects.')

    def handle(self, *args, **options):
        """transfer project"""
        reset_all_models = options['reset_all_models']
        connect_to_phenotips = not options['dont_connect_to_phenotips']
        project_ids_to_process = options['project_id']
        
        counters = OrderedDefaultDict(int)

        #if reset_all_models:
        #    print("Dropping all records from SeqrProject, SeqrFamily, SeqrIndividual")
        #    SeqrIndividual.objects.all().delete()
        #    SeqrFamily.objects.all().delete()
        #    SeqrProject.objects.all().delete()

        # reset models that'll be regenerated
        #if not project_ids_to_process:
        #    SeqrSample.objects.all().delete()
        #    SeqrVariantTagType.objects.all().delete()
        #    SeqrVariantTag.objects.all().delete()
        #    SeqrVariantNote.objects.all().delete()



        if project_ids_to_process:
            projects = Project.objects.filter(project_id__in=project_ids_to_process)
            logging.info("Processing %s projects" % len(projects))
        else:
            projects = Project.objects.filter(
                ~Q(project_id__contains="DEPRECATED") &
                ~Q(project_name__contains="DEPRECATED") &
                ~Q(project_id__istartswith="temp") &
                ~Q(project_id__istartswith="test_") &
                ~Q(project_name__contains="DISABLED_")
            )
            logging.info("Processing all %s projects" % len(projects))
            project_ids_to_process = [p.project_id for p in projects]


        updated_seqr_project_guids = set()
        updated_seqr_family_guids = set()
        updated_seqr_individual_guids = set()

        core_variant_tag_type_names = [vtt.name for vtt in SeqrVariantTagType.objects.filter(project=None)]
        # If a core tag type exists with that name, delete any project-specific tag types
        _, deleted = SeqrVariantTagType.objects.filter(
            project__isnull=False,
            name__in=core_variant_tag_type_names,
        ).delete()
        for model, delete_count in deleted.items():
            print("=== deleted {} {} models with  core tag types".format(delete_count, model))

        for source_project in tqdm(projects, unit=" projects"):
            counters['source_projects'] += 1

            print("Project: " + source_project.project_id)

            # transfer Project data
            new_project, project_created = transfer_project(source_project)
            updated_seqr_project_guids.add(new_project.guid)
            if project_created: counters['projects_created'] += 1

            # transfer Families and Individuals
            source_family_id_to_new_family = {}
            for source_family in Family.objects.filter(project=source_project):
                new_family, family_created = transfer_family(source_family)

                updated_seqr_family_guids.add(new_family.guid)

                if family_created: counters['families_created'] += 1

                source_family_id_to_new_family[source_family.id] = new_family

                for source_individual in Individual.objects.filter(family=source_family):

                    new_individual, individual_created, phenotips_data_retrieved = transfer_individual(
                        source_individual, new_project, connect_to_phenotips
                    )

                    updated_seqr_individual_guids.add(new_individual.guid)

                    if individual_created: counters['individuals_created'] += 1
                    if phenotips_data_retrieved: counters['individuals_data_retrieved_from_phenotips'] += 1

                    create_sample_records(source_individual, new_individual, counters)

                for source_analysed_by in AnalysedBy.objects.filter(family=source_family):
                    new_analysed_by, analysed_by_created = transfer_analysed_by(source_analysed_by, new_family)

                    if analysed_by_created: counters['analysed_by_created'] += 1

            # transfer MME data
            if new_project.is_mme_enabled:
                num_transferred_mme_submissions, errors = transfer_mme_submission_data(new_project)
                for error in errors:
                    logger.error(error)
                counters['mme_submissions'] += num_transferred_mme_submissions

            # TODO family groups, cohorts
            for source_variant_tag_type in ProjectTag.objects.filter(project=source_project).order_by('order'):
                if source_variant_tag_type not in core_variant_tag_type_names:
                    _, created = get_or_create_variant_tag_type(source_variant_tag_type)
                    if created: counters['variant_tag_types_created'] += 1

                for source_variant_tag in VariantTag.objects.filter(project_tag=source_variant_tag_type):
                    new_family = source_family_id_to_new_family.get(source_variant_tag.family.id if source_variant_tag.family else None)
                    _, variant_tag_created = get_or_create_variant_tag(source_variant_tag, new_family)

                    if variant_tag_created: counters['variant_tags_created'] += 1

            for source_variant_functional_data in VariantFunctionalData.objects.filter(family__project=source_project):
                new_family = source_family_id_to_new_family.get(source_variant_functional_data.family.id)

                _, variant_functional_data_created = get_or_create_variant_functional_data(
                    source_variant_functional_data,
                    new_family,
                )

                if variant_functional_data_created:   counters['variant_functional_data_created'] += 1

            for source_variant_note in VariantNote.objects.filter(project=source_project):
                new_family = source_family_id_to_new_family.get(source_variant_note.family.id if source_variant_note.family else None)

                new_variant_note, variant_note_created = get_or_create_variant_note(
                    source_variant_note,
                    new_family,
                )

                if variant_note_created:   counters['variant_notes_created'] += 1


        for deprecated_project_id in project_ids_to_process:

            base_project = Project.objects.get(project_id=deprecated_project_id)

            # delete Tag type
            for seqr_variant_tag_type in SeqrVariantTagType.objects.filter(project__deprecated_project_id=deprecated_project_id):
                if not ProjectTag.objects.filter(
                    project=base_project,
                    tag=seqr_variant_tag_type.name,
                    title=seqr_variant_tag_type.description,
                    color=seqr_variant_tag_type.color,
                    order=seqr_variant_tag_type.order
                ):
                    seqr_variant_tag_type.delete()
                    print("--- deleting variant tag type: " + str(seqr_variant_tag_type))
                    counters['seqr_variant_tag_type_deleted'] += 1

            # delete Tag
            delete_count, _ = SeqrVariantTag.objects.filter(saved_variant__isnull=True).delete()
            counters['seqr_variant_tag_deleted'] += delete_count
            for seqr_variant_tag in SeqrVariantTag.objects.filter(saved_variant__project__deprecated_project_id=deprecated_project_id):

                if not VariantTag.objects.filter(
                        project_tag__project=base_project,
                        project_tag__tag=seqr_variant_tag.variant_tag_type.name,
                        #project_tag__title=seqr_variant_tag.variant_tag_type.description,
                        xpos=seqr_variant_tag.saved_variant.xpos_start,
                        ref=seqr_variant_tag.saved_variant.ref,
                        alt=seqr_variant_tag.saved_variant.alt,
                ):
                    seqr_variant_tag.delete()
                    print("--- deleting variant tag: " + str(seqr_variant_tag))
                    counters['seqr_variant_tag_deleted'] += 1

            # delete functional data tags
            delete_count, _ = SeqrVariantFunctionalData.objects.filter(saved_variant__isnull=True).delete()
            counters['seqr_variant_functional_data_deleted'] += delete_count
            for seqr_variant_functional_data in SeqrVariantFunctionalData.objects.filter(
                    saved_variant__project__deprecated_project_id=deprecated_project_id):

                if not VariantFunctionalData.objects.filter(
                        family__project=base_project,
                        functional_data_tag=seqr_variant_functional_data.functional_data_tag,
                        metadata=seqr_variant_functional_data.metadata,
                        xpos=seqr_variant_functional_data.saved_variant.xpos_start,
                        ref=seqr_variant_functional_data.saved_variant.ref,
                        alt=seqr_variant_functional_data.saved_variant.alt,
                ):
                    seqr_variant_functional_data.delete()
                    print("--- deleting variant tag: " + str(seqr_variant_functional_data))
                    counters['seqr_variant_tag_deleted'] += 1

            # delete Variant Note
            delete_count, _ = SeqrVariantNote.objects.filter(saved_variant__isnull=True).delete()
            counters['seqr_variant_note_deleted'] += delete_count
            for seqr_variant_note in SeqrVariantNote.objects.filter(saved_variant__project__deprecated_project_id=deprecated_project_id):

                if not VariantNote.objects.filter(
                    project=base_project,
                    note=seqr_variant_note.note,
                    xpos=seqr_variant_note.saved_variant.xpos_start,
                    ref=seqr_variant_note.saved_variant.ref,
                    alt=seqr_variant_note.saved_variant.alt,
                    date_saved=seqr_variant_note.last_modified_date,
                    user=seqr_variant_note.created_by,
                ):
                    print("--- deleting variant note: " + str(new_variant_note))
                    seqr_variant_note.delete()
                    counters['seqr_variant_note_deleted'] += 1

            for indiv in SeqrIndividual.objects.filter(family__project__deprecated_project_id=deprecated_project_id):
                if indiv.guid not in updated_seqr_individual_guids:
                    print("Deleting SeqrIndividual: %s" % indiv)
                    counters["deleted SeqrIndividuals"] += 1
                    indiv.sample_set.all().delete()
                    indiv.delete()

            # delete families that are in SeqrFamily table, but not in BaseProject table
            for f in SeqrFamily.objects.filter(project__deprecated_project_id=deprecated_project_id):
                if f.guid not in updated_seqr_family_guids:
                    print("--- deleting SeqrFamily: %s" % f)
                    counters["deleted SeqrFamilys"] += 1
                    f.delete()

            # if there's a set of samples without individuals
            for sample in SeqrSample.objects.filter(individual__isnull=True):
                print("--- deleting SeqrSample without indiv: %s" % sample)
                counters["deleted SeqrSample"] += 1
                sample.delete()

            # delete projects that are in SeqrProject table, but not in BaseProject table
            #for p in SeqrProject.objects.filter():
            #    if p.guid not in updated_seqr_project_guids:
            #        while True:
            #            i = raw_input('Delete SeqrProject %s? [Y/n]' % p.guid)
            #            if i == 'Y':
            #                p.delete()
            #            else:
            #                print("Keeping %s .." % p.guid)
            #            break

        # delete projects that are in SeqrProject table, but not in BaseProject table
        if not project_ids_to_process:
            all_project_ids = set([project.project_id for project in Project.objects.all()])
            for seqr_project in SeqrProject.objects.all():
                if seqr_project.deprecated_project_id not in all_project_ids:
                    #seqr_project.delete()
                    print("--- Deleting SeqrProject: %s ??" % seqr_project)

        logger.info("Done")
        logger.info("Stats: ")
        for k, v in counters.items():
            if v > 0:
                logger.info("  %s: %s" % (k, v))


def create_sample_records(source_individual, new_individual, counters):
    loaded_vcf_files = source_individual.vcf_files.filter(dataset_type=VCFFile.DATASET_TYPE_VARIANT_CALLS, loaded_date__isnull=False)
    for loaded_vcf_file in loaded_vcf_files:
        new_sample, sample_created = get_or_create_sample(
            source_individual,
            new_individual,
            sample_type=loaded_vcf_file.sample_type,
            dataset_type=SeqrSample.DATASET_TYPE_VARIANT_CALLS,
            elasticsearch_index=loaded_vcf_file.elasticsearch_index,
            dataset_file_path=loaded_vcf_file.file_path,
            sample_status=SeqrSample.SAMPLE_STATUS_LOADED if loaded_vcf_file else None,
            loaded_date=loaded_vcf_file.loaded_date,
        )

        if sample_created:
            counters['samples_created'] += 1
            logger.info("Created sample: " + str(new_sample.json()))

        if source_individual.bam_file_path:
            new_sample, sample_created = get_or_create_sample(
                source_individual,
                new_individual,
                sample_type=loaded_vcf_file.sample_type,
                dataset_type=SeqrSample.DATASET_TYPE_READ_ALIGNMENTS,
                elasticsearch_index=None,
                dataset_file_path=source_individual.bam_file_path,
                loaded_date=loaded_vcf_file.loaded_date,
                sample_status=SeqrSample.SAMPLE_STATUS_LOADED if loaded_vcf_file else None,
            )
            if sample_created:
                counters['samples_created'] += 1
                logger.info("Created alignment sample: " + str(new_sample.json()))


def look_up_vcf_loaded_date(vcf_path):
    vcf_record = get_annotator().get_vcf_file_from_annotator(vcf_path)
    if vcf_record is None:
        raise ValueError("Couldn't find loaded date for %s" % vcf_path)

    loaded_date = vcf_record['_id'].generation_time
    # logger.info("%s data-loaded date: %s" % (vcf_path, loaded_date))
    return loaded_date


def update_model_fields(model, xbrowse_model, xbrowse_fields):
    """Updates the given field if the new value is different from it's current value.
    Args:
        model: django ORM model
        field_name: name of field to update
        new_value: The new value to set the field to
    """
    original_values = {field_name: getattr(xbrowse_model, field_name) for field_name in xbrowse_fields}
    seqr_fields = _convert_xbrowse_kwargs_to_seqr_kwargs(xbrowse_model, **original_values)
    for field_name, new_value in seqr_fields.items():
        if getattr(model, field_name) != new_value:
            if DEBUG and field_name != 'phenotips_data':
                i = raw_input("Should %s.%s = %s\n instead of \n%s \n in %s ? [Y\n]" % (model.__class__.__name__.encode('utf-8'), field_name.encode('utf-8'), unicode(new_value).encode('utf-8'), getattr(model, field_name), str(model)))
                if i.lower() != "y":
                    print("ok, skipping.")
                    return

            setattr(model, field_name, new_value)
            if field_name != 'phenotips_data':
                print("Setting %s.%s = %s" % (model.__class__.__name__.encode('utf-8'), field_name.encode('utf-8'), unicode(new_value).encode('utf-8')))

    if hasattr(xbrowse_model, 'date_saved'):
        model.save(last_modified_date=getattr(xbrowse_model, 'date_saved'))
    else:
        model.save()


def transfer_project(source_project):
    """Transfers the given project and returns the new project"""

    new_project, created = safe_get_or_create(source_project)

    if created:
        print("Created SeqrProject", new_project)

    source_project.seqr_project = new_project
    source_project.save()

    update_model_fields(new_project, source_project, [
        'description', 'genome_version', 'is_phenotips_enabled', 'is_mme_enabled', 'mme_primary_data_owner',
        'mme_contact_url', 'mme_contact_institution', 'is_functional_data_enabled', 'last_accessed_date',
        'project_name', 'project_id', 'is_phenotips_enabled', 'phenotips_user_id'
    ])

    for p in source_project.private_reference_populations.all():
        new_project.custom_reference_populations.add(p)
    new_project.save()

    # grant gene list CAN_VIEW permissions to project collaborators
    for source_gene_list in source_project.gene_lists.all():
        try:
            locus_list = LocusList.objects.get(
                created_by=source_gene_list.owner,
                name=source_gene_list.name or source_gene_list.slug,
                is_public=source_gene_list.is_public,
            )
        except ObjectDoesNotExist:
            raise Exception('LocusList "%s" not found. Please run `python manage.py transfer_gene_lists`' % (
                source_gene_list.name or source_gene_list.slug))
        except MultipleObjectsReturned:
            logger.error("Multiple LocusLists with  owner '%s' and name '%s'" % (
                source_gene_list.owner, (source_gene_list.name or source_gene_list.slug))
            )
            continue

        assign_perm(user_or_group=new_project.can_view_group, perm=CAN_VIEW, obj=locus_list)

    # add collaborators to new_project.can_view_group and/or can_edit_group
    collaborator_user_ids = set()
    for collaborator in ProjectCollaborator.objects.filter(project=source_project):
        collaborator_user_ids.add( collaborator.user.id )
        if collaborator.collaborator_type == 'manager':
            new_project.can_edit_group.user_set.add(collaborator.user)
            new_project.can_view_group.user_set.add(collaborator.user)
        elif collaborator.collaborator_type == 'collaborator':
            new_project.can_view_group.user_set.add(collaborator.user)
            new_project.can_edit_group.user_set.remove(collaborator.user)
        else:
            raise ValueError("Unexpected collaborator_type: %s" % collaborator.collaborator_type)

    for user in new_project.can_edit_group.user_set.all():
        if user.id not in collaborator_user_ids:
            new_project.can_view_group.user_set.remove(user)
            new_project.can_edit_group.user_set.remove(user)
            new_project.owners_group.user_set.remove(user)
            print("REMOVED user %s permissions from project %s" % (user, new_project))

    return new_project, created


def safe_get_or_create(xbrowse_model):
    seqr_model = find_matching_seqr_model(xbrowse_model)
    if seqr_model:
        return seqr_model, False
    else:
        return _create_seqr_model(xbrowse_model), True


def transfer_family(source_family):
    """Transfers the given family and returns the new family"""

    new_family, created = safe_get_or_create(source_family)
    if created:
        print("Created SeqrFamily", new_family)

    update_model_fields(new_family, source_family, [
        'project', 'family_id', 'family_name', 'short_description', 'pedigree_image', 'about_family_content', 'analysis_summary_content',
        'causal_inheritance_mode', 'analysis_status', 'coded_phenotype', 'post_discovery_omim_number',
        'internal_case_review_notes', 'internal_case_review_summary',
    ])
    if new_family.display_name == new_family.family_id:
        new_family.display_name = ''
        new_family.save()

    return new_family, created


def transfer_individual(source_individual, new_project, connect_to_phenotips):
    """Transfers the given Individual and returns the new Individual"""

    # get rid of '.' to signify 'unknown'
    if source_individual.paternal_id == "." or source_individual.maternal_id == "." or source_individual.gender == "." or source_individual.affected == ".":
        if source_individual.paternal_id == ".":
            source_individual.paternal_id = ""
        if source_individual.maternal_id == ".":
            source_individual.maternal_id = ""
        if source_individual.affected == ".":
            source_individual.affected = ""
        if source_individual.gender == ".":
            source_individual.gender = ""
        source_individual.save()

    new_individual, created = safe_get_or_create(source_individual)
    if created:
        print("Created SeqrSample", new_individual)

    update_model_fields(new_individual, source_individual, [
        'family', 'indiv_id', 'created_date', 'maternal_id', 'paternal_id', 'gender', 'affected', 'nickname',
        'case_review_status', 'phenotips_id', 'phenotips_data',
    ])

    if new_individual.display_name == new_individual.individual_id:
        new_individual.display_name = ''
        new_individual.save()

    # update PhenoTips data
    phenotips_data_retrieved = False
    if connect_to_phenotips and new_project.is_phenotips_enabled:
        try:
            data_json = _get_patient_data(
                new_project,
                new_individual,
            )

            _update_individual_phenotips_data(new_individual, data_json)

            phenotips_data_retrieved = True
        except phenotips_api.PhenotipsException as e:
            print("Couldn't retrieve latest data from phenotips for %s: %s" % (new_individual, e))

    return new_individual, created, phenotips_data_retrieved


def transfer_analysed_by(source_analysed_by, new_family):
    created = False
    if not source_analysed_by.seqr_family_analysed_by:
        new_analysed_by = SeqrAnalysedBy.objects.create(
            family=new_family,
            created_by=source_analysed_by.user,
        )
        new_analysed_by.save(last_modified_date=source_analysed_by.date_saved)

        source_analysed_by.seqr_family_analysed_by = new_analysed_by
        source_analysed_by.save()
        created = True

    return source_analysed_by.seqr_family_analysed_by, created


def get_or_create_sample(
        source_individual,
        new_individual,
        sample_type,
        dataset_type,
        elasticsearch_index,
        dataset_file_path,
        sample_status,
        loaded_date):
    """Creates and returns a new Sample based on the provided models."""

    new_sample, created = SeqrSample.objects.get_or_create(
        sample_type=sample_type,
        individual=new_individual,
        sample_id=(source_individual.vcf_id or source_individual.indiv_id).strip(),
        dataset_type=dataset_type,
        elasticsearch_index=elasticsearch_index,
        dataset_file_path=dataset_file_path,
        sample_status=sample_status,
        loaded_date=loaded_date,
    )

    new_sample.created_date = new_individual.created_date
    new_sample.save()

    return new_sample, created


def get_or_create_variant_tag_type(source_variant_tag_type):
    new_variant_tag_type, created = safe_get_or_create(source_variant_tag_type)

    if created:
        print("=== created variant tag type: " + str(new_variant_tag_type))

    update_model_fields(new_variant_tag_type, source_variant_tag_type, [
        'project', 'tag', 'title', 'color', 'order', 'category'
    ])

    return new_variant_tag_type, created


def get_or_create_variant_tag(source_variant_tag, new_family):
    new_variant_tag, created = safe_get_or_create(source_variant_tag)
    if created:
        print("=== created variant tag: " + str(new_variant_tag))
        new_variant_tag.saved_variant = deprecated_get_or_create_saved_variant(
            xpos=source_variant_tag.xpos,
            ref=source_variant_tag.ref,
            alt=source_variant_tag.alt,
            family=new_family,
        )

    update_model_fields(new_variant_tag, source_variant_tag, ['project_tag', 'search_url', 'user'])

    return new_variant_tag, created


def get_or_create_variant_functional_data(source_variant_functional_data, new_family):
    new_variant_functional_data, created = safe_get_or_create(source_variant_functional_data)
    if created:
        print("=== created variant functional data: " + str(new_variant_functional_data))
        new_variant_functional_data.saved_variant = deprecated_get_or_create_saved_variant(
            xpos=source_variant_functional_data.xpos,
            ref=source_variant_functional_data.ref,
            alt=source_variant_functional_data.alt,
            family=new_family,
        )

    update_model_fields(new_variant_functional_data, source_variant_functional_data, ['functional_data_tag', 'search_url', 'user', 'metadata'])

    return new_variant_functional_data, created


def get_or_create_variant_note(source_variant_note, new_family):
    new_variant_note, created = safe_get_or_create(source_variant_note)

    if created:
        print("=== created variant note: " + str(new_variant_note))
        new_variant_note.saved_variant = deprecated_get_or_create_saved_variant(
            xpos=source_variant_note.xpos,
            ref=source_variant_note.ref,
            alt=source_variant_note.alt,
            family=new_family,
        )

    new_variant_note.submit_to_clinvar = source_variant_note.submit_to_clinvar or False
    update_model_fields(new_variant_note, source_variant_note, ['note', 'submit_to_clinvar', 'search_url', 'user'])

    return new_variant_note, created


def look_up_individual_loaded_date(source_individual, earliest_loaded_date=False):
    """Retrieve the data-loaded time for the given individual"""

    # decode data loaded time
    loaded_date = None
    try:
        datastore = get_datastore(source_individual.project)

        family_id = source_individual.family.family_id
        project_id = source_individual.project.project_id
        if earliest_loaded_date:
            project_id += "_previous1" # add suffix

        family_collection = datastore._get_family_collection(project_id, family_id) if hasattr(datastore, '_get_family_collection') else None
        if not family_collection:
            #logger.error("mongodb family collection not found for %s %s" % (project_id, family_id))
            return loaded_date

        record = family_collection.find_one()
        if record:
            loaded_date = record['_id'].generation_time
            # logger.info("%s data-loaded date: %s" % (project_id, loaded_date))
        else:
            family_info_record = datastore._get_family_info(project_id, family_id)
            loaded_date = family_info_record['_id'].generation_time

    except Exception as e:
        logger.error('Unable to look up loaded_date for %s' % (source_individual,))
        logger.error(e)

    return loaded_date
