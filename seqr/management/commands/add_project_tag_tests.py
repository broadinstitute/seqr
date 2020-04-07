from io import StringIO
from django.core.management import call_command
from django.test import TestCase

TEST_ARGUMENTS = {
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
        call_command('add_project_tag', '--project={}'.format(TEST_ARGUMENTS["project"]),
            '--name={}'.format(TEST_ARGUMENTS["name"]), '--order={}'.format(TEST_ARGUMENTS["order"]),
            '--category={}'.format(TEST_ARGUMENTS["category"]),
            '--description={}'.format(TEST_ARGUMENTS["description"]),
            '--color={}'.format(TEST_ARGUMENTS["color"]), stdout = out)

        expectOutput = out.getvalue()
        self.assertIn('', expectOutput)
