from django.core.exceptions import ObjectDoesNotExist

from xbrowse_server.base.models import Individual, Family, Cohort, ProjectPhenotype, IndividualPhenotype, FamilySearchFlag, ProjectGeneList
from xbrowse_server import sample_management


def copy_project(from_project, to_project, upsert=False, users=False, flags=False, data=False, all=False):

    # todo: put all the data copying (vcf, bam, coverage) in one section

    if all:
        upsert = True
        users = True
        flags = True

    #
    # project settings
    #

    # collaborators
    if users:
        managers = from_project.get_managers()
        for m in managers:
            to_project.set_as_manager(m)

        collaborators = from_project.get_collaborators()
        for u in collaborators:
            to_project.set_as_collaborator(u)

    # gene lists
    for d in from_project.get_gene_lists():
        ProjectGeneList.objects.create(gene_list=d, project=to_project)

    # reference populations
    for r in from_project.get_private_reference_populations():
        to_project.private_reference_populations.add(r)

    # phenotypes
    for from_p in from_project.get_phenotypes():
        to_p = ProjectPhenotype.objects.get_or_create(
            project=to_project,
            slug=from_p.slug,
            category=from_p.category,
            datatype=from_p.datatype,
            name=from_p.name,
        )[0]


    #
    # sample data
    #

    # individuals with phenotypes
    for from_individual in from_project.individual_set.all():
        if upsert:
            to_individual = Individual.objects.get_or_create(indiv_id=from_individual.indiv_id, project=to_project)[0]
        else:
            try:
                to_individual = Individual.objects.get(indiv_id=from_individual.indiv_id, project=to_project)
            except ObjectDoesNotExist:
                continue

        to_individual.nickname = from_individual.nickname
        to_individual.gender = from_individual.gender
        to_individual.affected = from_individual.affected
        to_individual.paternal_id = from_individual.paternal_id
        to_individual.maternal_id = from_individual.maternal_id
        to_individual.other_notes = from_individual.other_notes
        if data:
            to_individual.coverage_file = from_individual.coverage_file
        to_individual.save()

        if data:
            for vcf in from_individual.vcf_files.all():
                to_individual.vcf_files.add(vcf)

        # individual phenotypes
        for from_phenotype in from_individual.get_phenotypes():

            # project phenotype should already exist
            project_phenotype = ProjectPhenotype.objects.get(project=to_project,
                slug=from_phenotype.phenotype.slug,
                category=from_phenotype.phenotype.category,
                datatype=from_phenotype.phenotype.datatype
            )
            individual_phenotype = IndividualPhenotype.objects.get_or_create(
                phenotype=project_phenotype,
                individual=to_individual
            )[0]
            individual_phenotype.boolean_val = from_phenotype.boolean_val
            individual_phenotype.float_val = from_phenotype.float_val
            individual_phenotype.save()

        if from_individual.family:
            sample_management.set_family_id_for_individual(to_individual, from_individual.family.family_id)

    # families
    for from_family in from_project.family_set.all():
        try:
            to_family = Family.objects.get(project=to_project, family_id=from_family.family_id)
        except ObjectDoesNotExist:
            continue

        to_family.family_name = from_family.family_name
        to_family.short_description = from_family.short_description
        to_family.about_family_content = from_family.about_family_content
        to_family.analysis_status = from_family.analysis_status
        to_family.save()

    def can_copy_cohort_into_project(cohort, to_project):
        for individual in cohort.individuals.all():
            if not Individual.objects.filter(project=to_project, indiv_id=individual.indiv_id).exists():
                return False
        return True

    # cohorts
    for from_cohort in from_project.cohort_set.all():

        if not can_copy_cohort_into_project(from_cohort, to_project):
            print "Warning: could not load cohort %s" % from_cohort.cohort_id
            continue

        to_cohort = Cohort.objects.get_or_create(project=to_project, cohort_id=from_cohort.cohort_id)[0]
        to_cohort.display_name = from_cohort.display_name
        to_cohort.short_description = from_cohort.short_description
        to_cohort.save()
        for from_i in from_cohort.individuals.all():
            to_i = Individual.objects.get(project=to_project, indiv_id=from_i.indiv_id)
            to_cohort.individuals.add(to_i)

    # flags
    if flags:
        for from_flag in FamilySearchFlag.objects.filter(family__project=from_project):
            try:
                to_family = Family.objects.get(family_id=from_flag.family.family_id, project=to_project)
            except ObjectDoesNotExist:
                continue

            to_flag = FamilySearchFlag.objects.get_or_create(
                user=from_flag.user,
                family=to_family,
                xpos=from_flag.xpos,
                ref=from_flag.ref,
                alt=from_flag.alt,
                flag_type=from_flag.flag_type,
                suggested_inheritance=from_flag.suggested_inheritance,
                date_saved=from_flag.date_saved,
                note=from_flag.note
            )[0]