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

from seqr import models
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
    Dataset as SeqrDataset, \
    LocusList, \
    CAN_EDIT, CAN_VIEW, ModelWithGUID

from xbrowse_server.mall import get_datastore, get_annotator, get_reference

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
        parser.add_argument('project_name', nargs="*", help='Project(s) to transfer. If not specified, defaults to all projects.')

    def handle(self, *args, **options):
        """transfer project"""
        project_names_to_process = options['project_name']

        counters = OrderedDefaultDict(int)

        if project_names_to_process:
            seqr_projects = SeqrProject.objects.filter(name__in=project_names_to_process)
            logging.info("Processing %s projects" % len(seqr_projects))
        else:
            seqr_projects = SeqrProject.objects.all()
            logging.info("Processing all %s projects" % len(seqr_projects))

        #updated_seqr_project_guids = set()
        #updated_seqr_family_guids = set()
        #updated_seqr_individual_guids = set()

        for seqr_project in tqdm(seqr_projects, unit=" projects"):
            counters['source_projects'] += 1

            logging.info("Project: " + seqr_project.guid)

            # transfer Project data
            project = Project.objects.get(project_id=seqr_project.deprecated_project_id)
            for dataset in seqr_project.dataset_set.all():
                if dataset.analysis_type == "VARIANTS":
                    project.genome_version = dataset.genome_version

            project.project_name = seqr_project.name
            project.created_by = seqr_project.created_by

            project.is_phenotips_enabled = seqr_project.is_phenotips_enabled
            project.phenotips_user_id = seqr_project.phenotips_user_id

            project.is_mme_enabled = seqr_project.is_mme_enabled
            project.mme_primary_data_owner = seqr_project.mme_primary_data_owner
            project.mme_contact_url = seqr_project.mme_contact_url
            project.mme_contact_institution = seqr_project.mme_contact_institution

            project.save()

            # TODO ProjectCategory

            # transfer Families and Individuals
            source_family_id_to_new_family = {}
            for seqr_family in seqr_project.family_set.all():
                #print("Family: " + seqr_family.guid)

                try:
                    family = Family.objects.get(project=project, family_id=seqr_family.family_id)
                except MultipleObjectsReturned as e:
                    logging.error("ERROR on %s family %s: %s" % (project, seqr_family.family_id, e))
                    family = Family.objects.filter(project=project, family_id=seqr_family.family_id)[0]
                    
                family.internal_analysis_status = seqr_family.internal_analysis_status
                family.save()

                for seqr_individual in seqr_family.individual_set.all():
                    individual = Individual.objects.get(family=family, indiv_id=seqr_individual.individual_id)
                    #print("Individual: " + seqr_individual.guid)
                    individual.case_review_status_last_modified_date = seqr_individual.case_review_status_last_modified_date
                    individual.case_review_status_last_modified_by = seqr_individual.case_review_status_last_modified_by
                    individual.case_review_discussion = seqr_individual.case_review_discussion
                    individual.phenotips_patient_id = seqr_individual.phenotips_patient_id
                    individual.save()
                    logging.info("%s has %s samples" % (seqr_individual, len(seqr_individual.sample_set.all())))
                    for sample in seqr_individual.sample_set.all():
                        logging.info("    %s has %s datasets" % (sample, len(sample.dataset_set.all())))
                        for dataset in sample.dataset_set.all():
                            if dataset.analysis_type != "VARIANTS" or not dataset.is_loaded:
                                continue

                            for vcf_file in individual.vcf_files.all():
                                vcf_file.project = project
                                vcf_file.sample_type = sample.sample_type
                                vcf_file.elasticsearch_index = dataset.dataset_id
                                vcf_file.loaded_date = dataset.loaded_date
                                vcf_file.save()

