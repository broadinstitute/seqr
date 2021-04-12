# -*- coding: utf-8 -*-

from django.test import TestCase

import mock
import os
import subprocess

from seqr.models import Family, Individual, Sample
from seqr.views.utils.pedigree_image_utils import update_pedigree_images


MOCK_PAINT_PROCESS = mock.MagicMock()
MOCK_PAINT_PROCESS.returncode = 0
MOCK_PAINT_PROCESS.stdout = 'Generated pedigree'

class PedigreeImageTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.utils.pedigree_image_utils.BASE_DIR', '/')
    @mock.patch('seqr.views.utils.pedigree_image_utils.logger')
    @mock.patch('seqr.views.utils.pedigree_image_utils.random.randint')
    @mock.patch('seqr.views.utils.pedigree_image_utils.subprocess.run')
    @mock.patch('seqr.views.utils.pedigree_image_utils.tempfile')
    def test_update_pedigree_images(self, mock_tempfile, mock_run, mock_randint, mock_logger):
        mock_tempfile.gettempdir.return_value = '/tmp'
        mock_tempfile_file = mock_tempfile.NamedTemporaryFile.return_value.__enter__.return_value
        mock_tempfile_file.name = 'temp.fam'
        mock_randint.return_value = 123456

        def _mock_paint(command, **kwargs):
            with open(command[-1], 'wb') as f:
                f.write(b'\xff\xd8\xff')
            return MOCK_PAINT_PROCESS
        mock_run.side_effect = _mock_paint

        test_families = Family.objects.filter(guid='F000001_1')

        update_pedigree_images(test_families, None)
        pedigree_image = test_families.first().pedigree_image
        self.assertTrue(bool(pedigree_image))
        self.assertEqual(pedigree_image.name, 'pedigree_images/pedigree_image_123456.png')
        os.remove(pedigree_image.path)
        mock_run.assert_called_with(
            ['perl', '/seqr/management/commands/HaploPainter1.043.pl', '-b', '-outformat', 'png', '-pedfile', 'temp.fam', '-family', '1', '-outfile', '/tmp/pedigree_image_123456.png'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        mock_tempfile_file.write.assert_has_calls([
            mock.call('\t'.join(['1', 'NA19675_1', 'NA19678', 'NA19679', '1', '2'])),
            mock.call('\n'),
            mock.call('\t'.join(['1', 'NA19678', '0', '0', '1', '1'])),
            mock.call('\n'),
            mock.call('\t'.join(['1', 'NA19679', '0', '0', '2', '1'])),
            mock.call('\n'),
        ])
        mock_logger.info.assert_any_call('Generated pedigree')
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

        # Create placeholder when only has one parent
        Sample.objects.get(guid='S000130_na19678').delete()
        Individual.objects.get(individual_id='NA19678').delete()
        mock_tempfile_file.write.reset_mock()
        mock_run.reset_mock()
        mock_logger.reset_mock()
        MOCK_PAINT_PROCESS.returncode = 1
        MOCK_PAINT_PROCESS.stdout = 'Error!'

        update_pedigree_images(test_families, None)
        pedigree_image = test_families.first().pedigree_image
        self.assertTrue(bool(pedigree_image))
        self.assertEqual(pedigree_image.name, 'pedigree_images/pedigree_image_123456.png')
        os.remove(pedigree_image.path)
        mock_run.assert_called_with(
            ['perl', '/seqr/management/commands/HaploPainter1.043.pl', '-b', '-outformat', 'png', '-pedfile', 'temp.fam', '-family', '1', '-outfile', '/tmp/pedigree_image_123456.png'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        mock_tempfile_file.write.assert_has_calls([
            mock.call('\t'.join(['1', 'NA19675_1', 'placeholder_123456', 'NA19679', '1', '2'])),
            mock.call('\n'),
            mock.call('\t'.join(['1', 'NA19679', '0', '0', '2', '1'])),
            mock.call('\n'),
            mock.call('\t'.join(['1', 'placeholder_123456', '0', '0', '1', '9'])),
            mock.call('\n'),
        ])
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_called_with('Generated pedigree image for family 1 with exit status 1: Error!')

        # Do not generate for families with one individual
        mock_tempfile_file.write.reset_mock()
        mock_run.reset_mock()
        mock_logger.reset_mock()
        one_individual_families = Family.objects.filter(guid='F000003_3')
        update_pedigree_images(one_individual_families, None)
        pedigree_image = one_individual_families.first().pedigree_image
        self.assertFalse(bool(pedigree_image))
        mock_run.assert_not_called()
        mock_tempfile_file.write.assert_not_called()
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

        # Do not generate for families with no parental inheritance specified
        two_individual_families = Family.objects.filter(guid='F000012_12')
        update_pedigree_images(two_individual_families, None)
        pedigree_image = two_individual_families.first().pedigree_image
        self.assertFalse(bool(pedigree_image))
        mock_run.assert_not_called()
        mock_tempfile_file.write.assert_not_called()
        mock_logger.warning.assert_called_with('Unable to generate for pedigree image for family 12: no parents specified')
        mock_logger.error.assert_not_called()

        # Alert when generation fails
        mock_logger.reset_mock()
        mock_run.side_effect = lambda *args, **kwargs: MOCK_PAINT_PROCESS
        update_pedigree_images(test_families, None)
        pedigree_image = test_families.first().pedigree_image
        self.assertFalse(bool(pedigree_image))
        mock_run.assert_called_with(
            ['perl', '/seqr/management/commands/HaploPainter1.043.pl', '-b', '-outformat', 'png', '-pedfile', 'temp.fam', '-family', '1', '-outfile', '/tmp/pedigree_image_123456.png'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        records = [
            ['1', 'NA19675_1', 'placeholder_123456', 'NA19679', '1', '2'],
            ['1', 'NA19679', '0', '0', '2', '1'],
            ['1', 'placeholder_123456', '0', '0', '1', '9']
        ]
        mock_tempfile_file.write.assert_has_calls([
            mock.call('\t'.join(records[0])),
            mock.call('\n'),
            mock.call('\t'.join(records[1])),
            mock.call('\n'),
            mock.call('\t'.join(records[2])),
            mock.call('\n'),
        ])
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_called_with('Failed to generate pedigree image for family 1: Error!', extra={
            'detail': {'ped_file': records}})

