from django.core.management.base import BaseCommand
from optparse import make_option
import settings

from xbrowse_server.base.models import Project

class Command(BaseCommand):
    """Command to print out basic stats on some or all projects. Optionally takes a list of project_ids. """

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')
        parser.add_argument('-s', '--simple', action="store_true", help="List only the project ids"),


    def handle(self, *args, **options):
        if args:
            projects = []
            for arg in args:
                if Project.objects.filter(project_id=arg):
                    projects.append(Project.objects.get(project_id=arg))
                else: 
                    projects.extend([p for p in Project.objects.all() if arg.lower() in p.project_id.lower()])
                    print("project: %s doesn't exist" % arg)
        else:
            projects = Project.objects.all()

        if options.get('simple'):
            print("\t".join(["project id", "readviz enabled", "phenotips enabled", "collaborators"]))
            for project in projects:
                has_phenotips = project.project_id not in settings.PROJECTS_WITHOUT_PHENOTIPS
                has_readviz = any([i.bam_file_path for i in project.get_individuals()])
                print("\t".join(map(str, [project.project_id, "readviz-enabled" if has_readviz else "", "phenotips-enabled" if has_phenotips else "", ", ".join([(c.email or c.username) for c in project.collaborators.all()])])))
            return

        for project in projects:
            print("=============")
            print((
               "pk: %s - project id:   %s\n"
               "%3d families: %s\n"
               "%3d individuals: %s\n"
               "%3d collaborators: %s\n"
               "VCF files:\n%s"
               "reference populations: %s \n"
               "pedigree urls: %s \n"
               ) % (
                project.id,
                project.project_id,
                len({i.get_family_id() for i in project.get_individuals()} - {None,}),
                ", ".join([(family.family_id + "(%s)" % family.get_data_status()) for family in project.family_set.all()]),
                len(project.get_individuals()),
                ", ".join([(i.indiv_id + " (phenotips:%s) (has_variant_data: %s)\n" % (i.phenotips_id, i.has_variant_data())) for i in project.get_individuals()]),
                len(project.collaborators.all()),
                [u.email for u in project.collaborators.all()],
                "\n".join([v.path() for v in project.get_all_vcf_files()]) + "\n",
                ",".join([p.slug + " name: " + p.name for p in project.private_reference_populations.all()]),
                #project.families_by_vcf().items()
                ", ".join([f.pedigree_image.url for f in project.family_set.all() if f.pedigree_image]),                
                ))
            print("%d individuals have, %d don't have readviz" % ( len([i.bam_file_path for i in project.get_individuals() if i.bam_file_path]), 
                                                                   len([i.bam_file_path for i in project.get_individuals() if not i.bam_file_path]) ))
            print("Don't have readviz: " + ", ".join([i.indiv_id for i in project.get_individuals() if not i.bam_file_path]))
