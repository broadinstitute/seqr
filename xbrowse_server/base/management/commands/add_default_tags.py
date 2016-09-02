import sys
from optparse import make_option
from xbrowse_server import xbrowse_controls
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, ProjectTag, Family 


def get_or_create_project_tag(project, tag_name, description, color='#1f78b4'):
    """
    Gets or creates a particular ProjectTag in a given project.

    Args:
        project: The project that contains this tag
        tag_name: The name of the new tag (can contain spaces)   (eg. "Causal Variant")
        description:  (eg. "causal variant")

    Returns:
        new ProjectTag model object (or an existing one if a match was found)
    """
    project_tag, created = ProjectTag.objects.get_or_create(project=project, tag=tag_name)
    if created:
        print("Created new tag: %s :  %s" % (project, tag_name))

    project_tag.title=description
    project_tag.color=color
    project_tag.save()
        


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')
        parser.add_argument('-p', '--print-tags', help="Print what tags are bieng used", action="store_true")

    def handle(self, *args, **options):
        if len(args) < 1:
            sys.exit("ERROR: must specify 1 or more project_ids on the command line")

        project_ids = args

        if options["print_tags"]:
            for project in Project.objects.all():
                print("========")
                users = list(project.get_users())
                if users and len(ProjectTag.objects.filter(project=project, tag='VUS')) == 0: 
                    print("##### " + project.project_id + " #### " + ",".join(map(str, users)) + ", " + ("%s families" % len(Family.objects.filter(project=project))))
                    for project_tag in ProjectTag.objects.filter(project=project):       
                        print(project_tag.tag + ": " + project_tag.title)

        for project_id in project_ids:
            project = Project.objects.get(project_id=project_id)
            get_or_create_project_tag(project, tag_name="Review", description="", color='#88CCDD')  # blue
            get_or_create_project_tag(project, tag_name="Incidental Finding", description="", color='#FFAA33')  

            get_or_create_project_tag(project, tag_name="Novel Gene", description="", color='#FF0000')  # 4C0083
            get_or_create_project_tag(project, tag_name="Known Gene Phenotype Expansion", description="", color='#5521CC')  
            get_or_create_project_tag(project, tag_name="Known Gene for Phenotype", description="", color='#2177DD') 

            get_or_create_project_tag(project, tag_name="Pathogenic", description="Potential candidate gene", color='#AA1111')  # red
            get_or_create_project_tag(project, tag_name="Likely Pathogenic", description="Likely pathogenic", color='#FF9988')  # light red
            get_or_create_project_tag(project, tag_name="VUS", description="Uncertain significance", color='#AAAAAA')  # gray
            get_or_create_project_tag(project, tag_name="Likely Benign", description="Likely Benign", color='#B2DF8A')  # light green
            get_or_create_project_tag(project, tag_name="Benign", description="Strong evidence", color='#11AA11')  # green
        print("Done")
"""
 Review   Review 
 Incidental Finding   Incidental finding 
 Known Gene for Phenotype   Known gene for phenotype 
 Known Gene Phenotype Expansion   Known gene phenotype expansion 
 Novel Gene   Novel gene 
 Pathogenic   Potential candidate gene 
 Likely Pathogenic   Moderate and supporting evidence 
 VUS   Uncertain significance 
 Likely Benign   Moderate and supporting evidence 
 Benign   Strong evidence
"""
