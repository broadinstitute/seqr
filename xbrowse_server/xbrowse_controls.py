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

import json
import os
import platform
import sh
import gzip
import datetime
import tempfile
import shutil

from xbrowse_server.base.models import Project, Individual, Family, Cohort
from xbrowse import vcf_stuff
from xbrowse import genomeloc

from django.conf import settings
import xbrowse_annotation_controls


def reload_project(project_id, annotate=True):
    """
    Reload a whole project
    """
    print "Starting to reload {}".format(project_id)
    project = Project.objects.get(project_id=project_id)

    if annotate: 
        for vcf in project.get_all_vcf_files():
            settings.ANNOTATOR.add_vcf_file_to_annotator(vcf.path())

    reload_project_coverage(project_id)
    reload_project_variants(project_id)

    project.date_loaded = datetime.datetime.now()
    print "Finished reloading {}".format(project_id)


def reload_family_coverage(project_id, family_id):
    print "Loading coverage data for family %s / %s" % (project_id, family_id)
    family = Family.objects.get(project__project_id=project_id, family_id=family_id)

    # TODO: extract this out with the loading below
    for indiv in Individual.objects.filter(family=family):
        if indiv.coverage_file:
            settings.COVERAGE_STORE.add_sample(str(indiv.pk), gzip.open(indiv.coverage_file))


def reload_project_coverage(project_id):
    print "Loading coverage data for project %s" % project_id
    project = Project.objects.get(project_id=project_id)

    for indiv in Individual.objects.filter(project=project):
        if indiv.coverage_file:
            settings.COVERAGE_STORE.add_sample(str(indiv.pk), gzip.open(indiv.coverage_file))


def reload_family_variants(project_id, family_id):
    """
    Do everything in reload_project_variants just for a single family
    Family will have needs_reload=False at the end, but no guarantee about individuals or cohorts
    TODO: take Family, not IDs
    """
    print "Loading variants for family %s / %s" % (project_id, family_id)
    family = Family.objects.get(project__project_id=project_id, family_id=family_id)

    # some checks at the beginning for things that could mess us up in the interim
    vcf_files = family.get_vcf_files()
    if len(vcf_files) != 1:
        raise Exception("Family %s does not have exactly 1 VCF file" % family_id)

    _family_preprocessing(family)

    # delete if exists
    if settings.DATASTORE.family_exists(project_id, family_id):
        settings.DATASTORE.delete_family(project_id, family_id)

    # add
    settings.DATASTORE.add_family(project_id, family_id, family.indiv_ids_with_variant_data())

    # load
    settings.DATASTORE.load_family(
        project_id,
        family_id,
        vcf_files[0].path(),
        reference_populations=family.project.get_reference_population_slugs(),
    )

    # finish
    _family_postprocessing(family)


def reload_variants_for_family_list(project, families, vcf_file):
    """
    Reload variants for a list of families, all from the same vcf
    """
    for family in families:
        print "Adding {}".format(family.family_id)
        _family_preprocessing(family)

    family_list = []
    for family in families:
        family_list.append({
            'project_id': family.project.project_id,
            'family_id': family.family_id,
            'individuals': family.indiv_ids_with_variant_data(),
        })

    # add all families from this vcf to the datastore
    settings.DATASTORE.add_family_set(family_list)

    # load them all into the datastore
    family_tuple_list = [(f['project_id'], f['family_id']) for f in family_list]
    settings.DATASTORE.load_family_set(
        vcf_file,
        family_tuple_list,
        reference_populations=project.get_reference_population_slugs(),
    )

    # finish up each family
    for family in families:
        _family_postprocessing(family)


def reload_cohort_variants(project_id, cohort_id):
    """
    Analagous to reload_family_variants above - the two should be in sync
    """
    cohort = Cohort.objects.get(project__project_id=project_id, cohort_id=cohort_id)

    print "Loading variants for cohort %s / %s" % (project_id, cohort_id)

    cohort._needs_reload = False
    cohort.save()

    # some checks at the beginning for things that could mess us up in the interim
    vcf_files = cohort.get_vcf_files()
    if len(vcf_files) != 1:
        raise Exception("Cohort %s does not have exactly 1 VCF file" % cohort_id)
    for individual in cohort.get_individuals():
        if not individual.has_variant_data():
            raise Exception("Individual %s does not have variant data (and is in a cohort)" % individual.indiv_id)

    # delete if exists
    if settings.DATASTORE.family_exists(project_id, cohort_id):
        settings.DATASTORE.delete_family(project_id, cohort_id)

    # add
    settings.DATASTORE.add_family(project_id, cohort_id, cohort.indiv_id_list())

    # load
    settings.DATASTORE.load_family(
        project_id,
        cohort_id,
        vcf_files[0].path(),
        reference_populations=cohort.project.get_reference_population_slugs(),
    )

    cohort.save()


def reload_project_variants(project_id):
    """
    Reload all variant data for this project
    All families, cohorts, individuals in this project will have needs_upload=False at the end

    Plan to switch to the following setup:
    - load all individual variant data
    - index all families and cohorts (together) in datastore
    - postprocess each family
    - postprocess each cohort
    """
    print "Loading project %s" % project_id
    project = Project.objects.get(project_id=project_id)

    # first remove any trace of this project from datastore
    settings.DATASTORE.delete_project(project_id)

    for family in project.get_families():
        _family_preprocessing(family)

    # batch load families by VCF file
    # will remove this when decouple family from vcf
    for vcf_file, families in project.families_by_vcf().items():
        for i in xrange(0, len(families), settings.FAMILY_LOAD_BATCH_SIZE):
            reload_variants_for_family_list(project, families[i:i+settings.FAMILY_LOAD_BATCH_SIZE], vcf_file)

    # now load cohorts
    # these should be loaded as a family
    for cohort in project.cohort_set.all():
        reload_cohort_variants(project_id, cohort.cohort_id)

    print "Finished loading project %s!" % project_id


def _family_preprocessing(family):

    family._needs_reload = False
    family.save()


def _family_postprocessing(family):

    family._needs_reload = False
    family.save()




def preload_vep_vcf_annotations(vcf_file_path):
    settings.ANNOTATOR.preload_vep_annotated_vcf(open(vcf_file_path))





def reload_project_datastore(project_id):
    """
    Load this project into the project datastore
    Which allows queries over all variants in a project
    """
    project = Project.objects.get(project_id=project_id)
    settings.PROJECT_DATASTORE.delete_project(project_id)
    settings.PROJECT_DATASTORE.add_project(project_id, project.get_reference_population_slugs())
    for vcf_file in project.get_all_vcf_files():
        project_indiv_ids = [i.indiv_id for i in project.get_individuals()]
        vcf_ids = vcf_file.sample_id_list()
        indiv_id_list = [i for i in project_indiv_ids if i in vcf_ids]
        settings.PROJECT_DATASTORE.add_variants_to_project_from_vcf(
            vcf_file.file_handle(),
            project_id,
            indiv_id_list=indiv_id_list
        )


def write_snp_fileset(family, output_dir_path):
    """
    Write a set of files for a family that can be passed to linkage engine
    Creates the following files:
        variants.txt
        [family_id].fam
        markers.txt
        disease_model.json
    """

    individuals = family.get_individuals()

    # fam file
    fam_file_path = os.path.join(output_dir_path, family.family_id + '.fam')
    f = open(fam_file_path, 'w')
    for indiv in individuals:
        fields = [
            family.family_id,
            indiv.indiv_id,
            indiv.paternal_id if indiv.paternal_id else '.',
            indiv.maternal_id if indiv.maternal_id else '.',
            '2' if indiv.gender == 'F' else ('1' if indiv.gender == 'F' else '0'),
            '2' if indiv.affected == 'A' else ('1' if indiv.affected == 'N' else '0'),
        ]
        f.write('\t'.join(fields)+'\n')
    f.close()

    # markers.txt
    markers_path = os.path.join(output_dir_path, 'markers.txt')
    shutil.copy(settings.COMMON_SNP_FILE, markers_path)

    # disease model
    disease_model_path = os.path.join(output_dir_path, 'disease_model.txt')
    f = open(disease_model_path, 'w')
    f.writelines([
        "DD\t.001\n",
        "Dd\t.001\n",
        "dd\t.999\n",
    ])
    f.close()

    # variants.txt
    variants_file_path = os.path.join(output_dir_path, 'variants.txt')
    f = open(variants_file_path, 'w')
    f.write('#CHR\tPOS\tREF\tALT')
    for indiv in individuals:
        f.write('\t'+indiv.indiv_id)
    f.write('\n')
    for _line in open(settings.COMMON_SNP_FILE):
        fields = _line.strip('\n').split('\t')
        xpos = genomeloc.get_single_location('chr'+fields[0], int(fields[1]))
        ref = fields[2]
        alt = fields[3]
        variant = settings.DATASTORE.get_single_variant(family.project.project_id, family.family_id, xpos, ref, alt)
        fields = [
            fields[0],
            fields[1],
            fields[2],
            fields[3],
        ]
        for indiv in individuals:
            if variant:
                genotype = variant.get_genotype(indiv.indiv_id)
                fields.append(str(genotype.num_alt) if genotype.num_alt is not None else '.')
            else:
                fields.append('0')
        f.write('\t'.join(fields)+'\n')
    f.close()


