from django.core.management.base import BaseCommand

from seqr.models import Project, Individual


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('project_id')
        parser.add_argument('tsv_file')

    def handle(self, *args, **options):
        project_id = options['project_id']
        tsv_path = options['tsv_file']

        project = Project.objects.get(deprecated_project_id=project_id)

        for line in open(tsv_path):
            fields = line.rstrip('\n').split('\t')

            assert len(fields) > 1
            indiv_id = fields[0]
            notes = fields[1].strip()
            if not notes:
                continue

            i = Individual.objects.get(individual_id=indiv_id)
            i.notes = (i.notes or "") + notes
            i.save()