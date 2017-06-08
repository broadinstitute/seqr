from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ProjectCollaborator, Family, Individual, \
    FamilyGroup, CausalVariant, ProjectTag, VariantTag, VariantNote, ProjectGeneList



class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--gene-list', action="store_true", dest='gene_list', default=False)  # whether to only serialize the gene list
        parser.add_argument('-f', '--from-project', help="project id from which to transfer metadata")
        parser.add_argument('-t', '--to-project', help="project id to which to transfer metadata")

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

        # Project
        from_project = Project.objects.get(project_id=from_project_id)
        to_project = Project.objects.get(project_id=to_project_id)
        to_project.description = from_project.description
        to_project.save()

        # ProjectCollaborator
        for c in ProjectCollaborator.objects.filter(project=from_project):
            ProjectCollaborator.objects.get_or_create(project=to_project, user=c.user, collaborator_type=c.collaborator_type)

        # Reference Populations
        for reference_population in from_project.private_reference_populations.all():
            print("Adding private reference population: " + reference_population.slug)
            to_project.private_reference_populations.add(reference_population)
            to_project.save()

        # Family
        to_family_id_to_family = {} # maps family_id to the to_family object
        for from_f in Family.objects.filter(project=from_project):
            try:
                to_f = Family.objects.get(project=to_project, family_id=from_f.family_id)
                print("Matched family ids %s (%s) to %s (%s)" % (from_f.family_id, from_f.short_description, to_f.family_id, to_f.short_description)) 
            except Exception as e:
                print("WARNING - skipping family: " + from_f.family_id + ": " + str(e))
                continue

            to_family_id_to_family[to_f.family_id] = to_f
            to_f.family_name = from_f.family_name
            to_f.short_description = from_f.short_description
            to_f.about_family_content = from_f.about_family_content
            to_f.pedigree_image_height = from_f.pedigree_image_height
            to_f.pedigree_image_width = from_f.pedigree_image_width
            to_f.analysis_status = from_f.analysis_status
            to_f.causal_inheritance_mode = from_f.causal_inheritance_mode
            to_f.relatedness_matrix_json = from_f.relatedness_matrix_json
            to_f.variant_stats_json = from_f.variant_stats_json
            to_f.has_before_load_qc_error = from_f.has_before_load_qc_error
            to_f.before_load_qc_json = from_f.before_load_qc_json
            to_f.has_after_load_qc_error = from_f.has_after_load_qc_error
            to_f.has_after_load_qc_error = from_f.has_after_load_qc_error
            to_f.after_load_qc_json = from_f.after_load_qc_json 
            to_f.save()

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
            if not from_family.family_id in to_family_id_to_family:
                print("WARNING - skipping family: " + from_family.family_id)
                continue

            to_family = to_family_id_to_family[from_family.family_id]
            for from_i in Individual.objects.filter(project=from_project, family=from_family):
                try:
                    to_i = Individual.objects.get(project=to_project, family=to_family, indiv_id=from_i.indiv_id)
                except:
                    print("WARNING - skipping individual: " + str(from_i.indiv_id) + " in family " + from_family.family_id) 
                    continue
                to_i.nickname = from_i.nickname
                to_i.other_notes = from_i.other_notes
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

        #family_search_flag, created = FamilySearchFlag.objects.get_or_create(
        #    family = families[obj_fields['family']],
        #    xpos = obj_fields['xpos'],
        #    ref = obj_fields['ref'],
        #    alt = obj_fields['alt'],
        #    flag_type = obj_fields['flag_type'],
        #    suggested_inheritance = obj_fields['suggested_inheritance'], 
        #    date_saved = obj_fields['date_saved'],
        #    note = obj_fields['note'],
        #    )
        #family_search_flag.search_spec_json = obj_fields['search_spec_json']
        #family_search_flag.save()


    def handle(self, *args, **options):
        from_project_id = options["from_project"]
        to_project_id = options["to_project"]
        assert from_project_id
        assert to_project_id

        print("Transfering data from project %s to %s" % (from_project_id, to_project_id))
        if raw_input("Continue? [Y/n] ").lower() != 'y':
            return

        self.transfer_project(from_project_id, to_project_id)
        
