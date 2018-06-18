import sys
from django.core.management.base import BaseCommand

from xbrowse_server.base.model_utils import get_or_create_xbrowse_model, update_xbrowse_model
from xbrowse_server.base.models import Project, ProjectTag, Family 


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')
        parser.add_argument('--all', help="Add tags to all projects", action="store_true")

    def handle(self, *args, **options):
        if options["all"]:
            project_ids = [p.project_id for p in Project.objects.all()]
        else:
            if len(args) < 1:
                sys.exit("ERROR: must specify 1 or more project ids on the command line or use the --all option to work on all projects")

            project_ids = args

        for project_id in project_ids:
            print("="*30)
            print("====== %20s ===========" % project_id)
            print("="*30)
            
            project = Project.objects.get(project_id=project_id)
            get_or_create_project_tag(project, order=1, category="CMG Discovery Tags", tag_name="Tier 1 - Novel gene and phenotype", color='#03441E', description="Gene not previously associated with a Mendelian condition")
            get_or_create_project_tag(project, order=2, category="CMG Discovery Tags", tag_name="Tier 1 - Novel gene for known phenotype", color='#096C2F', description="Phenotype known but no causal gene known (includes adding to locus heterogeneity)")
            get_or_create_project_tag(project, order=3, category="CMG Discovery Tags", tag_name="Tier 1 - Phenotype expansion", color='#298A49', description="Phenotype studies have different clinical characteristics and/or natural history")
            get_or_create_project_tag(project, order=4, category="CMG Discovery Tags", tag_name="Tier 1 - Phenotype not delineated", color='#44AA60', description="Phenotype not previously delineated (i.e. no MIM #)")
            get_or_create_project_tag(project, order=5, category="CMG Discovery Tags", tag_name="Tier 1 - Novel mode of inheritance", color='#75C475', description="Gene previously associated with a Mendelian condition but mode of inheritance is different")
            get_or_create_project_tag(project, order=6, category="CMG Discovery Tags", original_names=["Novel Gene"], tag_name="Tier 2 - Novel gene and phenotype", color='#0B437D', description="Gene not previously associated with a Mendelian condition")
            get_or_create_project_tag(project, order=7, category="CMG Discovery Tags", original_names=["Known Gene Phenotype Expansion"], tag_name="Tier 2 - Novel gene for known phenotype", color='#1469B0', description="Phenotype known but no causal gene known (includes adding to locus heterogeneity)")
            get_or_create_project_tag(project, order=7.5, category="CMG Discovery Tags", original_names=[], tag_name="Tier 2 - Phenotype expansion", color='#318CC2', description="Phenotype studies have different clinical characteristics and/or natural history")
            get_or_create_project_tag(project, order=8, category="CMG Discovery Tags", tag_name="Tier 2 - Phenotype not delineated", color='#5383aa', description="Phenotype not previously delineated (i.e. no OMIM #)")

            get_or_create_project_tag(project, order=9, category="CMG Discovery Tags", tag_name="Known gene for phenotype", color='#030A75', description="The gene overlapping the variant has been previously associated with the same phenotype presented by the patient")
            get_or_create_project_tag(project, order=10, category="Collaboration", original_names=["Review", "Interesting"], tag_name="Review", description="To mark a variant and/or gene of interest for further review.", color='#668FE3')

            get_or_create_project_tag(project, order=10.3, category="Collaboration", original_names=[], tag_name="Send for Sanger validation", description="Send for Sanger validation", color='#f1af5f')
            get_or_create_project_tag(project, order=10.31, category="Collaboration", original_names=[], tag_name="Sanger validated", description="Confirmed by Sanger sequencing", color='#b2df8a')
            get_or_create_project_tag(project, order=10.32, category="Collaboration", original_names=[], tag_name="Sanger did not validate", description="Sanger did not validate", color='#823a3a')

            get_or_create_project_tag(project, order=10.5, category="Collaboration", tag_name="Excluded", description="To mark a variant and/or gene you previously reviewed but do not think it contributing to the phenotype in this case. To help other members of your team (and yourself), please consider also adding a note with details of why you reprioritized this variant.", color='#555555')

            get_or_create_project_tag(project, order=11, category="ACMG Variant Classification", tag_name="Pathogenic", description="", color='#B92732')  # red
            get_or_create_project_tag(project, order=15, category="ACMG Variant Classification", tag_name="Benign", description="", color='#2971B1')  # green6

            get_or_create_project_tag(project, order=12, category="ACMG Variant Classification", original_names=["LP"], tag_name="Likely Pathogenic", description="", color='#E48065')  # light red
            get_or_create_project_tag(project, order=13, category="ACMG Variant Classification", tag_name="VUS", description="Variant of uncertain significance", color='#FACCB4')  # gray
            get_or_create_project_tag(project, order=14, category="ACMG Variant Classification", original_names=["LB"], tag_name="Likely Benign", description="", color='#6BACD0')  # light green

            get_or_create_project_tag(project, order=16, category="ACMG Variant Classification", original_names=["Incidental Finding"], tag_name="Secondary finding", color="#FED82F", description="The variant was found during the course of searching for candidate disease genes and can be described as pathogenic or likely pathogenic according to ACMG criteria and overlaps a gene known to cause a disease that differs from the patient's primary indication for sequencing.")

            get_or_create_project_tag(project, order=17, category="Data Sharing", original_names=["MME"], tag_name="MatchBox (MME)", description="Gene, variant, and phenotype to be submitted to Matchmaker Exchange", color='#531B86')
            get_or_create_project_tag(project, order=18, category="Data Sharing", original_names=["clinvar"], tag_name="Submit to Clinvar", description="By selecting this tag, you are notifying CMG staff that this variant should be submitted to ClinVar. Generally, this is for pathogenic or likely pathogenic variants in known disease genes or for any benign or likely benign variants that are incorrectly annotated in ClinVar. Please also add a note that describes supporting evidence for how you interpreted this variant.", color='#8A62AE')
            get_or_create_project_tag(project, order=19, category="Data Sharing", original_names=[], tag_name="Share with KOMP", description="To mark a variant/gene that you would like us to share with the Mouse Knockout Project for their knockout and phenotyping pipeline. Add additional notes to comments as needed.", color='#ad627a')

        print("Done")


def get_or_create_project_tag(project, order, category, tag_name, description, color='#1f78b4', original_names=None):
    """
    Updates or creates a particular ProjectTag in a given project.

    Args:
        project (object): The project that contains this tag
        category (string):
        tag_name (string): The name of the new tag (can contain spaces)   (eg. "Causal Variant")
        description (string):  Longer description of the tag
        color (string): hex color (eg. "#123456")
        original_names (list): if the tag appeaered under one or more different names, remap these to the new tag_name

    Returns:
        new ProjectTag model object (or an existing one if a match was found)
    """

    project_tag = None
    if original_names:
        for original_name in original_names:
            tags = ProjectTag.objects.filter(project=project, tag__icontains=original_name, order__isnull=True)
            if tags:
                project_tag = tags[0]

    if project_tag is None:
        tags = ProjectTag.objects.filter(project=project, tag__iexact=tag_name)
        if tags:
            project_tag = tags[0]

    if project_tag is None:
        tags = ProjectTag.objects.filter(project=project, tag__icontains=tag_name)
        if tags:
            project_tag = tags[0]

    if project_tag is None:
        project_tag, created = get_or_create_xbrowse_model(ProjectTag, project=project, tag=tag_name)
        if created:
            print("Created new tag: %s :  %s" % (project, tag_name))

    update_xbrowse_model(
        project_tag,
        order=order,
        category=category,
        tag=tag_name,
        title=description,
        color=color)
