from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from xbrowse_server.base.models import Project, Individual


class Command(BaseCommand):
    """
    Replace sample IDs in a project. Takes project ID and a 2 col TSV file with columns old_id, new_id
    """
    def handle(self, *args, **options):
        project = Project.objects.get(project_id=args[0])
        sample_map = dict(l.strip('\n').split('\t') for l in open(args[1]).readlines())

        for old_id, new_id in sample_map.iteritems():
            try:
                indiv = Individual.objects.get(project=project, indiv_id=old_id)
            except ObjectDoesNotExist:
                continue
            indiv.indiv_id = new_id
            indiv.save()