from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, Individual


class Command(BaseCommand):
    """
    Replace sample IDs in a project. Takes project ID and a 2 col TSV file with columns old_id, new_id
    """
    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        project = Project.objects.get(project_id=args[0])
        sample_map = dict(l.strip('\n').split('\t') for l in open(args[1]).readlines())

        # replace the actual sample IDs
        for old_id, new_id in sample_map.iteritems():
            try:
                indiv = Individual.objects.get(project=project, indiv_id=old_id)
            except ObjectDoesNotExist:
                continue
            indiv.indiv_id = new_id
            indiv.save()

        # replace the maternal and paternal IDs
        for individual in project.get_individuals():
            if individual.paternal_id in sample_map:
                individual.paternal_id = sample_map[individual.paternal_id]
                individual.save()
            if individual.maternal_id in sample_map:
                individual.maternal_id = sample_map[individual.maternal_id]
                individual.save()
