from django.conf import settings

from xbrowse_server.base.model_utils import update_xbrowse_model, delete_xbrowse_model, get_or_create_xbrowse_model
from xbrowse_server.base.models import Project, Family, Individual, Cohort, ProjectPhenotype, IndividualPhenotype, FamilyGroup
from xbrowse import fam_stuff
from xbrowse_server.mall import get_mall, get_project_datastore
from xbrowse.utils import slugify


def add_indiv_ids_to_project(project, indiv_id_list):
    """
    Add these individuals if they don't already exist
    """
    for indiv_id in indiv_id_list:
        get_or_create_xbrowse_model(Individual, project=project, indiv_id=indiv_id)


def set_parents_for_individual(individual):
    """
    Sets family for an individual (creating if necessary)
    Saves both to db
    """
    project = individual.project
    if individual.paternal_id and individual.paternal_id != '.':
        father = get_or_create_xbrowse_model(Individual, project=project, indiv_id=individual.paternal_id)[0]
        update_xbrowse_model(father, family=individual.family)

    if individual.maternal_id and individual.maternal_id != '.':
        mother = get_or_create_xbrowse_model(Individual, project=project, indiv_id=individual.maternal_id)[0]
        update_xbrowse_model(mother, family=individual.family)


def set_individual_phenotypes_from_dict(individual, phenotype_dict):
    """
    Set the phenotypes for this indiviudal from dict
    Deletes all current phenotypes and rebuilds from phenotype_dict
    """

    for p in individual.get_phenotypes():
        p.delete()

    for phenotype_slug, value in phenotype_dict.items():
        project_phenotype = ProjectPhenotype.objects.get(slug=phenotype_slug, project=individual.project)
        indiv_phenotype = IndividualPhenotype.objects.create(
            individual=individual,
            phenotype=project_phenotype
        )
        if project_phenotype.datatype == 'bool':
            indiv_phenotype.boolean_val = value
        elif project_phenotype.datatype == 'number':
            indiv_phenotype.float_val = value
        indiv_phenotype.save()


def update_project_from_fam(project, fam_file, in_case_review=False):
    """
    Update project with the individuals in fam_file
    Create individuals and families if necessary and return a list of
    JSON obejcts representing the individual details
    """
    xindividuals = fam_stuff.get_individuals_from_fam_file(fam_file)

    individual_details=[]
    for ind in xindividuals:
        individual_details.append(ind.toJSON())
    individuals = update_project_from_individuals(project, xindividuals)
    if in_case_review:
        for ind in individuals:
            ind.in_case_review = True
            if not ind.case_review_status:
                update_xbrowse_model(ind, case_review_status='I')
            else:
                print("ERROR: case review status already set to" + ind.case_review_status)


    return individual_details


def update_project_from_individuals(project, xindividuals):
    # make sure families exist
    families = {}
    for family_id in set([xindividual.family_id for xindividual in xindividuals]):
        family, _ = get_or_create_xbrowse_model(Family, family_id=family_id, project=project)
        families[family_id] = family

    individuals = []
    for xindividual in xindividuals:
        individual, _ = get_or_create_xbrowse_model(
            Individual,
            project=project,
            family=families[xindividual.family_id],
            indiv_id=xindividual.indiv_id)

        individual.from_xindividual(xindividual)
        individuals.append(individual)

        #set_parents_for_individual(individual)

    return individuals


def add_cohort(project, cohort_id, indiv_id_list):
    """
    Create a cohort in project with these individuals
    """
    cohort = Cohort.objects.create(project=project, cohort_id=cohort_id)
    for indiv_id in indiv_id_list:
        individual = Individual.objects.get(project=project, indiv_id=indiv_id)
        cohort.individuals.add(individual)
    return cohort


def delete_project(project_id, delete_data=False):
    """
    Delete a project and perform any cleanup (ie. deleting from datastore and removing temp files)
    """
    project = Project.objects.get(project_id=project_id)
    if delete_data:
        get_project_datastore(project).delete_project_store(project_id)
        get_mall(project).variant_store.delete_project(project_id)

    project.individual_set.all().delete()
    project.family_set.all().delete()
    project.delete()

def delete_family(project_id, family_id):
    """
    Delete a project and perform any cleanup (ie. deleting from datastore and removing temp files)
    """
    family = Family.objects.get(project__project_id=project_id, family_id=family_id)
    for individual in family.get_individuals():
        update_xbrowse_model(individual, family=None)

    get_mall(project_id).variant_store.delete_family(project_id, family_id)
    delete_xbrowse_model(family)


def copy_project(from_project_id, to_project_id):
    """

    """

    # project

    # each individual

    # update family meta

    # update cohort meta
    pass


def add_vcf_file_to_individual(individual, vcf_file):
    """
    Add vcf_file to this individual
    Raise if indiv not in vcf
    """
    if individual.indiv_id not in vcf_file.sample_id_list():
        raise Exception("Individual %s is not in VCF file" % individual.indiv_id)
    individual.vcf_files.add(vcf_file)


def add_vcf_file_to_project(project, vcf_file):
    """
    Add this VCF file to all the individuals in project that are in the VCF file
    """
    vcf_sample_ids = set(vcf_file.sample_id_list())
    vcf_id_map = {slugify(s, separator='_', replace_dot=True): s for s in vcf_sample_ids}
    for individual in project.individual_set.all():
        if individual.indiv_id in vcf_id_map:
            individual.vcf_files.add(vcf_file)
            if individual.indiv_id != vcf_id_map[individual.indiv_id]:
                individual.vcf_id = vcf_id_map[individual.indiv_id]
                individual.save()


def create_family_group(project, family_list, slug):
    """
    Make a FamilyGroup in project for the families in family_list
    """
    family_group = FamilyGroup.objects.create(project=project, slug=slug, name=slug, description="")
    for family in family_list:
        family_group.families.add(family)
    return family_group
