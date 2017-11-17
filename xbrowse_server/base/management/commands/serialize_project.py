import sys
from django.core.management.base import BaseCommand
from optparse import make_option
from django.contrib.auth.models import User
from xbrowse_server.base.models import Project, ProjectCollaborator, Project, \
    Family, FamilyImageSlide, Cohort, Individual, \
    FamilySearchFlag, ProjectPhenotype, IndividualPhenotype, FamilyGroup, \
    CausalVariant, ProjectTag, VariantTag, VariantNote, ReferencePopulation, \
    UserProfile, VCFFile, ProjectGeneList

from django.core import serializers
from xbrowse.utils import slugify


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

        parser.add_argument('--gene-list', action="store_true", dest='gene_list', default=False)  # whether to only serialize the gene list


    def write_out_project(self, project_id):
        """
        Method that takes a project id and writes out a "<project_id>.json" file
        containing a list of the following models in JSON format:

        ProjectCollaborator => user = models.ForeignKey(User), project = models.ForeignKey('base.Project'), collaborator_type = models.CharField(max_length=20, choices=COLLABORATOR_TYPES, default="collaborator")
        Project => (private_reference_populations = models.ManyToManyField(ReferencePopulation), gene_lists = models.ManyToManyField('gene_lists.GeneList', through='ProjectGeneList'))
        Family => Project,
        FamilyGroup => Project   (families = models.ManyToManyField(Family))
        FamilyImageSlide => Family
        Cohort => Project  (individuals = models.ManyToManyField('base.Individual'), vcf_files, bam_file)
        Individual => Project, Family  # vcf_files = models.ManyToManyField(VCFFile, null=True, blank=True), bam_file = models.ForeignKey('datasets.BAMFile', null=True, blank=True)
        FamilySearchFlag => User, Family
        CausalVariant => Family
        ProjectTag => Project
        VariantTag => ProjectTag, Family
        VariantNote => User, Project
        IndividualPhenotype => Individual, ProjectPhenotype
        ProjectPhenotype => Project
        """
        output_obj = []

        # Project
        project = Project.objects.get(project_id=project_id)
        output_obj += [project]

        # Users
        for user in User.objects.all():
            print(user.pk)
            output_obj.append(user)

        # ProjectCollaborator
        collaborators = list(ProjectCollaborator.objects.filter(project=project))
        output_obj += collaborators


        # Family
        families = list(Family.objects.filter(project=project))
        output_obj += families

        # FamilyGroup
        familyGroups = list(FamilyGroup.objects.filter(project=project))
        output_obj += familyGroups

        # FamilyImageSlide
        familyImageSlides = []
        for family in families:
            familyImageSlides.extend(
                list(FamilyImageSlide.objects.filter(family=family)))
        output_obj += familyImageSlides

        # Cohort
        cohorts = list(Cohort.objects.filter(project=project))
        output_obj += cohorts

        # Individual
        individuals = []
        for family in families:
            individuals.extend(
                list(Individual.objects.filter(project=project, family=family)))
        output_obj += individuals

        # CausalVariant
        causal_variants = []
        for family in families:
            causal_variants.extend(
                list(CausalVariant.objects.filter(family=family)))
        output_obj += causal_variants

        # ProjectTag
        project_tags = list(ProjectTag.objects.filter(project=project, ))
        output_obj += project_tags

        # VariantTag
        variant_tags = []
        for family in families:
            for project_tag in project_tags:
                variant_tags.extend(
                    list(VariantTag.objects.filter(
                        family=family, project_tag=project_tag)))
        output_obj += variant_tags

        # VariantNote
        variant_notes = list(VariantNote.objects.filter(project=project, ))
        output_obj += variant_notes

        # ProjectPhenotype
        project_phenotypes = list(ProjectPhenotype.objects.filter(project=project,))
        output_obj += project_phenotypes

        # IndividualPhenotype, VCFFiles
        individual_phenotypes = []
        vcf_files = []
        for individual in individuals:
            vcf_files.extend(list(individual.vcf_files.all()))
            #individual.bam_files.all()

            individual_phenotypes.extend(
                list(IndividualPhenotype.objects.filter(individual=individual)))
        output_obj += individual_phenotypes
        output_obj += vcf_files

        # ReferencePopulation
        reference_populations = list(project.private_reference_populations.all())
        output_obj += reference_populations

        # GeneList
        gene_lists = list(project.gene_lists.all())
        output_obj += gene_lists

        # GeneListItems
        for gene_list in gene_lists:
            output_obj += list(gene_list.genelistitem_set.all())

        # FamilySearchFlag
        family_search_flags = []
        for family in families:
            family_search_flags.extend(list(FamilySearchFlag.objects.filter(family=family)))
        output_obj += family_search_flags


        with open(project_id+".json", "w") as f:
            f.write(
                serializers.serialize("json", output_obj, indent=2))

    def write_out_gene_list(self, project_id):
        """
        Method that takes a project id and writes out a "<project_id>.json" file
        containing a list of the following models in JSON format:

        """
        project = Project.objects.get(project_id=project_id)

        output_obj = []


        # GeneList
        gene_lists = list(project.gene_lists.all())
        output_obj += gene_lists

        # GeneListItems
        for gene_list in gene_lists:
            output_obj += list(gene_list.genelistitem_set.all())


        with open(project_id+"_gene_lists.json", "w") as f:
            f.write(
                serializers.serialize("json", output_obj, indent=2))

    def handle(self, *args, **options):

        for project_id in args:
            if options.get('gene_list'):
                self.write_out_gene_list(project_id)
            else:
                print("Writing out project: " + project_id)
                self.write_out_project(project_id)

