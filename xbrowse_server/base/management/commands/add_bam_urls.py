from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, Individual
from datasets.models import BAMFile


class Command(BaseCommand):

    def handle(self, *args, **options):

        project_id = args[0]
        project = Project.objects.get(project_id=project_id)

        for line in open(args[1]).readlines():
            indiv_id, bam_url = line.strip('\n').split('\t')
            indiv = Individual.objects.get(project=project, indiv_id=indiv_id)
            bam_file = BAMFile.objects.create(indiv_id=indiv_id, storage_mode='network', network_url=bam_url)
            indiv.bam_file = bam_file
            indiv.save()
