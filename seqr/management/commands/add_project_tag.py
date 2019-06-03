from django.core.management.base import BaseCommand, CommandError
from django.db.models.query_utils import Q

from seqr.models import Project, VariantTagType
from seqr.model_utils import create_seqr_model


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--project', help='Project for tag.', required=True)
        parser.add_argument('--name', help='Tag name', required=True)
        parser.add_argument('--order', help='Order in project tag list', required=True)
        parser.add_argument('--category', help='Category (optional)')
        parser.add_argument('--description', help='Description (optional)')
        parser.add_argument('--color', help='Color (optional)')

    def handle(self, *args, **options):
        project_name = options['project']
        tag_options = {k: options[k] or '' for k in ['name', 'order', 'category', 'description', 'color']}

        project = Project.objects.get(Q(name=project_name) | Q(guid=project_name))
        if VariantTagType.objects.filter(name__iexact=options['name']).filter(Q(project=project) | Q(project__isnull=True)):
            raise CommandError('Tag "{}" already exists for project {}'.format(options['name'], project_name))

        create_seqr_model(VariantTagType, project=project, **tag_options)
