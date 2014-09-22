from django.core.management.base import BaseCommand
from xbrowse_server import mall
from xbrowse_server.base.models import Project, Individual


class Command(BaseCommand):
    def handle(self, *args, **options):
        project = Project.objects.get(project_id=args[0])
        sample_map = dict(l.strip('\n').split('\t') for l in open(args[1]).readlines())

        datastore_db = mall.get_datastore()._db

        for old_id, new_id in sample_map.iteritems():
            # change actual IDs
            indiv = Individual.objects.get(project=project, indiv_id=old_id)
            indiv.indiv_id = new_id
            indiv.save()

            # datastore
            if indiv.family:
                mall.get_datastore().delete_family(project.project_id, indiv.family.family_id)
