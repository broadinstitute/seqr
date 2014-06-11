from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project


class Command(BaseCommand):

    def handle(self, *args, **options):
        project = Project.objects.get(project_id=args[0])

        for vcf in project.get_all_vcf_files():
            print '\t'.join(['VCF', vcf.path()])

        for i in project.get_individuals():
            if i.exome_depth_file:
                print '\t'.join(['CNV', i.indiv_id, i.exome_depth_file])