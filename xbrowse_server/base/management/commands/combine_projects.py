import os

from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ProjectCollaborator, Project, \
    Family, FamilyImageSlide, Cohort, Individual, \
    FamilySearchFlag, ProjectPhenotype, IndividualPhenotype, FamilyGroup, \
    CausalVariant, ProjectTag, VariantTag, VariantNote, ReferencePopulation, \
    UserProfile, VCFFile, ProjectGeneList
from xbrowse_server.gene_lists.models import GeneList, GeneListItem
from xbrowse_server.mall import get_project_datastore, get_datastore

from django.core import serializers


def update(mongo_collection, match_json, set_json, upsert=False):
    print("-----")
    print("updating %s to %s" % (match_json, set_json))
    #return 
    update_result = mongo_collection.update(match_json, {'$set': set_json}, upsert=upsert)
    print("updated %s" % (str(update_result)))
    return update_result

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('-f', '--from-project', help="project id from which to copy metadata and link in data")
        parser.add_argument('-t', '--to-project', help="destination project id")

    def handle(self, *args, **options):
        from_project_id = options["from_project"]
        to_project_id = options["to_project"]
        assert from_project_id
        assert to_project_id

        print("Transferring data from project %s to %s" % (from_project_id, to_project_id))
        if raw_input("Continue? [Y/n] ").lower() != 'y':
            return

        self.transfer_project(from_project_id, to_project_id)

    def transfer_project(self, from_project_id, to_project_id):
        """
        The following models are transfered between projects.

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

        families_db = get_datastore()._db

        # Project
        from_project = Project.objects.get(project_id=from_project_id)
        to_project, created = Project.objects.get_or_create(project_id=to_project_id)
        if created:
            print("Created project: " + str(to_project))
        to_project.description = from_project.description
        to_project.save()

        # ProjectCollaborator
        #for c in ProjectCollaborator.objects.filter(project=from_project):
        #    ProjectCollaborator.objects.get_or_create(project=to_project, user=c.user, collaborator_type=c.collaborator_type)

        # Reference Populations
        for reference_population in from_project.private_reference_populations.all():
            print("Adding private reference population: " + reference_population.slug)
            to_project.private_reference_populations.add(reference_population)
            to_project.save()

        # Family
        to_family_id_to_family = {} # maps family_id to the to_family object
        for from_f in Family.objects.filter(project=from_project):

            to_f, created = Family.objects.get_or_create(project=to_project, family_id=from_f.family_id)
            if not created:
                print("Matched family ids %s (%s) to %s (%s)" % (from_f.family_id, from_f.short_description, to_f.family_id, to_f.short_description))

            to_family_id_to_family[to_f.family_id] = to_f

            to_f.family_name = from_f.family_name
            to_f.short_description = from_f.short_description

            to_f.about_family_content = from_f.about_family_content
            to_f.analysis_summary_content = from_f.analysis_summary_content
            to_f.coded_phenotype = from_f.coded_phenotype
            to_f.post_discovery_omim_number = from_f.post_discovery_omim_number

            to_f.pedigree_image = from_f.pedigree_image
            to_f.pedigree_image_height = from_f.pedigree_image_height
            to_f.pedigree_image_width = from_f.pedigree_image_width

            to_f.analysis_status = from_f.analysis_status
            to_f.analysis_status_date_saved = from_f.analysis_status_date_saved
            to_f.analysis_status_saved_by = from_f.analysis_status_saved_by
            to_f.causal_inheritance_mode = from_f.causal_inheritance_mode

            to_f.internal_case_review_notes = from_f.internal_case_review_notes
            to_f.internal_case_review_brief_summary = from_f.internal_case_review_brief_summary

            to_f.save()

            update(
                families_db.families, 
                {'project_id': to_project.project_id, 'family_id': to_f.family_id },
                { 
                    "status" : "loaded", 
                    "family_id" : to_f.family_id, 
                    "individuals" : [i.indiv_id for i in Individual.objects.filter(project=from_project, family=from_f)],
                    "coll_name" : "family_%s_%s" % (from_project.project_id, from_f.family_id), 
                    "project_id" : to_project.project_id
                },
                upsert=True
            )
            

        # FamilyGroup
        for from_fg in FamilyGroup.objects.filter(project=from_project):
            FamilyGroup.objects.get_or_create(project=to_project, slug=from_fg.slug, name=from_fg.name, description=from_fg.description)

        # FamilyImageSlide
        #for from_family in Family.objects.filter(project=from_project):
        # TODO - need to iterate over image slides of from_family, and link to image slides of to_family
        #        FamilyImageSlide.objects.get_or_create(family=to_family, )


        # Cohort
        #cohorts = list(Cohort.objects.filter(project=project))
        #output_obj += cohorts


        # Individual
        for from_family in Family.objects.filter(project=from_project):
            to_family = to_family_id_to_family[from_family.family_id]

            for from_i in Individual.objects.filter(project=from_project, family=from_family):
                to_i, created = Individual.objects.get_or_create(project=to_project, family=to_family, indiv_id=from_i.indiv_id)

                if not created:
                    print("matched existing individual: " + str(from_i.indiv_id) + " in family " + from_family.family_id)

                to_i.created_date = from_i.created_date

                to_i.affected = from_i.affected

                to_i.phenotips_id = from_i.phenotips_id
                to_i.phenotips_data = from_i.phenotips_data

                to_i.case_review_status = from_i.case_review_status

                to_i.mean_target_coverage = from_i.mean_target_coverage
                to_i.coverage_status = from_i.coverage_status
                to_i.bam_file_path = from_i.bam_file_path
                to_i.vcf_id = from_i.vcf_id

                to_i.gender = from_i.gender

                to_i.in_case_review = from_i.in_case_review
                

                to_i.nickname = from_i.nickname
                to_i.maternal_id = from_i.maternal_id
                to_i.paternal_id = from_i.paternal_id

                to_i.other_notes = from_i.other_notes

                for vcf_file in from_i.vcf_files.all():
                    if vcf_file not in to_i.vcf_files.all():
                        to_i.vcf_files.add(vcf_file)

                to_i.save()


            for from_v in CausalVariant.objects.filter(family=from_family):
                CausalVariant.objects.get_or_create(
                    family = to_family,
                    variant_type=from_v.variant_type,
                    xpos=from_v.xpos,
                    ref=from_v.ref,
                    alt=from_v.alt)

        for from_vn in VariantNote.objects.filter(project=from_project):
            if from_vn.family.family_id not in to_family_id_to_family:
                print("Skipping note: " + str(from_vn.toJSON()))
                continue
            to_family = to_family_id_to_family[from_vn.family.family_id]
            VariantNote.objects.get_or_create(
                project=to_project,
                family=to_family,
                user=from_vn.user,
                date_saved=from_vn.date_saved,
                note=from_vn.note,
                xpos=from_vn.xpos,
                ref=from_vn.ref,
                alt=from_vn.alt)

        for from_ptag in ProjectTag.objects.filter(project=from_project):
            to_ptag, created = ProjectTag.objects.get_or_create(project=to_project, tag=from_ptag.tag, title=from_ptag.title, color=from_ptag.color)
            for from_vtag in VariantTag.objects.filter(project_tag=from_ptag):
                if from_vtag.family.family_id not in to_family_id_to_family:
                    print("Skipping tag: " + str(from_vtag.xpos))
                    continue


                to_family = to_family_id_to_family[from_vtag.family.family_id]
                VariantTag.objects.get_or_create(
                    family=to_family,
                    project_tag=to_ptag,
                    xpos=from_vtag.xpos,
                    ref=from_vtag.ref,
                    alt=from_vtag.alt)


        for project_gene_list in ProjectGeneList.objects.filter(project=from_project):
            project_gene_list, created = ProjectGeneList.objects.get_or_create(project=to_project, gene_list=project_gene_list.gene_list)

