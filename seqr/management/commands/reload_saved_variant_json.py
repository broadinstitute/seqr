import logging
from django.core.management.base import BaseCommand, CommandError
from django.db.models.query_utils import Q
from seqr.models import Project
from seqr.utils.search.elasticsearch.es_utils import update_project_saved_variant_json
from seqr.utils.search.utils import es_only
from seqr.views.utils.variant_utils import update_projects_saved_variant_json

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Transfer projects to the new seqr schema'

    def add_arguments(self, parser):
        parser.add_argument('projects', nargs="*", help='Project(s) to transfer. If not specified, defaults to all projects.')
        parser.add_argument('--family-guid', help='optional family to reload variants for')

    @es_only
    def handle(self, *args, **options):
        projects_to_process = options['projects']
        family_guid = options['family_guid']

        if projects_to_process:
            projects = Project.objects.filter(Q(name__in=projects_to_process) | Q(guid__in=projects_to_process))
            logging.info("Processing %s projects" % len(projects))
        else:
            projects = Project.objects.all()
            logging.info("Processing all %s projects" % len(projects))

        family_ids = [family_guid] if family_guid else None
        project_list = [(*project, family_ids) for project in projects.order_by('id').values_list('id', 'guid', 'name', 'genome_version')]
        update_projects_saved_variant_json(project_list, user_email='manage_command', update_function=update_project_saved_variant_json)
        logger.info("Done")
