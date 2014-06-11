from django.core.management.base import BaseCommand
from optparse import make_option
from xbrowse_server.base.models import Project, FamilyGroup
from xbrowse_server import sample_management
from xbrowse.parsers import vcf_stuff
import gzip

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--skip-probands', action="store_true"),
    )

    def handle(self, *args, **options):
        project = Project.objects.get(project_id=args[0])
        slug = args[1]
        families = project.get_families()
        families = [f for f in families if f.num_individuals_with_variant_data() == f.num_individuals()]
        if options.get('skip_probands'):
            families = [f for f in families if f.num_individuals_with_variant_data() > 1]
        sample_management.create_family_group(project, families, slug)
