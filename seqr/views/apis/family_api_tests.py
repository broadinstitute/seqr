# -*- coding: utf-8 -*-

import json
import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls.base import reverse

from openpyxl import load_workbook
from StringIO import StringIO

from seqr.models import Individual, Family
from seqr.views.apis.family_api import update_family_pedigree_image
from seqr.views.utils.test_utils import _check_login

FAMILY_GUID = 'F000001_1'


class ProjectAPITest(TestCase):
    fixtures = ['users', '1kg_project']

    #  TODO test other family api methods

    def test_update_family_pedigree_image(self):
        url = reverse(update_family_pedigree_image, args=[FAMILY_GUID])
        _check_login(self, url)

        f = SimpleUploadedFile("new_ped_image.png", b"file_content")

        # send invalid request
        response = self.client.post(url, {'f1': f, 'f2': f})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Received 2 files')

        # send valid add/update request
        response = self.client.post(url, {'f': f})
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), ['F000001_1'])
        self.assertRegex(response_json['F000001_1']['pedigreeImage'], '/media/pedigree_images/new_ped_image_.+\.png')

        # send valid delete request
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()

        self.assertListEqual(response_json.keys(), ['F000001_1'])
        self.assertIsNone(response_json['F000001_1']['pedigreeImage'])
