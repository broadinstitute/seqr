import json
import mock
from datetime import datetime
from django.test import TestCase
from django.urls.base import reverse

from seqr.models import Project
from seqr.views.apis.project_api import create_project_handler, delete_project_handler, update_project_handler, \
    project_page_data
from seqr.views.utils.test_utils import _check_login, create_proxy_request_stub, PROJECT_FIELDS, \
    INTERNAL_FAMILY_FIELDS, INTERNAL_INDIVIDUAL_FIELDS, SAMPLE_FIELDS, LOCUS_LIST_FIELDS, IGV_SAMPLE_FIELDS


PROJECT_GUID = 'R0001_1kg'
EMPTY_PROJECT_GUID = 'R0002_empty'


class ProjectAPITest(TestCase):
    fixtures = ['users', '1kg_project', 'reference_data']
    multi_db = True

    @mock.patch('seqr.views.utils.phenotips_utils.proxy_request', create_proxy_request_stub(201))
    def test_create_update_and_delete_project(self):
        create_project_url = reverse(create_project_handler)
        _check_login(self, create_project_url)

        # check validation of bad requests
        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps({'bad_json': None}))
        self.assertEqual(response.status_code, 400)

        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps({'form': {'missing_name': True}}))
        self.assertEqual(response.status_code, 400)

        # send valid request to create project
        response = self.client.post(create_project_url, content_type='application/json', data=json.dumps(
            {'name': 'new_project', 'description': 'new project description', 'genomeVersion': '38'}
        ))
        self.assertEqual(response.status_code, 200)

        # check that project was created
        new_project = Project.objects.filter(name='new_project')
        self.assertEqual(len(new_project), 1)
        self.assertEqual(new_project[0].description, 'new project description')
        self.assertEqual(new_project[0].genome_version, '38')

        project_guid = new_project[0].guid
        self.assertSetEqual(set(response.json()['projectsByGuid'].keys()), {project_guid})

        # update the project
        update_project_url = reverse(update_project_handler, args=[project_guid])
        response = self.client.post(update_project_url, content_type='application/json', data=json.dumps(
            {'description': 'updated project description'}
        ))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['projectsByGuid'][project_guid]['description'], 'updated project description')
        self.assertEqual(Project.objects.get(guid=project_guid).description, 'updated project description')

        # genome version should not update
        response = self.client.post(update_project_url, content_type='application/json', data=json.dumps(
            {'genomeVersion': '37'}
        ))
        self.assertEqual(response.json()['projectsByGuid'][project_guid]['genomeVersion'], '38')
        self.assertEqual(Project.objects.get(guid=project_guid).genome_version, '38')

        # delete the project
        delete_project_url = reverse(delete_project_handler, args=[project_guid])
        response = self.client.post(delete_project_url, content_type='application/json')

        self.assertEqual(response.status_code, 200)

        # check that project was deleted
        new_project = Project.objects.filter(name='new_project')
        self.assertEqual(len(new_project), 0)

    def test_project_page_data(self):
        url = reverse(project_page_data, args=[PROJECT_GUID])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(
            set(response_json.keys()),
            {'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid', 'locusListsByGuid',
             'analysisGroupsByGuid', 'genesById', 'mmeSubmissionsByGuid', 'igvSamplesByGuid'}
        )
        self.assertSetEqual(
            set(response_json['projectsByGuid'][PROJECT_GUID]['variantTagTypes'][0].keys()),
            {'variantTagTypeGuid', 'name', 'category', 'description', 'color', 'order', 'numTags', 'numTagsPerFamily'}
        )
        project_fields = {
            'collaborators', 'locusListGuids', 'variantTagTypes', 'variantFunctionalTagTypes', 'detailsLoaded',
            'discoveryTags',
        }
        project_fields.update(PROJECT_FIELDS)
        self.assertSetEqual(set(response_json['projectsByGuid'][PROJECT_GUID].keys()), project_fields)
        self.assertEqual(
            response_json['projectsByGuid'][PROJECT_GUID]['lastAccessedDate'][:10],
            datetime.today().strftime('%Y-%m-%d')
        )
        discovery_tags = response_json['projectsByGuid'][PROJECT_GUID]['discoveryTags']
        self.assertEqual(len(discovery_tags), 1)
        self.assertEqual(discovery_tags[0]['variantGuid'], 'SV0000001_2103343353_r0390_100')
        self.assertListEqual(response_json['genesById'].keys(), ['ENSG00000135953'])
        self.assertSetEqual(set(response_json['familiesByGuid'].values()[0].keys()), INTERNAL_FAMILY_FIELDS)
        individual_fields = {'sampleGuids', 'igvSampleGuids', 'mmeSubmissionGuid'}
        individual_fields.update(INTERNAL_INDIVIDUAL_FIELDS)
        self.assertSetEqual(set(response_json['individualsByGuid'].values()[0].keys()), individual_fields)
        self.assertSetEqual(set(response_json['samplesByGuid'].values()[0].keys()), SAMPLE_FIELDS)
        self.assertSetEqual(set(response_json['igvSamplesByGuid'].values()[0].keys()), IGV_SAMPLE_FIELDS)
        self.assertSetEqual(set(response_json['locusListsByGuid'].values()[0].keys()), LOCUS_LIST_FIELDS)
        self.assertSetEqual(
            set(response_json['analysisGroupsByGuid'].values()[0].keys()),
            {'analysisGroupGuid', 'description', 'name', 'projectGuid', 'familyGuids'}
        )
        self.assertSetEqual(
            set(response_json['mmeSubmissionsByGuid'].values()[0].keys()),
            {'submissionGuid', 'individualGuid', 'createdDate', 'lastModifiedDate', 'deletedDate'}
        )
        self.assertSetEqual(
            set(response_json['individualsByGuid']['I000001_na19675']['features'][0].keys()),
            {'id', 'category', 'label'}
        )
        self.assertSetEqual(
            set(response_json['individualsByGuid']['I000001_na19675']['absentFeatures'][0].keys()),
            {'id', 'category', 'label'}
        )

    def test_empty_project_page_data(self):
        url = reverse(project_page_data, args=[EMPTY_PROJECT_GUID])
        _check_login(self, url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertSetEqual(
            set(response_json.keys()),
            {'projectsByGuid', 'familiesByGuid', 'individualsByGuid', 'samplesByGuid', 'locusListsByGuid',
             'analysisGroupsByGuid', 'genesById', 'mmeSubmissionsByGuid', 'igvSamplesByGuid'}
        )
        self.assertListEqual(response_json['projectsByGuid'].keys(), [EMPTY_PROJECT_GUID])
        self.assertDictEqual(response_json['familiesByGuid'], {})
        self.assertDictEqual(response_json['individualsByGuid'], {})
        self.assertDictEqual(response_json['samplesByGuid'], {})
        self.assertDictEqual(response_json['analysisGroupsByGuid'], {})
        self.assertDictEqual(response_json['genesById'], {})
        self.assertDictEqual(response_json['mmeSubmissionsByGuid'], {})
        self.assertDictEqual(response_json['locusListsByGuid'], {})
