import mock

from io import BytesIO
from django.core.management import call_command
from django.test import TestCase
EXPECTED_EXCEPTION_MSG = 'Error at /readviz/NA19675.cram (Individual: NA19675_1): Error accessing "/readviz/NA19675.cram" \n---- DONE ----\nChecked 1 samples\n1 failed samples: NA19675_1\n'
EXPECTED_NORMAL_MSG = 'Error at /readviz/NA19675.cram (Individual: NA19675_1): Error accessing "/readviz/NA19675.cram" \n---- DONE ----\nChecked 1 samples\n1 failed samples: NA19675_1\n'


class AddProjectTagTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.utils.dataset_utils.validate_alignment_dataset_path')
    def test_normal_command(self, mock_validate_path):
        mock_validate_path.return_value = ""
        out = BytesIO()
        call_command('check_bam_cram_paths', u'1kg project n\u00e5me with uni\u00e7\u00f8de', stdout=out)

        self.assertEqual(EXPECTED_NORMAL_MSG, out.getvalue())

    @mock.patch('seqr.views.utils.dataset_utils.validate_alignment_dataset_path')
    def test_exception_command(self, mock_validate_path):
        mock_validate_path.side_effect = Exception('Error accessing "/readviz/NA19675.cram"')
        out = BytesIO()
        call_command('check_bam_cram_paths', u'1kg project n\u00e5me with uni\u00e7\u00f8de', stdout=out)

        self.assertEqual(EXPECTED_EXCEPTION_MSG, out.getvalue())
