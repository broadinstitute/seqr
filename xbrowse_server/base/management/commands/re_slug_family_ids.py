from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from xbrowse_server import sample_management
from xbrowse_server.base.models import Project, Family
from xbrowse.utils import slugify


class Command(BaseCommand):
    """
    This is kind of a silly command - we switched from one slugify library to another a while ago,
    so some of the family IDs need to be switched from "family-slug-1" to "Family-Slug-1".
    """
    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*')

    def handle(self, *args, **options):
        project_id = args[0]
        project = Project.objects.get(project_id=project_id)
        raw_family_ids = [line.strip('\n') for line in open(args[1])]

        for raw_id in raw_family_ids:
            old_slugified_id = slugify(raw_id, separator='_').lower()
            if Family.objects.filter(project=project, family_id=old_slugified_id).exists():
                family = Family.objects.get(project=project, family_id=old_slugified_id)
                family.family_id = slugify(raw_id, separator='_')  # set family ID to new slug repr
                family.save()