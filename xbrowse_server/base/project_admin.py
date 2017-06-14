from django.core.exceptions import ObjectDoesNotExist

from xbrowse_server.base.models import Individual, Family, Cohort, ProjectPhenotype, IndividualPhenotype, FamilySearchFlag, ProjectGeneList, \
    VariantNote, VariantTag, ProjectTag
from xbrowse_server import sample_management


def copy_project(from_project, to_project, samples=False, settings=False, upsert=False, users=False, saved_variants=False, data=False):
    """
    This is idempotent
    :param from_project:
    :param to_project:
    :param settings:
    :param upsert:
    :param users:
    :param saved_variants:
    :param data:
    :return:
    """

    # todo: put all the data copying (vcf, bam, coverage) in one section


    #
    # project settings
    #

    if settings:
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

    # collaborators
    if users:
        managers = from_project.get_managers()
        for m in managers:
            to_project.set_as_manager(m)

        collaborators = from_project.get_collaborators()
        for u in collaborators:
            to_project.set_as_collaborator(u)

    #
    # sample data
    #

    if samples:
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
    if saved_variants:

        # variant notes
        for from_note in VariantNote.objects.filter(project=from_project):
            to_note = VariantNote.objects.get_or_create(
                user=from_note.user,
                date_saved=from_note.date_saved,
                project=to_project,
                note=from_note.note,
                xpos=from_note.xpos,
                ref=from_note.ref,
                alt=from_note.alt,
            )[0]
            if from_note.family:
                to_note.family = Family.objects.get(project=to_project, family_id=from_note.family.family_id)
            if from_note.individual:
                to_note.individual = Individual.objects.get(project=to_project, indiv_id=from_note.individual.indiv_id)

        # variant tags
        # start with project tags
        # should these be in the --settings or --saved_variants parameters?
        for from_tag in ProjectTag.objects.filter(project=from_project):
            to_tag = ProjectTag.objects.get_or_create(
                project=to_project,
                tag=from_tag.tag,
                title=from_tag.title,
                color=from_tag.color,
            )[0]

        # now variant tags
        for from_tag in VariantTag.objects.filter(project_tag__project=from_project):
            to_project_tag = ProjectTag.objects.get(project=to_project, tag=from_tag.project_tag.tag)
            to_family = None
            if from_tag.family:
                to_family = Family.objects.get(project=to_project, family_id=from_tag.family.family_id)
            to_tag = VariantTag.objects.get_or_create(
                project_tag=to_project_tag,
                family=to_family,
                xpos=from_tag.xpos,
                ref=from_tag.ref,
                alt=from_tag.alt,
            )[0]
