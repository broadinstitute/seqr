from django.core import serializers
import json
from django.core.management.base import BaseCommand
from optparse import make_option
from django.contrib.auth.models import User
from xbrowse_server.base.models import Project, ProjectCollaborator, Project, \
    Family, FamilyImageSlide, Cohort, Individual, DiseaseGeneList, \
    FamilySearchFlag, ProjectPhenotype, IndividualPhenotype, FamilyGroup, \
    CausalVariant, ProjectTag, VariantTag, VariantNote, ReferencePopulation, \
    UserProfile, VCFFile, ProjectGeneList
from xbrowse_server.gene_lists.models import GeneList, GeneListItem

from django.core import serializers
from slugify import slugify


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('-d', '--deserialize', action="store_true", dest='deserialize', default=False),
    )

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
        collaborators = list(ProjectCollaborator.objects.filter(project=project))
        for collaborator in collaborators:
            print(collaborator.user.pk)
            output_obj.append(collaborator.user)

        # ProjectCollaborator
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



    def load_project(self, project_id):
        #from collections import defaultdict
        #objects_by_pk = defaultdict(dict)
        print("------------------")
        project = None
        users = {}
        families = {}
        cohorts = {}
        individuals = {}
        project_tags = {}
        project_phenotypes = {}
        gene_lists = {}
        with open(project_id + ".json") as f:
            contents = f.read()
            raw_json_data = json.loads(contents)

            #obj_generator = serializers.json.Deserializer(contents)
            # Couldn't find a way to make Deserializer return foreign key ids
            for obj in raw_json_data:
                #print("Object: " + str(obj))
                obj_pk = obj['pk']
                obj_model = obj['model']
                obj_fields = obj['fields']
                if obj_model == 'base.project':
                    project = Project.objects.get(project_id=obj_fields['project_id'])
                    project.project_name = obj_fields['project_name']
                    project.description = obj_fields['description']
                    project.last_accessed_date = obj_fields['last_accessed_date']
                    if obj_fields['private_reference_populations']:
                        #raise ValueError("private_reference_populations not implemented: " + str(obj_fields['private_reference_populations']))
                        ""
                    if 'gene_lists' in obj_fields and obj_fields['gene_lists']:
                        raise ValueError("gene_lists not implemented: " + str(project.gene_lists.all()))

                    print("project: " + str(project))
                    project.save()
                elif obj_model == 'auth.user':
                    user = User.object.get_or_create(project=project,
                        username=obj_fields['username'],
                        first_name = obj_fields['first_name'],
                        last_name = obj_fields['last_name'],
                        email = obj_fields['email'])
                    user.is_active = bool(obj_fields['is_active']),
                    user.is_superuser = bool(obj_fields['is_superuser']),
                    user.is_staff = bool(obj_fields['is_staff']),
                    user.last_login = obj_fields['last_login']
                    user.groups = obj_fields['groups']
                    user.password = obj_fields['password']
                    user.date_joined = obj_fields['date_joined']
                    user.save()
                    users[obj_pk] = user
                elif obj_model == 'base.projectcollaborator':
                    collaborator = ProjectCollaborator.object.get_or_create(project=project, user=users[obj_fields["user"]])
                    collaborator.collaborator_type = obj_fields['collaborator_type']
                    collaborator.save()
                elif obj_model == 'base.family':
                    family = Family.objects.get(project=project, family_id=slugify(obj_fields['family_id']))
                    family.family_name = obj_fields['family_name']
                    family.short_description = obj_fields['short_description']
                    family.about_family_content = obj_fields['about_family_content']
                    if obj_fields['pedigree_image']:
                        raise ValueError("pedigree image not implemented")

                    family.pedigree_image_height = obj_fields['pedigree_image_height']
                    family.pedigree_image_width = obj_fields['pedigree_image_width']
                    family.analysis_status = obj_fields['analysis_status']
                    family.causal_inheritance_mode = obj_fields['causal_inheritance_mode']
                    family.relatedness_matrix_json = obj_fields['relatedness_matrix_json']
                    family.variant_stats_json = obj_fields['variant_stats_json']
                    family.has_before_load_qc_error = obj_fields['has_before_load_qc_error']
                    family.before_load_qc_json = obj_fields['before_load_qc_json']
                    family.has_after_load_qc_error = obj_fields['has_after_load_qc_error']
                    family.after_load_qc_json = obj_fields['after_load_qc_json']

                    families[obj_pk] = family
                    print("family: " + str(family))
                    family.save()

                elif obj_model == 'base.familygroup':
                    family_group, created = FamilyGroup.objects.get_or_create(project=project,
                        slug=obj_fields['slug'],
                        name=obj_fields['name'],
                        description=obj_fields['description'])
                    if not family_group.families.all():
                        for family_id in obj_fields['families']:
                            family_group.families.add(families[family_id])
                    print("familygroup: " + str(family_group))
                    family_group.save()
                elif obj_model == 'base.familyimageslide':
                    raise ValueError("FamilyImageSlide not implemented")
                elif obj_model == 'base.cohort':
                    cohorts[obj_pk] = obj
                    raise ValueError("Cohort not implemented")
                elif obj_model == "base.individual":
                    individual = individuals[obj_pk] = Individual.objects.get(project=project, indiv_id=obj_fields['indiv_id'])
                    individual.nickname = obj_fields['nickname']
                    individual.other_notes = obj_fields['other_notes']
                    print("individual: " + str(individual))
                    individual.save()
                elif obj_model == "base.causalvariant":
                    causal_variant, created = CausalVariant.objects.get_or_create(
                        family = families[obj_fields["family"]],
                        variant_type=obj_fields["variant_type"],
                        xpos=obj_fields["xpos"],
                        ref=obj_fields["ref"],
                        alt=obj_fields["alt"])
                    print("causalvariant: " + str(causal_variant))
                    causal_variant.save()
                elif obj_model == "base.projecttag":
                    project_tag, created = ProjectTag.objects.get_or_create(
                        project = project,
                        tag=obj_fields["tag"],
                        title=obj_fields["title"],
                        color=obj_fields["color"])
                    project_tags[obj_pk] = project_tag
                    print("projecttag: " + str(project_tag))
                    project_tag.save()
                elif obj_model == "base.varianttag":
                    variant_tag, created = VariantTag.objects.get_or_create(
                        project_tag = project_tags[obj_fields['project_tag']],
                        family=families[obj_fields["family"]],
                        xpos=obj_fields["xpos"],
                        ref=obj_fields["ref"],
                        alt=obj_fields["alt"])
                    print("varianttag: " + str(variant_tag))
                    variant_tag.save()
                elif obj_model == "base.variantnote":
                    variant_note, created = VariantNote.objects.get_or_create(
                        user=users[obj_fields['user']],
                        date_saved=obj_fields["date_saved"],
                        project=project,
                        note=obj_fields["note"],
                        xpos=obj_fields["xpos"],
                        ref=obj_fields["ref"],
                        alt=obj_fields["alt"],
                        family=families[obj_fields["family"]],
                        #individual=individuals[obj_fields["individual"]],
                    )
                    print("variant_note: " + str(variant_note))
                    variant_note.save()
                elif obj_model == "base.vcffile":
                    print(obj_fields)
                elif obj_model == "gene_lists.genelist":
                    gene_list, created = GeneList.objects.get_or_create(
                        slug = obj_fields['slug'],
                        name = obj_fields['name'],
                        description = obj_fields['description'],
                        is_public = False,
                        #owner = models.ForeignKey(User, null=True, blank=True),
                        last_updated = obj_fields['last_updated'],
                    )

                    project_gene_list, created = ProjectGeneList.objects.get_or_create(project=project, gene_list=gene_list)
                    project_gene_list.save()

                    gene_lists[obj_pk] = gene_list
                    #project.gene_lists.add(gene_list)
                    #gene_list.save()


                elif obj_model == "gene_lists.genelistitem":
                    gene_list_item, created = GeneListItem.objects.get_or_create(
                        gene_id = obj_fields['gene_id'],
                        gene_list = gene_lists[obj_fields['gene_list']],
                        description = obj_fields['description']
                    )
                    gene_list_item.save()

                elif obj_model == "base.referencepopulation":
                    print(obj_fields)
                elif obj_model == "base.projectphenotype":
                    project_phenotypes[obj_pk] = None
                    raise ValueError("base.projectphenotype not supported")
                elif obj_model == "base.individualphenotype":
                    raise ValueError("base.individualphenotype not supported")
                else:
                    raise ValueError("Unexpected obj_model: " + obj_model)

    def handle(self, *args, **options):

        if options.get('deserialize'):
            for project_id in args:
                print("Loading project: " + project_id)
                self.load_project(project_id)
        else:
            for project_id in args:
                print("Writing out project: " + project_id)
                self.write_out_project(project_id)



