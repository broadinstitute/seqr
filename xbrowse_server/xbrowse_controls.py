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
from django.utils import timezone
from xbrowse_server import mall

from xbrowse_server.base.models import Project, Individual, Family, Cohort, Breakpoint, BreakpointGene
from xbrowse import genomeloc
from xbrowse_server.mall import get_mall, get_cnv_store, get_coverage_store, get_project_datastore
from xbrowse.utils import slugify

import csv


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
    get_mall(project_id).variant_store.delete_project(project_id)

    # coverage store
    for individual in individuals:
        get_coverage_store().remove_sample(individual.get_coverage_store_id())

    # cnv store
    for individual in individuals:
        get_cnv_store().remove_sample(individual.get_coverage_store_id())


def load_project(project_id, force_load_annotations=False, force_load_variants=False, vcf_files=None, mark_as_loaded=True, start_from_chrom=None, end_with_chrom=None):
    """
    Reload a whole project
    """
    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- starting load_project: " + project_id + (" from chrom: " + start_from_chrom) if start_from_chrom else ""))

    settings.EVENTS_COLLECTION.insert({'event_type': 'load_project_started', 'date': timezone.now(), 'project_id': project_id})

    if vcf_files is None:
        load_project_variants(project_id, force_load_annotations=force_load_annotations, force_load_variants=force_load_variants, start_from_chrom=start_from_chrom, end_with_chrom=end_with_chrom)
    else:
        load_project_variants_from_vcf(project_id, vcf_files=vcf_files, mark_as_loaded=mark_as_loaded, start_from_chrom=start_from_chrom, end_with_chrom=end_with_chrom)

    load_project_breakpoints(project_id)
    
    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- load_project: " + project_id + " is done!"))

    # update the analysis status from 'Waiting for data' to 'Analysis in Progress'
    for f in Family.objects.filter(project__project_id=project_id):
        if f.analysis_status == 'Q':
            f.analysis_status = 'I'
            f.save()

    settings.EVENTS_COLLECTION.insert({'event_type': 'load_project_finished', 'date': timezone.now(), 'project_id': project_id})


def load_coverage_for_individuals(individuals):
    for individual in individuals:
        if individual.coverage_file:
            get_coverage_store().add_sample(individual.get_coverage_store_id(), gzip.open(individual.coverage_file))


def load_project_coverage(project_id):
    print "Loading coverage data for project %s" % project_id
    project = Project.objects.get(project_id=project_id)
    individuals = project.get_individuals()
    load_coverage_for_individuals(individuals)


def load_variants_for_family_list(project, families, vcf_file, mark_as_loaded=True, start_from_chrom=None, end_with_chrom=None):
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
    get_mall(project.project_id).variant_store.add_family_set(family_list)

    # create the VCF ID map
    vcf_id_map = {}
    for family in families:
        for individual in family.get_individuals():
            if individual.vcf_id:
                vcf_id_map[individual.vcf_id] = individual.indiv_id

    # load them all into the datastore
    family_tuple_list = [(f['project_id'], f['family_id']) for f in family_list]
    get_mall(project.project_id).variant_store.load_family_set(
        vcf_file,
        family_tuple_list,
        reference_populations=project.get_reference_population_slugs(),
        vcf_id_map=vcf_id_map,
        mark_as_loaded=mark_as_loaded,
        start_from_chrom=start_from_chrom, 
        end_with_chrom=end_with_chrom,
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
        get_mall(project.project_id).variant_store.add_family_set(family_list)

        vcf_files = cohort.get_vcf_files()

        # create the VCF ID map
        vcf_id_map = {}
        for individual in cohort.get_individuals():
            if individual.vcf_id:
                vcf_id_map[individual.vcf_id] = individual.indiv_id

        # load them all into the datastore
        for vcf_file in vcf_files:
            family_tuple_list = [(f['project_id'], f['family_id']) for f in family_list]
            get_mall(project.project_id).variant_store.load_family_set(
                vcf_file.path(),
                family_tuple_list,
                reference_populations=project.get_reference_population_slugs(),
                vcf_id_map=vcf_id_map,
            )


def load_project_variants_from_vcf(project_id, vcf_files, mark_as_loaded=True, start_from_chrom=None, end_with_chrom=None):
    """
    Load any families and cohorts in this project that aren't loaded already
    
    Args:
       project_id: the project id as a string
       vcf_files: a list of one or more vcf file paths
    """
    print("Called load_project_variants_from_vcf on " + str(vcf_files))
    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- loading project: " + project_id + " - db.variants cache"))
    project = Project.objects.get(project_id=project_id)

    for vcf_file in vcf_files:
        
        r = vcf.VCFReader(filename=vcf_file)
        if "CSQ" not in r.infos:
            raise ValueError("VEP annotations not found in VCF: " + vcf_file)
        
        if vcf_file in vcf_files:
            mall.get_annotator().add_preannotated_vcf_file(vcf_file)
            
    # batch load families by VCF file
    print("project.families_by_vcf(): " + str(project.families_by_vcf()))
    for vcf_file, families in project.families_by_vcf().items():
        if vcf_file not in vcf_files:
            print("Skipping %(vcf_file)s since its not in %(vcf_files)s" % locals())
            continue

        #families = [f for f in families if get_mall(project.project_id).variant_store.get_family_status(project_id, f.family_id) != 'loaded']
        print("Loading families for VCF file: " + vcf_file)
        for i in xrange(0, len(families), settings.FAMILY_LOAD_BATCH_SIZE):
            #print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- loading project: " + project_id + " - families batch %d - %d families" % (i, len(families[i:i+settings.FAMILY_LOAD_BATCH_SIZE]))))
            load_variants_for_family_list(project, families[i:i+settings.FAMILY_LOAD_BATCH_SIZE], vcf_file, mark_as_loaded=mark_as_loaded, start_from_chrom=start_from_chrom, end_with_chrom=end_with_chrom)
            print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- finished loading project: " + project_id))


def load_project_variants(project_id, force_load_annotations=False, force_load_variants=False, ignore_csq_in_vcf=False, start_from_chrom=None, end_with_chrom=None):
    """
    Load any families and cohorts in this project that aren't loaded already 
    """
    print "Loading project %s" % project_id
    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- loading project: " + project_id + " - db.variants cache"))
    project = Project.objects.get(project_id=project_id)

    for vcf_obj in sorted(project.get_all_vcf_files(), key=lambda v:v.path()):
        r = vcf.VCFReader(filename=vcf_obj.path())
        if not ignore_csq_in_vcf and "CSQ" not in r.infos:
            raise ValueError("VEP annotations not found in VCF: " + vcf_obj.path())

        mall.get_annotator().add_preannotated_vcf_file(vcf_obj.path(), force=force_load_annotations)
        

    # batch load families by VCF file
    for vcf_file, families in project.families_by_vcf().items():
        if not force_load_variants:
            # filter out families that have already finished loading
            families = [f for f in families if get_mall(project.project_id).variant_store.get_family_status(project_id, f.family_id) != 'loaded']

        for i in xrange(0, len(families), settings.FAMILY_LOAD_BATCH_SIZE):
            print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- loading project: " + project_id + " - families batch %d - %d families" % (i, len(families[i:i+settings.FAMILY_LOAD_BATCH_SIZE])) ))
            load_variants_for_family_list(project, families[i:i+settings.FAMILY_LOAD_BATCH_SIZE], vcf_file, start_from_chrom=start_from_chrom, end_with_chrom=end_with_chrom)

    # now load cohorts
    load_cohorts(project_id)

def load_cohorts(project_id):
    # now load cohorts
    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- loading project: " + project_id + " - cohorts"))

    project = Project.objects.get(project_id=project_id)
    for vcf_file, cohorts in project.cohorts_by_vcf().items():
        cohorts = [c for c in cohorts if get_mall(project.project_id).variant_store.get_family_status(project_id, c.cohort_id) != 'loaded']
        for i in xrange(0, len(cohorts), settings.FAMILY_LOAD_BATCH_SIZE):
            print("Loading project %s - cohorts: %s" % (project_id, cohorts[i:i+settings.FAMILY_LOAD_BATCH_SIZE]))
            load_variants_for_cohort_list(project, cohorts[i:i+settings.FAMILY_LOAD_BATCH_SIZE])

    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- finished loading project: " + project_id))


def _family_postprocessing(family):
    """
    Placeholder - we used to do postprocessing for stats and will want to add it back soon
    """
    pass


def preload_vep_vcf_annotations(vcf_file_path):
    mall.get_annotator().preload_vep_annotated_vcf(open(vcf_file_path))


def load_project_datastore(project_id, vcf_files=None, start_from_chrom=None, end_with_chrom=None):
    """
    Load this project into the project datastore
    Which allows queries over all variants in a project
    """
    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- starting load_project_datastore: " + project_id + (" from chrom: " + start_from_chrom) if start_from_chrom else ""))

    settings.EVENTS_COLLECTION.insert({'event_type': 'load_project_datastore_started', 'date': timezone.now(), 'project_id': project_id})

    project = Project.objects.get(project_id=project_id)
    get_project_datastore(project_id).delete_project_store(project_id)
    get_project_datastore(project_id).add_project(project_id)
    for vcf_file in sorted(project.get_all_vcf_files(), key=lambda v:v.path()):
        vcf_file_path = vcf_file.path()
        if vcf_files is not None and vcf_file_path not in vcf_files:
            print("Skipping - %(vcf_file_path)s is not in %(vcf_files)s" % locals())
        project_indiv_ids = [i.indiv_id for i in project.get_individuals()]
        vcf_ids = vcf_file.sample_id_list()
        indiv_id_list = [i for i in project_indiv_ids if i in vcf_ids]
        get_project_datastore(project_id).add_variants_to_project_from_vcf(
            vcf_file.file_handle(),
            project_id,
            indiv_id_list=indiv_id_list,
            start_from_chrom=start_from_chrom,
            end_with_chrom=end_with_chrom
        )

    get_project_datastore(project_id).set_project_collection_to_loaded(project_id)

    print(date.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S  -- load_project_datastore: " + project_id + " is done!"))

    settings.EVENTS_COLLECTION.insert({'event_type': 'load_project_datastore_finished', 'date': timezone.now(), 'project_id': project_id})


def load_project_breakpoints(project_id):

    project = Project.objects.get(project_id=project_id)

    breakpoint_files = project.breakpointfile_set.all()

    for breakpoint_file in breakpoint_files:
        print "Processing Breakpoint file: %s" % breakpoint_file.file_path
        if not os.path.exists(breakpoint_file.file_path):
            raise IOError("Specified breakpoint file %s does not exist" % breakpoint_file.file_path)

        with open(breakpoint_file.file_path) as bp_fh:
            r = csv.DictReader(bp_fh, delimiter='\t')
            for line in r:
                print "Loading breakpoint: %s" % str(line)
                add_breakpoint_from_dict(project, line)


def add_breakpoint_from_dict(project, bp ):
    """
    Add a breakpoint to the given project based on keys from the given dict.
    
    The sample id is presumed to already be loaded as an existing individual in the project.
    
    If a breakpoint already exists, it is not updated or changed (even if data loaded is
    actually different). Therefore to reload it is necessary to delete first, but it is 
    safe to load new samples incrementally by just running the load again.
    """

    # Fields in dict are chr     start   end     sample  depth   cscore  partner genes   cdsdist
    xpos = genomeloc.get_xpos(bp['chr'], int(bp['start']))
    sample_id = slugify(bp['sample'], separator='_')
    try:
        breakpoint = Breakpoint.objects.get(project=project, xpos=xpos, individual__indiv_id=sample_id)
        existing = True
    except Breakpoint.DoesNotExist:
        existing = False
        breakpoint = Breakpoint() 

        breakpoint.xpos = xpos
        breakpoint.project = project
        breakpoint.obs = int(bp['depth'])
        breakpoint.individual = Individual.objects.get(project=project, indiv_id=sample_id)
        breakpoint.sample_count = int(bp['sample_count'])
        breakpoint.partner = bp['partner']
        breakpoint.consensus = bp['cscore']
        breakpoint.save()

    for gene_symbol,cds_dist in zip(bp['genes'].split(','), bp['cdsdist'].split(',')):
        if gene_symbol:
            if existing:
                try:
                    gene = BreakpointGene.objects.get(breakpoint=breakpoint,
                                                      gene_symbol=gene_symbol)
                except BreakpointGene.DoesNotExist:
                    gene = BreakpointGene()
            else:
                gene = BreakpointGene()

            gene.breakpoint = breakpoint
            gene.gene_symbol = gene_symbol
            gene.cds_dist = int(cds_dist)
            gene.save()

  
                            