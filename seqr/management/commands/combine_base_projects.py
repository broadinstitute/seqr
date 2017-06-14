"""
This script can be used to combining multiple projects (containing either the same or different types of data)
into 1 joint project. For example it can combine 2 WES projects or a WES and a WGS project.
"""

import json
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from seqr.management.commands.utils.combine_utils import choose_one, ask_yes_no_question
from seqr.views.apis.phenotips_api import update_patient_data
from xbrowse_server.base.models import Project, ProjectCollaborator, Project, \
    Family, FamilyImageSlide, Cohort, Individual, FamilyGroup, \
    CausalVariant, ProjectTag, VariantTag, VariantNote, ReferencePopulation, \
    UserProfile, VCFFile, ProjectGeneList
from xbrowse_server.phenotips.utilities import add_individuals_to_phenotips, \
    create_user_in_phenotips


def update(mongo_collection, match_json, set_json, upsert=False):
    print("-----")
    print("updating %s to %s" % (match_json, set_json))
    update_result = mongo_collection.update(match_json, {'$set': set_json}, upsert=upsert)
    print("updated %s" % (str(update_result)))
    return update_result

logger = logging.getLogger(__name__)



class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--project-name', help='new project name')
        parser.add_argument('--project-description', help='new project description')
        parser.add_argument('to_project', help='Data will be combined into this project. It this project doesn\'t exist, it will be created.')
        parser.add_argument('from_project', help='Data will be parsed from this project, and this project will be deleted')
        parser.add_argument('from_project_datatype', help='project_b datatype', choices=["WES", "WGS", "RNA"])

    def handle(self, *args, **options):
        to_project_id = options["to_project"]
        from_project_id = options["from_project"]
        from_project_datatype = options["from_project_datatype"]
        assert from_project_id
        assert to_project_id

        print("=============================")
        print("Transferring metadata from project %s to %s" % (from_project_id, to_project_id))
        if not ask_yes_no_question("Continue?"):
            return

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

        # Project
        to_project, created = Project.objects.get_or_create(project_id=to_project_id)

        if created:
            print("--> Created project: " + str(to_project))
            to_project.created_date = timezone.now()
        else:
            print("--> Transferring into existing project: " + str(to_project))

        from_project = Project.objects.get(project_id=from_project_id)

        to_project.project_name = choose_one(to_project, 'project_name', from_project.project_name, to_project.project_name)
        to_project.description = choose_one(to_project, 'description', from_project.description, to_project.description)

        # Copy gene list
        for project_gene_list in ProjectGeneList.objects.filter(project=from_project):
            print("-->   Adding gene list: " + project_gene_list.gene_list.slug)
            ProjectGeneList.objects.get_or_create(project=to_project, gene_list=project_gene_list.gene_list)

        # Reference Populations
        for reference_population in from_project.private_reference_populations.all():
            if not to_project.private_reference_populations.filter(pk=reference_population.pk).exists():
                print("-->   Adding private reference population: " + reference_population.slug)
                to_project.private_reference_populations.add(reference_population)

        # set combined_projects_info
        if to_project.combined_projects_info:
            combined_projects_info = json.loads(to_project.combined_projects_info)
        else:
            combined_projects_info = {}

        combined_projects_info.update({from_project_datatype: {'project_id': from_project.project_id}})

        to_project.combined_projects_info = json.dumps(combined_projects_info)
        to_project.save()

        print("-->  Set project.combined_projects_info to %s" % (to_project.combined_projects_info, ))

        # Family
        to_family_id_to_family = {} # maps family_id to the to_family object
        from_families = Family.objects.filter(project=from_project)
        print("----> Transferring %s families" % len(from_families))
        for from_f in from_families:
            to_f, created = Family.objects.get_or_create(project=to_project, family_id=from_f.family_id)
            if created:
                print("----> Created family %s" % to_f.family_id)
            else:
                print("----> Transferring into existing family %s (%s)" % (to_f.family_id, to_f.short_description))

            to_family_id_to_family[to_f.family_id] = to_f

            to_f.family_name = choose_one(to_f, 'family_name', from_f.family_name, to_f.family_name)
            to_f.short_description = choose_one(to_f, 'short_description', from_f.short_description, to_f.short_description)

            to_f.about_family_content = choose_one(to_f, 'about_family_content', from_f.about_family_content, to_f.about_family_content)

            to_f.analysis_summary_content = choose_one(to_f, 'analysis_summary_content', from_f.analysis_summary_content, to_f.analysis_summary_content)

            to_f.pedigree_image = None         # choose_one(to_f, 'pedigree_image', from_f.pedigree_image, to_f.pedigree_image)
            to_f.pedigree_image_height = None  # choose_one(to_f, 'pedigree_image_height', from_f.pedigree_image_height, to_f.pedigree_image_height)
            to_f.pedigree_image_width = None   # choose_one(to_f, 'pedigree_image_width', from_f.pedigree_image_width, to_f.pedigree_image_width)

            to_f.analysis_status = choose_one(to_f, 'analysis_status', from_f.analysis_status, to_f.analysis_status, default_value='Q')
            to_f.analysis_status_date_saved = choose_one(to_f, 'analysis_status_date_saved', from_f.analysis_status_date_saved, to_f.analysis_status_date_saved)
            to_f.analysis_status_saved_by = choose_one(to_f, 'analysis_status_saved_by', from_f.analysis_status_saved_by, to_f.analysis_status_saved_by)
            to_f.causal_inheritance_mode = choose_one(to_f, 'causal_inheritance_mode', from_f.causal_inheritance_mode, to_f.causal_inheritance_mode)

            to_f.internal_case_review_notes = choose_one(to_f, 'internal_case_review_notes', from_f.internal_case_review_notes, to_f.internal_case_review_notes)
            to_f.internal_case_review_summary = choose_one(to_f, 'internal_case_review_summary', from_f.internal_case_review_summary, to_f.internal_case_review_summary)

            # combined families info
            if to_f.combined_families_info:
                combined_families_info = json.loads(to_f.combined_families_info)
            else:
                combined_families_info = {}

            combined_families_info.update({from_project_datatype: {'project_id': from_project.project_id, 'family_id': from_f.family_id}})

            to_f.combined_families_info = json.dumps(combined_families_info)
            to_f.save()
            print("---->  Set family.combined_families_info to %s" % (to_f.combined_families_info, ))


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
        print("-------> Transferring %s individuals" % len(Individual.objects.filter(project=from_project)))
        for from_family in Family.objects.filter(project=from_project):
            to_family = to_family_id_to_family[from_family.family_id]

            for from_i in Individual.objects.filter(project=from_project, family=from_family):
                to_i, created = Individual.objects.get_or_create(project=to_project, family=to_family, indiv_id=from_i.indiv_id)
                if created:
                    print("-------> Created individual %s" % to_i.indiv_id)
                else:
                    print("-------> Transferring into existing individual %s" % (to_i.indiv_id))


                to_i.created_date = choose_one(to_i, 'created_date', from_i.created_date, to_i.created_date, use_lower_value=True)
                to_i.maternal_id = choose_one(to_i, 'maternal_id', from_i.maternal_id, to_i.maternal_id)
                to_i.paternal_id = choose_one(to_i, 'paternal_id', from_i.paternal_id, to_i.paternal_id)
                to_i.gender = choose_one(to_i, 'gender', from_i.gender, to_i.gender, default_value='U')
                to_i.affected = choose_one(to_i, 'affected', from_i.affected, to_i.affected, default_value='U')

                to_i.nickname = choose_one(to_i, 'nickname', from_i.nickname, to_i.nickname)
                to_i.other_notes = choose_one(to_i, 'other_notes', from_i.other_notes, to_i.other_notes)

                to_i.case_review_status = choose_one(to_i, 'case_review_status', from_i.case_review_status, to_i.case_review_status)
                to_i.case_review_status_accepted_for = choose_one(to_i, 'case_review_status_accepted_for', from_i.case_review_status_accepted_for, to_i.case_review_status_accepted_for)

                to_i.phenotips_id = to_i.guid
                to_i.phenotips_data = choose_one(to_i, 'phenotips_data', from_i.phenotips_data, to_i.phenotips_data)
                # create phenotips patients and upload data


                to_i.mean_target_coverage = None
                to_i.coverage_status = choose_one(to_i, 'coverage_status', from_i.coverage_status, to_i.coverage_status, default_value='S')
                if from_i.bam_file_path:
                    if to_i.bam_file_path:
                        to_i.bam_file_path = to_i.bam_file_path + "," + from_i.bam_file_path
                    else:
                        to_i.bam_file_path = from_i.bam_file_path

                to_i.vcf_id = ''   # VCF ids will now be stored at the Sample not the Individual level

                for vcf_file in from_i.vcf_files.all():
                    if vcf_file not in to_i.vcf_files.all():
                        to_i.vcf_files.add(vcf_file)

                to_i.in_case_review = choose_one(to_i, 'in_case_review', from_i.in_case_review, to_i.in_case_review)

                # combined individuals info
                if to_i.combined_individuals_info:
                    combined_individuals_info = json.loads(to_i.combined_individuals_info)
                else:
                    combined_individuals_info = {}

                combined_individuals_info.update({from_project_datatype: {
                    'project_id': from_project.project_id,
                    'family_id': from_f.family_id,
                    'indiv_id': from_i.indiv_id}
                })

                to_i.combined_individuals_info = json.dumps(combined_individuals_info)
                to_i.save()

                print("------->  Set individual.combined_individuals_info to %s" % (to_i.combined_individuals_info, ))

            for from_v in CausalVariant.objects.filter(family=from_family):
                CausalVariant.objects.get_or_create(
                    family = to_family,
                    variant_type=from_v.variant_type,
                    xpos=from_v.xpos,
                    ref=from_v.ref,
                    alt=from_v.alt)

        # add this project to phenotips
        print("--> PHENOTIPS")
        create_user_in_phenotips(to_project.project_id, to_project.project_name)
        individuals_to_add = Individual.objects.filter(project=to_project, family=to_family)
        add_individuals_to_phenotips(to_project.project_id, [i.indiv_id for i in individuals_to_add])

        for i in individuals_to_add:
            if i.phenotips_data:
                to_project.phenotips_user_id = to_project.project_id
                try:
                    json_obj = json.loads(i.phenotips_data)
                    update_patient_data(to_project, i.phenotips_id, patient_json=json_obj, is_external_id=True)
                except Exception as e:
                    logger.error("%s - error while updating phenotips for %s: %s", e, i.phenotips_id, json_obj)

        # TODO: merge MME?
        from_variant_notes = VariantNote.objects.filter(project=from_project)
        print("--> Transferring %s VariantNotes:" % len(from_variant_notes))
        for from_vn in from_variant_notes:
            if from_vn.family and from_vn.family.family_id:
                to_family = to_family_id_to_family.get(from_vn.family.family_id)
            else:
                to_family = None

            _, created = VariantNote.objects.get_or_create(
                project=to_project,
                family=to_family,
                user=from_vn.user,
                date_saved=from_vn.date_saved,
                note=from_vn.note,
                xpos=from_vn.xpos,
                ref=from_vn.ref,
                alt=from_vn.alt)

            if created:
                print("-----> Created variant note %s:%s>%s" % (from_vn.xpos, from_vn.ref, from_vn.alt))

        from_project_tags = ProjectTag.objects.filter(project=from_project)
        print("--> Transferring %s ProjectTags" % len(from_project_tags))
        for from_ptag in from_project_tags:
            to_ptag, created = ProjectTag.objects.get_or_create(project=to_project, tag=from_ptag.tag)
            to_ptag.title = choose_one(to_ptag, 'title', from_ptag.title, to_ptag.title)
            to_ptag.category = choose_one(to_ptag, 'category', from_ptag.category, to_ptag.category)
            to_ptag.color = choose_one(to_ptag, 'color', from_ptag.color, to_ptag.color)
            to_ptag.order = choose_one(to_ptag, 'order', from_ptag.order, to_ptag.order)
            to_ptag.save()

            from_variant_tags = VariantTag.objects.filter(project_tag=from_ptag)
            print("-----> Transferring %s VariantTags for %s" % (len(from_variant_tags), from_ptag.tag))
            for from_vtag in from_variant_tags:
                if from_vtag.family and from_vtag.family.family_id:
                    to_family = to_family_id_to_family.get(from_vtag.family.family_id)
                else:
                    to_family = None

                _, created = VariantTag.objects.get_or_create(
                    family=to_family,
                    project_tag=to_ptag,
                    xpos=from_vtag.xpos,
                    ref=from_vtag.ref,
                    alt=from_vtag.alt)

                if created:
                    print("-----> Created variant tag %s:%s>%s" % (from_vtag.xpos, from_vtag.ref, from_vtag.alt))

        for project_gene_list in ProjectGeneList.objects.filter(project=from_project):
            project_gene_list, created = ProjectGeneList.objects.get_or_create(project=to_project, gene_list=project_gene_list.gene_list)

        # ProjectCollaborator
        collaborators = ProjectCollaborator.objects.filter(project=from_project)
        if len(collaborators) > 0:
            if not ask_yes_no_question("Transfer the %s collaborators?" % len(collaborators)):
                return

            print("Transferring the %s collaborators" % len(collaborators))
            for c in collaborators:
                _, created = ProjectCollaborator.objects.get_or_create(project=to_project, user=c.user, collaborator_type=c.collaborator_type)
                if created:
                    print("-----> Added %s %s" % (c.collaborator_type, c.user.email))