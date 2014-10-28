from collections import OrderedDict
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project


class Command(BaseCommand):
    def handle(self, *args, **options):
        # use OrderedDict as an ordered set
        vcf_file_paths = OrderedDict()
        projects_by_most_recent = Project.objects.all().order_by('-last_accessed_date')
        for project in projects_by_most_recent:
            for vcf in project.get_all_vcf_files():
                vcf_file_paths[vcf.path()] = None
        for vcf_path in vcf_file_paths.keys():
            print vcf_path
