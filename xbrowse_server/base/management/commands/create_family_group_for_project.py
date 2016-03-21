from optparse import make_option

from django.core.management.base import BaseCommand

from xbrowse_server.base.models import Project
from xbrowse_server import sample_management


class Command(BaseCommand):


    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')
        parser.add_argument('--skip-probands', action="store_true")


    def handle(self, *args, **options):
        project = Project.objects.get(project_id=args[0])
        slug = args[1]
        families = project.get_families()
        families = [f for f in families if f.num_individuals_with_variant_data() == f.num_individuals()]
        if options.get('skip_probands'):
            families = [f for f in families if f.num_individuals_with_variant_data() > 1]
        sample_management.create_family_group(project, families, slug)
