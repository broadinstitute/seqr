from django.core.management import call_command, CommandError
from django.test import TestCase
import mock

from seqr.models import IgvSample


class UpdateIgvPathsTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.management.commands.update_igv_location.logger.info')
    def test_command(self, mock_logger):
        with self.assertRaises(CommandError) as err:
            call_command('update_igv_location')
        self.assertEqual(str(err.exception), 'Error: the following arguments are required: old_prefix, new_prefix')

        call_command('update_igv_location', '/readviz/', '/seqr/static_media/igv/')
        mock_logger.assert_has_calls([
            mock.call('Updating 1 IGV samples'),
            mock.call('Done'),
        ])
        self.assertEqual(IgvSample.objects.get(id=145).file_path, '/seqr/static_media/igv/NA19675.cram')
        # Other IGV samples are unchanged
        self.assertEqual(IgvSample.objects.get(id=146).file_path, 'gs://readviz/NA20870.cram')

        with self.assertRaises(CommandError) as err:
            call_command('update_igv_location', '/readviz/', '/seqr/static_media/igv/')
        self.assertEqual(str(err.exception), 'No IGV samples found with file prefix "/readviz/"')
