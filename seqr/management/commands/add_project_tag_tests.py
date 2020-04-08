from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from seqr.models import Project, VariantTagType
from django.db.models.query_utils import Q

TAG_ARGUMENTS = {
    "project": "Test Project",
    "name": "Test tag - Novel gene and phenotype",
    "order": 22.0,
    "category": "CMG Discovery Tags",
    "description": "Gene not previously associated with a Mendelian condition",
    "color": "#03441E"
}


class AddProjectTagTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_normal_command(self):
        out = StringIO()
        call_command('add_project_tag', '--project={}'.format(TAG_ARGUMENTS["project"]),
            '--name={}'.format(TAG_ARGUMENTS["name"]), '--order={}'.format(TAG_ARGUMENTS["order"]),
            '--category={}'.format(TAG_ARGUMENTS["category"]),
            '--description={}'.format(TAG_ARGUMENTS["description"]),
            '--color={}'.format(TAG_ARGUMENTS["color"]), stdout = out)

        self.assertIn('', out.getvalue())

        project = Project.objects.get(Q(name = TAG_ARGUMENTS["project"]))
        variantTagType = VariantTagType.objects.get(name__iexact=TAG_ARGUMENTS["name"], project=project)
        tag_info = {
            "project": variantTagType.project.name,
            "name": variantTagType.name,
            "order": variantTagType.order,
            "category": variantTagType.category,
            "description": variantTagType.description,
            "color": variantTagType.color
        }
        self.assertDictEqual(tag_info, TAG_ARGUMENTS)

    def test_missing_required_args(self):
        out = StringIO()
        error = ''
        try:
            call_command('add_project_tag',
                stdout = out)
        except CommandError as err:
            error = err.message
        self.assertEqual(error, 'Error: argument --project is required')

        try:
            call_command('add_project_tag',
                '--project={}'.format(TAG_ARGUMENTS["project"]),
                stdout = out)
        except CommandError as err:
            error = err.message
        self.assertEqual(error, 'Error: argument --name is required')

        try:
            call_command('add_project_tag',
                '--project={}'.format(TAG_ARGUMENTS["project"]),
                '--name={}'.format(TAG_ARGUMENTS["name"]),
                stdout = out)
        except CommandError as err:
            error = err.message
        self.assertEqual(error, 'Error: argument --order is required')

    def test_bad_argument_value(self):
        out = StringIO()
        error = ''
        try:
            call_command('add_project_tag', '--project={}'.format(TAG_ARGUMENTS["project"]),
                '--name=Tier 1 - Novel gene and phenotype', '--order={}'.format(TAG_ARGUMENTS["order"]),
                '--category={}'.format(TAG_ARGUMENTS["category"]),
                '--description={}'.format(TAG_ARGUMENTS["description"]),
                '--color={}'.format(TAG_ARGUMENTS["color"]), stdout = out)
        except CommandError as err:
            error = err.message
        self.assertEqual(error, 'Tag "Tier 1 - Novel gene and phenotype" already exists for project Test Project')
