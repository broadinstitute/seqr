from collections import defaultdict
from django.core.management.base import BaseCommand

from seqr.models import ProjectCategory, Project
from seqr.views.utils.file_utils import parse_file


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('file')

    def handle(self, *args, **options):
        file_path = options['file']

        with open(file_path) as f:
            file_input = parse_file(file_path, f)

        project_categories = defaultdict(list)
        for row in file_input[1:]:
            if row[1]:
                for category in row[1].split(','):
                    project_categories[category.strip()].append(row[0].strip())

        for category_name, projects in project_categories.items():
            project_category = ProjectCategory.objects.create(name=category_name)
            project_category.projects.set(Project.objects.filter(name__in=projects))
            print('{}: {} projects'.format(category_name, len(projects)))
