# -*- coding: utf-8 -*-

from django.test import TestCase

import mock
import os

from seqr.models import Family, Individual, Sample
from seqr.views.utils.pedigree_image_utils import update_pedigree_images


class PedigreeImageTest(TestCase):
    fixtures = ['users', '1kg_project']

    @mock.patch('seqr.views.utils.pedigree_image_utils.BASE_DIR', '/')
    @mock.patch('seqr.views.utils.pedigree_image_utils.random.randint')
    @mock.patch('seqr.views.utils.pedigree_image_utils.os.system')
    @mock.patch('seqr.views.utils.pedigree_image_utils.tempfile')
    def test_update_pedigree_images(self, mock_tempfile, mock_os_system, mock_randint):
        mock_tempfile.gettempdir.return_value = '/tmp'
        mock_tempfile_file = mock_tempfile.NamedTemporaryFile.return_value.__enter__.return_value
        mock_tempfile_file.name = 'temp.fam'
        mock_randint.return_value = 123456

        def _mock_paint(command):
            with open(command.split('-outfile ')[-1], 'wb') as f:
                f.write(b'\xff\xd8\xff')
        mock_os_system.side_effect = _mock_paint

        test_families = Family.objects.filter(guid='F000001_1')

        update_pedigree_images(test_families, None)
        pedigree_image = test_families.first().pedigree_image
        self.assertTrue(bool(pedigree_image))
        self.assertEqual(pedigree_image.name, 'pedigree_images/pedigree_image_123456.png')
        os.remove(pedigree_image.path)
        mock_os_system.assert_called_with(
            'perl /seqr/management/commands/HaploPainter1.043.pl -b -outformat png -pedfile temp.fam -family 1 -outfile /tmp/pedigree_image_123456.png'
        )

        mock_tempfile_file.write.assert_has_calls([
            mock.call('\t'.join(['1', 'NA19675_1', 'NA19678', 'NA19679', '1', '2'])),
            mock.call('\n'),
            mock.call('\t'.join(['1', 'NA19678', '0', '0', '1', '1'])),
            mock.call('\n'),
            mock.call('\t'.join(['1', 'NA19679', '0', '0', '2', '1'])),
            mock.call('\n'),
        ])

        # Create placeholder when only has one parent
        Sample.objects.get(guid='S000130_na19678').delete()
        Individual.objects.get(individual_id='NA19678').delete()
        mock_tempfile_file.write.reset_mock()
        mock_os_system.reset_mock()

        update_pedigree_images(test_families, None)
        pedigree_image = test_families.first().pedigree_image
        self.assertTrue(bool(pedigree_image))
        self.assertEqual(pedigree_image.name, 'pedigree_images/pedigree_image_123456.png')
        os.remove(pedigree_image.path)
        mock_os_system.assert_called_with(
            'perl /seqr/management/commands/HaploPainter1.043.pl -b -outformat png -pedfile temp.fam -family 1 -outfile /tmp/pedigree_image_123456.png'
        )
        mock_tempfile_file.write.assert_has_calls([
            mock.call('\t'.join(['1', 'NA19675_1', 'placeholder_123456', 'NA19679', '1', '2'])),
            mock.call('\n'),
            mock.call('\t'.join(['1', 'NA19679', '0', '0', '2', '1'])),
            mock.call('\n'),
            mock.call('\t'.join(['1', 'placeholder_123456', '0', '0', '1', '9'])),
            mock.call('\n'),
        ])

        # Do not generate for families with one individual
        mock_tempfile_file.write.reset_mock()
        mock_os_system.reset_mock()
        one_individual_families = Family.objects.filter(guid='F000003_3')
        update_pedigree_images(one_individual_families, None)
        pedigree_image = one_individual_families.first().pedigree_image
        self.assertFalse(bool(pedigree_image))
        mock_os_system.assert_not_called()
        mock_tempfile_file.write.assert_not_called()
