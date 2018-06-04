from bson import json_util
import json
import logging
import os
import pymongo
from tqdm import tqdm
import settings

from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Q
from guardian.shortcuts import assign_perm

from seqr.utils.model_sync_utils import get_or_create_saved_variant
from seqr.views.apis import phenotips_api
from seqr.views.apis.phenotips_api import _update_individual_phenotips_data
from xbrowse_server.base.models import \
    Project, \
    Family, \
    Individual, \
    VariantNote, \
    ProjectTag, \
    VariantTag, \
    VariantFunctionalData, \
    ProjectCollaborator

from seqr.models import \
    Project as SeqrProject, \
    Family as SeqrFamily, \
    Individual as SeqrIndividual, \
    VariantTagType as SeqrVariantTagType, \
    VariantTag as SeqrVariantTag, \
    VariantNote as SeqrVariantNote, \
    VariantFunctionalData as SeqrVariantFunctionalData, \
    Sample as SeqrSample, \
    Dataset as SeqrDataset, \
    LocusList, \
    CAN_VIEW, ModelWithGUID

from xbrowse_server.mall import get_datastore, get_annotator

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
        parser.add_argument('-w', '--wgs-projects', help='text file that lists WGS project-ids - one per line')
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
        #    SeqrVariantTagType.objects.all().delete()
        #    SeqrVariantTag.objects.all().delete()
        #    SeqrVariantNote.objects.all().delete()
        #    SeqrSample.objects.all().delete()
        #    SeqrDataset.objects.all().delete()

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
            project_ids_to_process = [p.project_id for p in projects]

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
                sample_type = SeqrSample.SAMPLE_TYPE_WGS
                counters['wgs_projects'] += 1
            elif "rna-seq" in project_names:
                sample_type = SeqrSample.SAMPLE_TYPE_RNA
                counters['rna_projects'] += 1
            else:
                sample_type = SeqrSample.SAMPLE_TYPE_WES
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
                        new_project,
                        new_family,
                        new_variant_tag_type,
                    )

                    if variant_tag_created: counters['variant_tags_created'] += 1

            for source_variant_functional_data in VariantFunctionalData.objects.filter(family__project=source_project):
                new_family = source_family_id_to_new_family.get(source_variant_functional_data.family.id)

                _, variant_functional_data_created = get_or_create_variant_functional_data(
                    source_variant_functional_data,
                    new_project,
                    new_family,
                )

                if variant_functional_data_created:   counters['variant_functional_data_created'] += 1

            for source_variant_note in VariantNote.objects.filter(project=source_project):
                new_family = source_family_id_to_new_family.get(source_variant_note.family.id if source_variant_note.family else None)

                new_variant_note, variant_note_created = get_or_create_variant_note(
                    source_variant_note,
                    new_project,
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
                #sample.delete()

            for sample in SeqrSample.objects.filter(dataset__isnull=True):
                # print("--- deleting SeqrSample without dataset: %s" % sample)
                counters["deleted SeqrSample"] += 1
                #sample.delete()

            #for dataset in SeqrDataset.objects.filter(dataset__isnull=True):
            #    print("Deleting SeqrSample without dataset: %s" % sample)
            #    counters["deleted SeqrSample"] += 1
            #    #sample.delete()


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


def create_sample_records(sample_type, source_project, source_individual, new_project, new_individual, counters):

    vcf_files = [f for f in source_individual.vcf_files.all()]
    if len(vcf_files) > 0:
        new_sample, sample_created = get_or_create_sample(
            source_individual,
            new_individual,
            sample_type=sample_type
        )

        if sample_created: counters['samples_created'] += 1

        # get the most recent VCF file (the one with the highest primary key)
        #vcf_files_max_pk = max([f.pk for f in vcf_files])
        #vcf_path = [f.file_path for f in vcf_files if f.pk == vcf_files_max_pk][0]

        # get the earliest VCF file (the one with the lowest primary key)
        vcf_files_min_pk = min([f.pk for f in vcf_files])

        earliest_vcf_dataset = None
        for vcf_file in vcf_files:
            try:
                vcf_loaded_date = look_up_vcf_loaded_date(vcf_file.file_path)
            except Exception:
                vcf_loaded_date = None

            new_vcf_dataset, vcf_dataset_created = get_or_create_dataset(
                new_sample,
                new_project,
                source_individual,
                vcf_file.file_path,
                analysis_type=SeqrDataset.ANALYSIS_TYPE_VARIANT_CALLS,
                loaded_date=vcf_loaded_date,
            )

            if vcf_file.pk == vcf_files_min_pk:
                earliest_vcf_dataset = new_vcf_dataset

        #logger.info("get_or_create_dataset(%s, %s, %s, %s) returned %s" % (new_sample, new_project, source_individual, vcf_path, new_vcf_dataset))
        # logger.info("get_or_create_dataset(%s, %s, %s) returned %s" % (new_sample, new_project, source_individual, new_vcf_dataset))

        # find and record the earliest callset for this individual
        if earliest_vcf_dataset is not None:
            new_earliest_dataset, earliest_dataset_created = get_or_create_earliest_dataset(
                earliest_vcf_dataset,
                new_sample,
                new_project,
                source_individual,
                analysis_type=SeqrDataset.ANALYSIS_TYPE_VARIANT_CALLS,
            )

        if source_individual.bam_file_path:
            new_bam_dataset, bam_dataset_created = get_or_create_dataset(
                new_sample,
                new_project,
                source_individual,
                source_individual.bam_file_path,
                analysis_type=SeqrDataset.ANALYSIS_TYPE_ALIGNMENT,
                loaded_date=vcf_loaded_date,
                genome_version=new_vcf_dataset.genome_version,
            )


def look_up_vcf_loaded_date(vcf_path):
    vcf_record = get_annotator().get_vcf_file_from_annotator(vcf_path)
    if vcf_record is None:
        raise ValueError("Couldn't find loaded date for %s" % vcf_path)

    loaded_date = vcf_record['_id'].generation_time
    # logger.info("%s data-loaded date: %s" % (vcf_path, loaded_date))
    return loaded_date


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
        if DEBUG and field_name != 'phenotips_data':
            i = raw_input("Should %s.%s = %s\n instead of \n%s \n in %s ? [Y\n]" % (model.__class__.__name__.encode('utf-8'), field_name.encode('utf-8'), unicode(new_value).encode('utf-8'), getattr(model, field_name), str(model)))
            if i.lower() != "y":
                print("ok, skipping.")
                return
            
        setattr(model, field_name, new_value)
        if field_name != 'phenotips_data':
            print("Setting %s.%s = %s" % (model.__class__.__name__.encode('utf-8'), field_name.encode('utf-8'), unicode(new_value).encode('utf-8')))
        model.save()


def transfer_project(source_project):
    """Transfers the given project and returns the new project"""

    # create project
    try:
        new_project, created = SeqrProject.objects.get_or_create(
            deprecated_project_id=source_project.project_id.strip(),
        )
    except MultipleObjectsReturned as e:
        raise ValueError("multiple SeqrProjects found to have deprecated_project_id=%s" % source_project.project_id.strip(), e)

    if created:
        print("Created SeqrProject", new_project)

    if source_project.seqr_project != new_project:
        source_project.seqr_project = new_project
        source_project.save()

    update_model_field(new_project, 'guid', new_project._compute_guid()[:ModelWithGUID.MAX_GUID_SIZE])
    update_model_field(new_project, 'name', (source_project.project_name or source_project.project_id).strip())
    update_model_field(new_project, 'description', source_project.description)

    update_model_field(new_project, 'is_phenotips_enabled', source_project.is_phenotips_enabled)

    update_model_field(new_project, 'is_mme_enabled', source_project.is_mme_enabled)
    update_model_field(new_project, 'mme_primary_data_owner', source_project.mme_primary_data_owner)
    update_model_field(new_project, 'mme_contact_url', source_project.mme_contact_url)
    update_model_field(new_project, 'mme_contact_institution', source_project.mme_contact_institution)

    update_model_field(new_project, 'is_functional_data_enabled', source_project.is_functional_data_enabled)
    update_model_field(new_project, 'disease_area', source_project.disease_area)

    update_model_field(new_project, 'deprecated_last_accessed_date', source_project.last_accessed_date)

    for p in source_project.private_reference_populations.all():
        new_project.custom_reference_populations.add(p)

    if source_project.project_id not in settings.PROJECTS_WITHOUT_PHENOTIPS:
        update_model_field(new_project, 'is_phenotips_enabled', True)
        update_model_field(new_project, 'phenotips_user_id', source_project.project_id)
    else:
        new_project.is_phenotips_enabled = False

    #if source_project.project_id in settings.PROJECTS_WITH_MATCHMAKER:
    #    update_model_field(new_project, 'is_mme_enabled', True)
    #    update_model_field(new_project, 'mme_primary_data_owner', settings.MME_PATIENT_PRIMARY_DATA_OWNER[source_project.project_id])
    #else:
    #    new_project.is_mme_enabled = False

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


def transfer_family(source_family, new_project):
    """Transfers the given family and returns the new family"""
    #new_project.created_date.microsecond = random.randint(0, 10**6 - 1)

    new_family, created = SeqrFamily.objects.get_or_create(project=new_project, family_id=source_family.family_id)
    if created:
        print("Created SeqrFamily", new_family)

    if source_family.seqr_family != new_family:
        source_family.seqr_family = new_family
        source_family.save()

    update_model_field(new_family, 'display_name', source_family.family_name or source_family.family_id)
    update_model_field(new_family, 'description', source_family.short_description)
    update_model_field(new_family, 'pedigree_image', source_family.pedigree_image)
    update_model_field(new_family, 'analysis_notes', source_family.about_family_content)
    update_model_field(new_family, 'analysis_summary', source_family.analysis_summary_content)
    update_model_field(new_family, 'causal_inheritance_mode', source_family.causal_inheritance_mode)
    update_model_field(new_family, 'analysis_status', source_family.analysis_status)
    update_model_field(new_family, 'coded_phenotype', source_family.coded_phenotype)
    update_model_field(new_family, 'post_discovery_omim_number', source_family.post_discovery_omim_number)
    update_model_field(new_family, 'internal_case_review_notes', source_family.internal_case_review_notes)
    update_model_field(new_family, 'internal_case_review_summary', source_family.internal_case_review_summary)

    return new_family, created


def transfer_individual(source_individual, new_family, new_project, connect_to_phenotips):
    """Transfers the given Individual and returns the new Individual"""

    new_individual, created = SeqrIndividual.objects.get_or_create(family=new_family, individual_id=source_individual.indiv_id)
    if created:
        print("Created SeqrSample", new_individual)

    if source_individual.seqr_individual != new_individual:
        source_individual.seqr_individual = new_individual
        source_individual.save()

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

    update_model_field(new_individual, 'created_date', source_individual.created_date)
    update_model_field(new_individual, 'maternal_id',  source_individual.maternal_id)
    update_model_field(new_individual, 'paternal_id',  source_individual.paternal_id)
    update_model_field(new_individual, 'sex',  source_individual.gender)
    update_model_field(new_individual, 'affected',  source_individual.affected)
    update_model_field(new_individual, 'display_name', source_individual.nickname or source_individual.indiv_id)
    #update_model_field(new_individual, 'notes',  source_individual.notes) <-- notes exist only in the new SeqrIndividual schema. other_notes was never really used
    update_model_field(new_individual, 'case_review_status',  source_individual.case_review_status)
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


def get_or_create_sample(source_individual, new_individual, sample_type):
    """Creates and returns a new Sample based on the provided models."""

    new_sample, created = SeqrSample.objects.get_or_create(
        sample_type=sample_type,
        individual=new_individual,
        sample_id=(source_individual.vcf_id or source_individual.indiv_id).strip(),
        deprecated_base_project=source_individual.family.project,
    )
    new_sample.created_date=new_individual.created_date
    new_sample.sample_status=source_individual.coverage_status
    new_sample.save()

    return new_sample, created


def get_or_create_dataset(new_sample, new_project, source_individual, source_file_path, analysis_type, loaded_date=None, genome_version=None):

    new_dataset, created = SeqrDataset.objects.get_or_create(
        analysis_type=analysis_type,
        source_file_path=source_file_path,
        project=new_project,
    )

    new_dataset.name = os.path.basename(source_file_path)
    num_samples = new_dataset.samples.count()
    new_dataset.description = "%s %s sample" % (num_samples, new_sample.sample_type)
    if num_samples > 1:
        new_dataset.description += "s"

    # set name = vcf file path
    # set description = "WES callset with x samples"

    new_dataset.created_date = new_sample.individual.family.project.created_date
    if genome_version is not None:
        new_dataset.genome_version = genome_version
    new_dataset.save()

    if source_individual.is_loaded():
        new_dataset.is_loaded = True
        if loaded_date is not None:
            new_dataset.loaded_date = loaded_date
        elif not new_dataset.loaded_date:
            new_dataset.loaded_date = look_up_individual_loaded_date(source_individual)
        new_dataset.save()

    new_dataset.samples.add(new_sample)

    #if created:
        # SampleBatch permissions - handled same way as for gene lists, except - since SampleBatch
        # currently can't be shared with more than one project, allow SampleBatch metadata to be
        # edited by users with project CAN_EDIT permissions
    #    assign_perm(user_or_group=new_project.can_edit_group, perm=CAN_EDIT, obj=new_sample_batch)
    #    assign_perm(user_or_group=new_project.can_view_group, perm=CAN_VIEW, obj=new_sample_batch)

    return new_dataset, created


def date_difference_in_days(date1, date2):
    delta = date1 - date2
    return abs(delta.days)


def get_or_create_earliest_dataset(current_dataset, new_sample, new_project, source_individual, analysis_type):

    created = False

    # if the individual doesn't have data loaded, just punt
    if not source_individual.is_loaded():
        return current_dataset, created


    # check if an early dataset already exists for this sample
    matching_datasets = new_sample.dataset_set.filter(
        analysis_type=analysis_type,
        source_file_path='unknown-previous-callset-path',
        project=new_project)
    
    if matching_datasets:
        return matching_datasets[0], created

    # look up if an earlier dataset exists
    earliest_loaded_date = look_up_individual_loaded_date(source_individual, earliest_loaded_date=True)
    if earliest_loaded_date is None:
        # no earlier dataset found
        return current_dataset, created
        
    # if earliest_loaded_date is within ~ 1 month of current_dataset loaded date
    if date_difference_in_days(earliest_loaded_date, current_dataset.loaded_date) <= 25:
        logger.info("earliest found loaded-date is within %d days of the current loaded dataset" % (date_difference_in_days(earliest_loaded_date, current_dataset.loaded_date),))
        return current_dataset, created

    # if there's another sample in this project that had data loaded within 20 days of this one, reuse that dataset
    for existing_dataset_record in SeqrDataset.objects.filter(project=new_project, analysis_type=analysis_type):
        if existing_dataset_record.loaded_date and date_difference_in_days(earliest_loaded_date, existing_dataset_record.loaded_date) <= 25:
            logger.info("Updated earliest dataset record for sample %s %s: %s" % (new_project, new_sample, existing_dataset_record.loaded_date))
            existing_dataset_record.samples.add(new_sample)
            return existing_dataset_record, created

    # else create a new dataset
    earliest_dataset, created = SeqrDataset.objects.get_or_create(
        analysis_type=analysis_type,
        source_file_path='unknown-previous-callset-path',
        project=new_project,
        loaded_date=earliest_loaded_date,
        is_loaded=False,
    )
    earliest_dataset.created_date = new_sample.individual.family.project.created_date
    earliest_dataset.save()

    logger.info("Created new earliest dataset record for sample %s %s: %s" % (new_project, new_sample, earliest_loaded_date))

    earliest_dataset.samples.add(new_sample)

    #if created:
    # SampleBatch permissions - handled same way as for gene lists, except - since SampleBatch
    # currently can't be shared with more than one project, allow SampleBatch metadata to be
    # edited by users with project CAN_EDIT permissions
    #    assign_perm(user_or_group=new_project.can_edit_group, perm=CAN_EDIT, obj=new_sample_batch)
    #    assign_perm(user_or_group=new_project.can_view_group, perm=CAN_VIEW, obj=new_sample_batch)

    return earliest_dataset, created


def get_or_create_variant_tag_type(source_variant_tag_type, new_project):
    try:
        created = False
        new_variant_tag_type = SeqrVariantTagType.objects.get(
            project=None,
            name=source_variant_tag_type.tag,
        )
        # If a core tag type exists with that name, delete any project-specific tag types
        _, deleted = SeqrVariantTagType.objects.filter(
            project=new_project,
            name=source_variant_tag_type.tag,
        ).delete()
        for model, delete_count in deleted.items():
            print("=== deleted {} {} models with tag type {}".format(delete_count, model, source_variant_tag_type.tag))

    except ObjectDoesNotExist:
        new_variant_tag_type, created = SeqrVariantTagType.objects.get_or_create(
            project=new_project,
            name=source_variant_tag_type.tag,
        )

        if created:
            print("=== created variant tag type: " + str(new_variant_tag_type))

        new_variant_tag_type.description = source_variant_tag_type.title
        new_variant_tag_type.color = source_variant_tag_type.color
        new_variant_tag_type.order = source_variant_tag_type.order
        new_variant_tag_type.category = source_variant_tag_type.category
        new_variant_tag_type.is_built_in = False
        new_variant_tag_type.save()

    if source_variant_tag_type.seqr_variant_tag_type != new_variant_tag_type:
        source_variant_tag_type.seqr_variant_tag_type = new_variant_tag_type
        source_variant_tag_type.save()

    return new_variant_tag_type, created


def get_or_create_variant_tag(source_variant_tag, new_project, new_family, new_variant_tag_type):
    new_saved_variant = get_or_create_saved_variant(
        xpos=source_variant_tag.xpos,
        ref=source_variant_tag.ref,
        alt=source_variant_tag.alt,
        family=new_family,
        project=new_project
    )

    new_variant_tag, created = SeqrVariantTag.objects.get_or_create(
        saved_variant=new_saved_variant,
        variant_tag_type=new_variant_tag_type,
    )
    if created:
        print("=== created variant tag: " + str(new_variant_tag))

    if source_variant_tag.seqr_variant_tag != new_variant_tag:
        source_variant_tag.seqr_variant_tag = new_variant_tag
        source_variant_tag.save()

    new_variant_tag.search_parameters = source_variant_tag.search_url
    new_variant_tag.created_by = source_variant_tag.user
    new_variant_tag.save(last_modified_date=source_variant_tag.date_saved)

    return new_variant_tag, created


def get_or_create_variant_functional_data(source_variant_functional_data, new_project, new_family):
    new_saved_variant = get_or_create_saved_variant(
        xpos=source_variant_functional_data.xpos,
        ref=source_variant_functional_data.ref,
        alt=source_variant_functional_data.alt,
        family=new_family,
        project=new_project
    )

    new_variant_functional_data, created = SeqrVariantFunctionalData.objects.get_or_create(
        saved_variant=new_saved_variant,
        functional_data_tag=source_variant_functional_data.functional_data_tag,
    )
    if created:
        print("=== created variant functional data: " + str(new_variant_functional_data))

    if source_variant_functional_data.seqr_variant_functional_data != new_variant_functional_data:
        source_variant_functional_data.seqr_variant_functional_data = new_variant_functional_data
        source_variant_functional_data.save()

    new_variant_functional_data.search_parameters = source_variant_functional_data.search_url
    new_variant_functional_data.created_by = source_variant_functional_data.user
    new_variant_functional_data.metadata = source_variant_functional_data.metadata
    new_variant_functional_data.save(last_modified_date=source_variant_functional_data.date_saved)

    return new_variant_functional_data, created


def get_or_create_variant_note(source_variant_note, new_project, new_family):
    new_saved_variant = get_or_create_saved_variant(
        xpos=source_variant_note.xpos,
        ref=source_variant_note.ref,
        alt=source_variant_note.alt,
        family=new_family,
        project=new_project
    )

    new_variant_note, created = SeqrVariantNote.objects.get_or_create(
        created_by=source_variant_note.user,
        saved_variant=new_saved_variant,
        note=source_variant_note.note,
    )

    if created:
        print("=== created variant note: " + str(new_variant_note))

    if source_variant_note.seqr_variant_note != new_variant_note:
        source_variant_note.seqr_variant_note = new_variant_note
        source_variant_note.save()

    new_variant_note.search_parameters = source_variant_note.search_url
    new_variant_note.submit_to_clinvar = source_variant_note.submit_to_clinvar or False
    new_variant_note.save(last_modified_date=source_variant_note.date_saved)

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


def get_seqr_project_from_base_project(base_project):
    seqr_projects = SeqrProject.objects.filter(deprecated_project_id = base_project.project_id)
    if len(seqr_projects) == 1:
        return seqr_projects[0]

    return None


def get_seqr_family_from_base_family(base_family):
    seqr_families = SeqrFamily.objects.filter(family_id=base_family.family_id, project__deprecated_project_id=base_family.project.project_id)
    if len(seqr_families) == 1:
        return seqr_families[0]

    return None


def get_seqr_individual_from_base_individual(base_individual):
    seqr_individual = SeqrIndividual.objects.filter(
        individual_id=base_individual.indiv_id,
        family__family_id=base_individual.family.family_id,
        family__project__deprecated_project_id=base_individual.family.project.project_id
    )
    if len(seqr_individual) == 1:
        return seqr_individual[0]

    return None
