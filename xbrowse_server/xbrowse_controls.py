"""
Bridge to xBrowse for management commands like loading projects, etc
Celery tasks are just shells over these functions

Make sure DJANGO_SETTINGS_MODULE is set before calling - this script gets entities from django.conf

***
Future Plan
***
reload_exome_coverage() -> kwargs family, project
reload_variants() -> kwargs family, project

"""

import os
import gzip
import shutil
import vcf

from datetime import datetime, date
from django.conf import settings
from xbrowse_server import mall

from xbrowse_server.base.models import Project, Individual, Family, Cohort
from xbrowse import genomeloc
from xbrowse_server.mall import get_mall, get_cnv_store, get_coverage_store, get_project_datastore


def clean_project(project_id):
    """
    Clear data for this project from all the xbrowse resources:
     - datastore
     - coverage store
     - cnv store
    Does not remove any of the project's data links - so no data is lost, but everything must be rebuilt
    """
    project = Project.objects.get(project_id=project_id)
    individuals = project.get_individuals()

    # datastore
    get_mall().variant_store.delete_project(project_id)

    # coverage store
    for individual in individuals:
        get_coverage_store().remove_sample(individual.get_coverage_store_id())

    # cnv store
    for individual in individuals:
        get_cnv_store().remove_sample(individual.get_coverage_store_id())


def load_project(project_id, force_annotations=False):
    """
    Reload a whole project
    """
    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- starting load_project: " + project_id))
    project = Project.objects.get(project_id=project_id)

    #load_project_coverage(project_id)
    load_project_variants(project_id, force_annotations=force_annotations)

    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- load_project: " + project_id + " is done!"))


def load_coverage_for_individuals(individuals):
    for individual in individuals:
        if individual.coverage_file:
            get_coverage_store().add_sample(individual.get_coverage_store_id(), gzip.open(individual.coverage_file))


def load_project_coverage(project_id):
    print "Loading coverage data for project %s" % project_id
    project = Project.objects.get(project_id=project_id)
    individuals = project.get_individuals()
    load_coverage_for_individuals(individuals)


def load_variants_for_family_list(project, families, vcf_file):
    """
    Reload variants for a list of families, all from the same vcf
    """
    family_list = []
    for family in families:
        family_list.append({
            'project_id': family.project.project_id,
            'family_id': family.family_id,
            'individuals': family.indiv_ids_with_variant_data(),
        })

    # add all families from this vcf to the datastore
    get_mall().variant_store.add_family_set(family_list)

    # create the VCF ID map
    vcf_id_map = {}
    for family in families:
        for individual in family.get_individuals():
            if individual.vcf_id:
                vcf_id_map[individual.vcf_id] = individual.indiv_id

    # load them all into the datastore
    family_tuple_list = [(f['project_id'], f['family_id']) for f in family_list]
    get_mall().variant_store.load_family_set(
        vcf_file,
        family_tuple_list,
        reference_populations=project.get_reference_population_slugs(),
        vcf_id_map=vcf_id_map,
    )

    # finish up each family
    for family in families:
        _family_postprocessing(family)


def load_variants_for_cohort_list(project, cohorts):

    for cohort in cohorts:
        family_list = []
        print "Adding {}".format(cohort.cohort_id)
        family_list.append({
            'project_id': cohort.project.project_id,
            'family_id': cohort.cohort_id,
            'individuals': cohort.indiv_id_list(),
            })

        # add all families from this vcf to the datastore
        get_mall().variant_store.add_family_set(family_list)

        vcf_files = cohort.get_vcf_files()

        # create the VCF ID map
        vcf_id_map = {}
        for individual in cohort.get_individuals():
            if individual.vcf_id:
                vcf_id_map[individual.vcf_id] = individual.indiv_id

        # load them all into the datastore
        for vcf_file in vcf_files:
            family_tuple_list = [(f['project_id'], f['family_id']) for f in family_list]
            get_mall().variant_store.load_family_set(
                vcf_file.path(),
                family_tuple_list,
                reference_populations=project.get_reference_population_slugs(),
                vcf_id_map=vcf_id_map,
            )


def load_project_variants(project_id, force_annotations=False, ignore_csq_in_vcf=False):
    """
    Load any families and cohorts in this project that aren't loaded already 
    """
    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- loading project: " + project_id + " - db.variants cache"))
    os.system("du /usr/local/var/mongodb")
    project = Project.objects.get(project_id=project_id)

    for vcf_obj in project.get_all_vcf_files():
        r = vcf.VCFReader(filename=vcf_obj.path())
        if not ignore_csq_in_vcf and "CSQ" in r.infos:
            mall.get_annotator().add_preannotated_vcf_file(vcf_obj.path(), force=force_annotations)
        else:
            mall.get_annotator().add_vcf_file_to_annotator(vcf_obj.path(), force_all=force_annotations)

    # batch load families by VCF file
    for vcf_file, families in project.families_by_vcf().items():
        families = [f for f in families if get_mall().variant_store.get_family_status(project_id, f.family_id) != 'loaded']
        for i in xrange(0, len(families), settings.FAMILY_LOAD_BATCH_SIZE):
            os.system("du /usr/local/var/mongodb")
            print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- loading project: " + project_id + " - families batch %d - %d families" % (i, len(families[i:i+settings.FAMILY_LOAD_BATCH_SIZE])) ))
            #print "Loading project %s - families: %s" % (project_id, families[i:i+settings.FAMILY_LOAD_BATCH_SIZE])
            load_variants_for_family_list(project, families[i:i+settings.FAMILY_LOAD_BATCH_SIZE], vcf_file)

    # now load cohorts
    os.system("du /usr/local/var/mongodb")
    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- loading project: " + project_id + " - cohorts"))

    # TODO: load cohorts and families together
    for vcf_file, cohorts in project.cohorts_by_vcf().items():
        cohorts = [c for c in cohorts if get_mall().variant_store.get_family_status(project_id, c.cohort_id) != 'loaded']
        for i in xrange(0, len(cohorts), settings.FAMILY_LOAD_BATCH_SIZE):
            print "Loading project %s - cohorts: %s" % (project_id, cohorts[i:i+settings.FAMILY_LOAD_BATCH_SIZE])
            load_variants_for_cohort_list(project, cohorts[i:i+settings.FAMILY_LOAD_BATCH_SIZE])

    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- finished loading project: " + project_id))


def _family_postprocessing(family):
    """
    Placeholder - we used to do postprocessing for stats and will want to add it back soon
    """
    pass


def preload_vep_vcf_annotations(vcf_file_path):
    mall.get_annotator().preload_vep_annotated_vcf(open(vcf_file_path))


def load_project_datastore(project_id):
    """
    Load this project into the project datastore
    Which allows queries over all variants in a project
    """
    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- starting load_project_datastore: " + project_id))
    project = Project.objects.get(project_id=project_id)
    get_project_datastore().delete_project_store(project_id)
    get_project_datastore().add_project(project_id)
    for vcf_file in project.get_all_vcf_files():
        project_indiv_ids = [i.indiv_id for i in project.get_individuals()]
        vcf_ids = vcf_file.sample_id_list()
        indiv_id_list = [i for i in project_indiv_ids if i in vcf_ids]
        get_project_datastore().add_variants_to_project_from_vcf(
            vcf_file.file_handle(),
            project_id,
            indiv_id_list=indiv_id_list
        )

    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- load_project_datastore: " + project_id + " is done!"))
