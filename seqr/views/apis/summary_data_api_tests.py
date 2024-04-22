from datetime import datetime
from django.contrib.postgres.aggregates import ArrayAgg
from django.urls.base import reverse
import json
import mock
import responses

from seqr.views.apis.summary_data_api import mme_details, success_story, saved_variants_page, hpo_summary_data, \
    bulk_update_family_external_analysis, individual_metadata, family_metadata, variant_metadata
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase, AirtableTest, PARSED_VARIANTS
from seqr.models import FamilyAnalysedBy, SavedVariant, VariantTag
from settings import AIRTABLE_URL


PROJECT_GUID = 'R0001_1kg'

EXPECTED_SUCCESS_STORY = {'project_guid': 'R0001_1kg', 'family_guid': 'F000013_13', 'success_story_types': ['A'], 'family_id': 'no_individuals', 'success_story': 'Treatment is now available on compassionate use protocol (nucleoside replacement protocol)', 'row_id': 'F000013_13'}

EXPECTED_MME_DETAILS_METRICS = {
    u'numberOfPotentialMatchesSent': 1,
    u'numberOfUniqueGenes': 3,
    u'numberOfCases': 4,
    u'numberOfRequestsReceived': 3,
    u'numberOfSubmitters': 2,
    u'numberOfUniqueFeatures': 4,
    u'dateGenerated': '2020-04-27'
}

SAVED_VARIANT_RESPONSE_KEYS = {
    'projectsByGuid', 'locusListsByGuid', 'savedVariantsByGuid', 'variantFunctionalDataByGuid', 'genesById',
    'variantNotesByGuid', 'individualsByGuid', 'variantTagsByGuid', 'familiesByGuid', 'familyNotesByGuid',
    'mmeSubmissionsByGuid', 'transcriptsById',
}

EXPECTED_NO_AIRTABLE_SAMPLE_METADATA_ROW = {
    "projectGuid": "R0003_test",
    "num_saved_variants": 2,
    "solve_status": "Partially solved",
    "sample_id": "NA20889",
    "gene_known_for_phenotype-1": "Candidate",
    "gene_known_for_phenotype-2": "Candidate",
    "variant_inheritance-1": "unknown",
    "variant_inheritance-2": "unknown",
    'genetic_findings_id-1': 'NA20889_1_248367227',
    'genetic_findings_id-2': 'NA20889_1_249045487',
    "hgvsc-1": "c.3955G>A",
    "date_data_generation": "2017-02-05",
    "zygosity-1": "Heterozygous",
    "zygosity-2": "Heterozygous",
    "ref-1": "TC",
    "svType-2": "DEL",
    "sv_name-2": "DEL:chr1:249045487-249045898",
    "chrom-2": "1",
    "pos-2": 249045487,
    'end-2': 249045898,
    "maternal_id": "",
    "paternal_id": "",
    "maternal_guid": "",
    "paternal_guid": "",
    "hgvsp-1": "c.1586-17C>G",
    "internal_project_id": "Test Reprocessed Project",
    "pos-1": 248367227,
    "data_type": "WES",
    "familyGuid": "F000012_12",
    "family_history": "Yes",
    "hpo_present": "HP:0011675 (Arrhythmia)|HP:0001509 ()",
    "transcript-1": "ENST00000505820",
    'seqr_chosen_consequence-1': 'intron_variant',
    "ancestry": "Ashkenazi Jewish",
    "sex": "Female",
    "chrom-1": "1",
    "alt-1": "T",
    "gene-1": "OR4G11P",
    "gene_id-1": "ENSG00000240361",
    'variant_reference_assembly-1': 'GRCh37',
    'variant_reference_assembly-2': 'GRCh37',
    "pmid_id": None,
    "phenotype_description": None,
    "affected_status": "Affected",
    "analysisStatus": "Q",
    "filter_flags": "",
    "disorders": None,
    "family_id": "12",
    "displayName": "12",
    "MME": "Yes",
    "participant_id": "NA20889",
    "individual_guid": "I000017_na20889",
    "proband_relationship": "Self",
    "consanguinity": "Unknown",
    'analysis_groups': '',
    'alt-2': None,
    'ref-2': None,
    'hgvsc-2': '',
    'hgvsp-2': '',
    'transcript-2': None,
    'seqr_chosen_consequence-2': None,
    'gene-2': None,
    'gene_id-2': None,
    'svName-2': None,
    'svType-1': None,
    'sv_name-1': None,
    'svName-1': None,
    'end-1': None,
    'allele_balance_or_heteroplasmy_percentage-1': None,
    'allele_balance_or_heteroplasmy_percentage-2': None,
    'notes-1': None,
    'notes-2': None,
    'tags-1': ['Tier 1 - Novel gene and phenotype'],
    'tags-2': ['Tier 1 - Novel gene and phenotype'],
}
EXPECTED_SAMPLE_METADATA_ROW = {
    "dbgap_submission": "No",
    "dbgap_study_id": "",
    "dbgap_subject_id": "",
    "multiple_datasets": "No",
}
EXPECTED_SAMPLE_METADATA_ROW.update(EXPECTED_NO_AIRTABLE_SAMPLE_METADATA_ROW)
EXPECTED_NO_GENE_SAMPLE_METADATA_ROW = {
    'participant_id': 'NA21234',
    'sample_id': 'NA21234',
    'familyGuid': 'F000014_14',
    'family_id': '14',
    'displayName': '14',
    'projectGuid': 'R0004_non_analyst_project',
    'internal_project_id': 'Non-Analyst Project',
    'affected_status': 'Affected',
    'analysisStatus': 'Rncc',
    'ancestry': '',
    'consanguinity': 'Unknown',
    'data_type': 'WGS',
    'date_data_generation': '2018-02-05',
    'disorders': None,
    'filter_flags': '',
    'individual_guid': 'I000018_na21234',
    'variant_inheritance-1': 'unknown',
    'maternal_guid': '',
    'maternal_id': '',
    'MME': 'Yes',
    'family_history': 'Yes',
    'genetic_findings_id-1': 'NA21234_1_248367227',
    'num_saved_variants': 1,
    'paternal_guid': '',
    'paternal_id': '',
    'phenotype_description': None,
    'pmid_id': None,
    'proband_relationship': 'Self',
    'sex': 'Female',
    'solve_status': 'Unsolved',
    'alt-1': 'T',
    'chrom-1': '1',
    'gene_known_for_phenotype-1': 'Candidate',
    'tags-1': ['Tier 1 - Novel gene and phenotype'],
    'pos-1': 248367227,
    'end-1': None,
    'ref-1': 'TC',
    'zygosity-1': 'Heterozygous',
    'variant_reference_assembly-1': 'GRCh38',
    'allele_balance_or_heteroplasmy_percentage-1': None,
    'gene-1': None,
    'gene_id-1': None,
    'hgvsc-1': '',
    'hgvsp-1': '',
    'notes-1': None,
    'seqr_chosen_consequence-1': None,
    'svName-1': None,
    'svType-1': None,
    'sv_name-1': None,
    'transcript-1': None,
    'analysis_groups': '',
}

AIRTABLE_SAMPLE_RECORDS = {
  "records": [
    {
      "id": "rec2B6OGmQpAkQW3s",
      "fields": {
        "SeqrCollaboratorSampleID": "VCGS_FAM203_621_D1",
        "CollaboratorSampleID": "NA19675",
        "Collaborator": ["recW24C2CJW5lT64K"],
        "dbgap_study_id": "dbgap_stady_id_1",
        "dbgap_subject_id": "dbgap_subject_id_1",
        "dbgap_sample_id": "SM-A4GQ4",
        "SequencingProduct": [
          "Mendelian Rare Disease Exome"
        ],
        "dbgap_submission": [
          "WES",
          "Array"
        ]
      },
      "createdTime": "2019-09-09T19:21:12.000Z"
    },
    {
      "id": "rec2Nkg10N1KssPc3",
      "fields": {
        "SeqrCollaboratorSampleID": "HG00731",
        "CollaboratorSampleID": "NA20885",
        "Collaborator": ["reca4hcBnbA2cnZf9"],
        "dbgap_study_id": "dbgap_stady_id_2",
        "dbgap_subject_id": "dbgap_subject_id_2",
        "dbgap_sample_id": "SM-JDBTT",
        "SequencingProduct": [
          "Standard Germline Exome v6 Plus GSA Array"
        ],
        "dbgap_submission": [
          "WES",
          "Array"
        ]
      },
      "createdTime": "2019-07-16T18:23:21.000Z"
    }
]}
PAGINATED_AIRTABLE_SAMPLE_RECORDS = {
    'offset': 'abc123',
    'records': [{
      'id': 'rec2B6OGmQpfuRW5z',
      'fields': {
        'CollaboratorSampleID': 'NA19675',
        'Collaborator': ['recW24C2CJW5lT64K'],
        'dbgap_study_id': 'dbgap_study_id_2',
        'dbgap_subject_id': 'dbgap_subject_id_1',
        'dbgap_sample_id': 'SM-A4GQ4',
        'SequencingProduct': [
          'Mendelian Rare Disease Exome'
        ],
        'dbgap_submission': [
          'WES',
          'Array'
        ]
      },
      'createdTime': '2019-09-09T19:21:12.000Z'
    }
]}

AIRTABLE_COLLABORATOR_RECORDS = {
    "records": [
        {
            "id": "recW24C2CJW5lT64K",
            "fields": {
                "CollaboratorID": "Hildebrandt",
            }
        },
        {
            "id": "reca4hcBnbA2cnZf9",
            "fields": {
                "CollaboratorID": "Seidman",
            }
        }
    ]
}


BASE_VARIANT_METADATA_ROW = {
    'MME': False,
    'additional_family_members_with_variant': '',
    'allele_balance_or_heteroplasmy_percentage': None,
    'analysisStatus': 'Q',
    'analysis_groups': '',
    'clinvar': None,
    'condition_id': None,
    'consanguinity': 'Unknown',
    'end': None,
    'hgvsc': '',
    'hgvsp': '',
    'method_of_discovery': 'SR-ES',
    'notes': None,
    'phenotype_contribution': 'Full',
    'phenotype_description': None,
    'pmid_id': None,
    'seqr_chosen_consequence': None,
    'solve_status': 'Unsolved',
    'svName': None,
    'svType': None,
    'sv_name': None,
    'transcript': None,
}


# @mock.patch('seqr.views.utils.permissions_utils.safe_redis_get_json', lambda *args: None)
# class SummaryDataAPITest(AirtableTest):

#     @mock.patch('matchmaker.matchmaker_utils.datetime')
#     def test_mme_details(self, mock_datetime):
#         url = reverse(mme_details)
#         self.check_require_login(url)
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, 200)
#         self.assertDictEqual(response.json(), {'genesById': {}, 'savedVariantsByGuid': {}, 'submissions': []})

#         # Test behavior for non-analysts
#         self.login_manager()
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, 200)
#         response_json = response.json()
#         response_keys = {'genesById', 'submissions', 'savedVariantsByGuid'}
#         self.assertSetEqual(set(response_json.keys()), response_keys)
#         self.assertSetEqual(set(response_json['genesById'].keys()),
#                             {'ENSG00000240361', 'ENSG00000223972', 'ENSG00000135953'})
#         self.assertEqual(len(response_json['submissions']), self.NUM_MANAGER_SUBMISSIONS)

#         # Test analyst behavior
#         self.login_analyst_user()
#         mock_datetime.now.return_value = datetime(2020, 4, 27, 20, 16, 1)
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, 200)
#         response_json = response.json()
#         response_keys.add('metrics')
#         self.assertSetEqual(set(response_json.keys()), response_keys)
#         self.assertDictEqual(response_json['metrics'], EXPECTED_MME_DETAILS_METRICS)
#         self.assertEqual(len(response_json['genesById']), 3)
#         self.assertSetEqual(set(response_json['genesById'].keys()), {'ENSG00000240361', 'ENSG00000223972', 'ENSG00000135953'})
#         self.assertEqual(len(response_json['submissions']), 3)

#     def test_success_story(self):
#         url = reverse(success_story, args=['all'])
#         self.check_analyst_login(url)

#         response = self.client.get(url)
#         self.assertEqual(response.status_code, 200)
#         response_json = response.json()
#         self.assertListEqual(list(response_json.keys()), ['rows'])

#         self.assertEqual(len(response_json['rows']), 2)
#         self.assertDictEqual(response_json['rows'][1], EXPECTED_SUCCESS_STORY)

#         url = reverse(success_story, args=['A,T'])

#         response = self.client.get(url)
#         self.assertEqual(response.status_code, 200)
#         response_json = response.json()
#         self.assertListEqual(list(response_json.keys()), ['rows'])

#         self.assertEqual(len(response_json['rows']), 1)
#         self.assertDictEqual(response_json['rows'][0], EXPECTED_SUCCESS_STORY)

#         self.check_no_analyst_no_access(url)

#     @mock.patch('seqr.views.apis.summary_data_api.MAX_SAVED_VARIANTS', 1)
#     def test_saved_variants_page(self):
#         url = reverse(saved_variants_page, args=['Tier 1 - Novel gene and phenotype'])
#         self.check_require_login(url)

#         response = self.client.get('{}?gene=ENSG00000135953'.format(url))
#         self.assertEqual(response.status_code, 200)
#         self.assertDictEqual(response.json(), {k: {} for k in SAVED_VARIANT_RESPONSE_KEYS})

#         self.login_manager()
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, 400)
#         self.assertEqual(response.json()['error'], 'Select a gene to filter variants')

#         gene_url = '{}?gene=ENSG00000135953'.format(url)
#         response = self.client.get(gene_url)
#         self.assertEqual(response.status_code, 200)
#         response_json = response.json()
#         self.assertSetEqual(set(response_json.keys()), SAVED_VARIANT_RESPONSE_KEYS)
#         expected_variant_guids = {
#             'SV0000001_2103343353_r0390_100', 'SV0000007_prefix_19107_DEL_r00', 'SV0000006_1248367227_r0003_tes',
#         }
#         self.assertSetEqual(set(response_json['savedVariantsByGuid'].keys()), expected_variant_guids)
#         self.assertSetEqual(
#             set(response_json['projectsByGuid'][PROJECT_GUID].keys()),
#             {'projectGuid', 'name', 'variantTagTypes', 'variantFunctionalTagTypes'},
#         )

#         # Test analyst behavior
#         self.login_analyst_user()
#         response = self.client.get(gene_url)
#         self.assertEqual(response.status_code, 200)
#         response_json = response.json()
#         self.assertSetEqual(set(response_json.keys()), SAVED_VARIANT_RESPONSE_KEYS)
#         self.assertSetEqual(set(response_json['savedVariantsByGuid'].keys()), expected_variant_guids)

#         all_tag_url = reverse(saved_variants_page, args=['ALL'])
#         response = self.client.get('{}?gene=ENSG00000135953'.format(all_tag_url))
#         self.assertEqual(response.status_code, 200)
#         report_variant_guids = {
#             'SV0027168_191912632_r0384_rare', 'SV0027167_191912633_r0384_rare', 'SV0027166_191912634_r0384_rare',
#         }
#         expected_variant_guids.update(report_variant_guids)
#         expected_variant_guids.add('SV0000002_1248367227_r0390_100')
#         self.assertSetEqual(set(response.json()['savedVariantsByGuid'].keys()), expected_variant_guids)

#         multi_tag_url = reverse(saved_variants_page, args=['Review;Tier 1 - Novel gene and phenotype'])
#         response = self.client.get('{}?gene=ENSG00000135953'.format(multi_tag_url))
#         self.assertEqual(response.status_code, 200)
#         self.assertSetEqual(set(response.json()['savedVariantsByGuid'].keys()), {'SV0000001_2103343353_r0390_100'})

#         multi_tag_url = reverse(saved_variants_page, args=['Review;Tier 1 - Novel gene and phenotype'])
#         response = self.client.get('{}?gene=ENSG00000135953'.format(multi_tag_url))
#         self.assertEqual(response.status_code, 200)
#         self.assertSetEqual(set(response.json()['savedVariantsByGuid'].keys()), {'SV0000001_2103343353_r0390_100'})

#         discovery_tag_url = reverse(saved_variants_page, args=['CMG Discovery Tags'])
#         response = self.client.get('{}?gene=ENSG00000135953'.format(discovery_tag_url))
#         self.assertEqual(response.status_code, 200)
#         self.assertSetEqual(set(response.json()['savedVariantsByGuid'].keys()), {
#             'SV0000001_2103343353_r0390_100', 'SV0000002_1248367227_r0390_100', 'SV0000007_prefix_19107_DEL_r00',
#             'SV0000006_1248367227_r0003_tes', *report_variant_guids,
#         })

#         multi_discovery_tag_url = reverse(saved_variants_page, args=['CMG Discovery Tags;Review'])
#         response = self.client.get('{}?gene=ENSG00000135953'.format(multi_discovery_tag_url))
#         self.assertEqual(response.status_code, 200)
#         self.assertSetEqual(set(response.json()['savedVariantsByGuid'].keys()), {'SV0000001_2103343353_r0390_100'})

#     def test_hpo_summary_data(self):
#         url = reverse(hpo_summary_data, args=['HP:0002011'])
#         self.check_require_login(url)

#         response = self.client.get(url)
#         self.assertEqual(response.status_code, 200)
#         self.assertDictEqual(response.json(), {'data': []})

#         self.login_manager()
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, 200)
#         response_json = response.json()
#         self.assertSetEqual(set(response_json.keys()), {'data'})
#         self.assertListEqual(response_json['data'], [
#             {
#                 'individualGuid': 'I000001_na19675',
#                 'displayName': 'NA19675_1',
#                 'features': [
#                     {'id': 'HP:0001631', 'label': 'Defect in the atrial septum', 'category': 'HP:0025354'},
#                     {'id': 'HP:0002011', 'label': 'Morphological abnormality of the central nervous system',
#                      'category': 'HP:0000707', 'qualifiers': [
#                         {'label': 'Infantile onset', 'type': 'age_of_onset'},
#                         {'label': 'Mild', 'type': 'severity'},
#                         {'label': 'Nonprogressive', 'type': 'pace_of_progression'}
#                     ]},
#                     {'id': 'HP:0001636', 'label': 'Tetralogy of Fallot', 'category': 'HP:0033127'},
#                 ],
#                 'familyId': '1',
#                     'familyData': {
#                     'projectGuid': PROJECT_GUID,
#                     'genomeVersion': '37',
#                     'familyGuid': 'F000001_1',
#                     'analysisStatus': 'Q',
#                     'displayName': '1',
#                 }
#             },
#             {
#                 'individualGuid': 'I000004_hg00731',
#                 'displayName': 'HG00731_a',
#                 'features': [
#                     {'id': 'HP:0002011', 'label': 'Morphological abnormality of the central nervous system', 'category': 'HP:0000707'},
#                     {'id': 'HP:0011675', 'label': 'Arrhythmia', 'category': 'HP:0001626'},
#                 ],
#                 'familyId': '2',
#                 'familyData': {
#                     'projectGuid': PROJECT_GUID,
#                     'genomeVersion': '37',
#                     'familyGuid': 'F000002_2',
#                     'analysisStatus': 'Q',
#                     'displayName': '2_1',
#                 }
#             },
#         ])

#     @mock.patch('seqr.views.apis.summary_data_api.datetime')
#     @mock.patch('seqr.views.apis.summary_data_api.get_variants_for_variant_ids')
#     @mock.patch('seqr.views.apis.summary_data_api.load_uploaded_file')
#     def test_bulk_update_family_external_analysis(self, mock_load_uploaded_file, mock_get_variants_for_variant_ids, mock_datetime):
#         mock_created_time = datetime(2023, 12, 5, 20, 16, 1)
#         mock_datetime.now.return_value = mock_created_time

#         url = reverse(bulk_update_family_external_analysis)
#         self.check_analyst_login(url)

#         mock_load_uploaded_file.return_value = [['foo', 'bar']]
#         body = {'dataType': 'RNA', 'familiesFile': {'uploadedFileId': 'abc123'}}
#         response = self.client.post(url, content_type='application/json', data=json.dumps(body))
#         self.assertEqual(response.status_code, 400)
#         self.assertEqual(response.json()['error'], 'Project and Family columns are required')

#         mock_load_uploaded_file.return_value = [
#             ['Project', 'Family ID'],
#             ['1kg project n\u00e5me with uni\u00e7\u00f8de', '1'],
#             ['Test Reprocessed Project', '12'],
#             ['Test Reprocessed Project', 'not_a_family'],
#             ['not_a_project', '2'],
#             ['Non-Analyst Project', '14'],
#         ]
#         response = self.client.post(url, content_type='application/json', data=json.dumps(body))
#         self.assertDictEqual(response.json(), {
#             'warnings': [
#                 'No match found for the following families: 14 (Non-Analyst Project), not_a_family (Test Reprocessed Project), 2 (not_a_project)'
#             ],
#             'info': ['Updated "analysed by" for 2 families'],
#         })

#         models = FamilyAnalysedBy.objects.filter(last_modified_date__gte=mock_created_time)
#         self.assertEqual(len(models), 2)
#         self.assertSetEqual({fab.data_type for fab in models}, {'RNA'})
#         self.assertSetEqual({fab.created_by for fab in models}, {self.analyst_user})
#         self.assertSetEqual({fab.family.family_id for fab in models}, {'1', '12'})

#         # Test AIP
#         aip_upload = {
#             'metadata': {
#                 'categories': {
#                     '1': 'ClinVar Pathogenic',
#                     '2': 'New Gene-Disease Association',
#                     '3': 'High Impact Variant',
#                     '4': 'De-Novo',
#                     'support': 'High in Silico Scores'
#                 }
#             },
#             'results': {
#                 'HG00731': {
#                     '1-248367227-TC-T': {'categories': ['3', '4'], 'support_vars': ['2-103343353-GAGA-G']},
#                     '12-48367227-TC-T': {'categories': ['1'], 'support_vars': ['1-248367227-TC-T']},
#                 },
#                 'SAM_123': {
#                     '1-248367227-TC-T': {'categories': ['4', 'support'], 'support_vars': []},
#                 },
#             }
#         }
#         mock_load_uploaded_file.return_value = aip_upload
#         mock_get_variants_for_variant_ids.return_value = PARSED_VARIANTS
#         body['dataType'] = 'AIP'
#         response = self.client.post(url, content_type='application/json', data=json.dumps(body))
#         self.assertEqual(response.status_code, 400)
#         self.assertEqual(response.json()['errors'], ['Unable to find the following individuals: SAM_123'])

#         aip_upload['results']['NA20889'] = aip_upload['results'].pop('SAM_123')
#         response = self.client.post(url, content_type='application/json', data=json.dumps(body))
#         self.assertEqual(response.status_code, 400)
#         self.assertEqual(response.json()['errors'], [
#             "Unable to find the following family's AIP variants in the search backend: 2 (12-48367227-TC-T)",
#         ])

#         aip_upload['results']['HG00731']['2-103343353-GAGA-G'] = aip_upload['results']['HG00731'].pop('12-48367227-TC-T')
#         response = self.client.post(url, content_type='application/json', data=json.dumps(body))
#         self.assertEqual(response.status_code, 200)
#         self.assertDictEqual(response.json(), {'info': ['Loaded 2 new and 1 updated AIP tags for 2 families']})

#         new_saved_variant = SavedVariant.objects.get(variant_id='2-103343353-GAGA-G')
#         self.assertDictEqual(new_saved_variant.saved_variant_json, PARSED_VARIANTS[1])

#         aip_tags = VariantTag.objects.filter(variant_tag_type__name='AIP').order_by('id').values(
#             'metadata', saved_variant_ids=ArrayAgg('saved_variants__id'))
#         self.assertEqual(len(aip_tags), 4)

#         existing_tag = aip_tags[0]
#         self.assertListEqual(existing_tag['saved_variant_ids'], [2])
#         self.assertDictEqual(
#             json.loads(existing_tag['metadata']), {
#                 '3': {'name': 'High Impact Variant', 'date': '2023-12-05'},
#                 '4': {'name': 'de Novo', 'date': '2023-11-15'},
#                 'removed': {
#                     'support': {'date': '2023-11-15', 'name': 'High in Silico Scores'},
#                 },
#             })

#         new_saved_variant_tag = aip_tags[2]
#         self.assertListEqual(new_saved_variant_tag['saved_variant_ids'], [new_saved_variant.id])
#         self.assertDictEqual(
#             json.loads(new_saved_variant_tag['metadata']),
#             {'1': {'name': 'ClinVar Pathogenic', 'date': '2023-12-05'}},
#         )

#         comp_het_tag = aip_tags[1]
#         self.assertSetEqual(set(comp_het_tag['saved_variant_ids']), {2, new_saved_variant.id})
#         self.assertIsNone(comp_het_tag['metadata'])

#         existing_variant_new_tag = aip_tags[3]
#         self.assertListEqual(existing_variant_new_tag['saved_variant_ids'], [6])
#         self.assertDictEqual(
#             json.loads(existing_variant_new_tag['metadata']),
#             {'4': {'name': 'De-Novo', 'date': '2023-12-05'}, 'support': {'name': 'High in Silico Scores', 'date': '2023-12-05'}},
#         )

#         self.check_no_analyst_no_access(url)

#     def _has_expected_metadata_response(self, response, expected_individuals, has_airtable=False, has_duplicate=False):
#         self.assertEqual(response.status_code, 200)
#         response_json = response.json()
#         self.assertListEqual(list(response_json.keys()), ['rows'])
#         self.assertSetEqual({r['participant_id'] for r in response_json['rows']}, expected_individuals)
#         self.assertEqual(len(response_json['rows']), len(expected_individuals) + (2 if has_duplicate else 0))
#         test_row = next(r for r in response_json['rows'] if r['participant_id'] == 'NA20889')
#         self.assertDictEqual(
#             EXPECTED_SAMPLE_METADATA_ROW if has_airtable else EXPECTED_NO_AIRTABLE_SAMPLE_METADATA_ROW, test_row
#         )
#         if has_duplicate:
#             self.assertEqual(len([r['participant_id'] for r in response_json['rows'] if r['participant_id'] == 'NA20888']), 2)

#     @mock.patch('seqr.views.utils.airtable_utils.MAX_OR_FILTERS', 2)
#     @mock.patch('seqr.views.utils.airtable_utils.AIRTABLE_API_KEY', 'mock_key')
#     @mock.patch('seqr.views.utils.airtable_utils.is_google_authenticated')
#     @responses.activate
#     def test_sample_metadata_export(self, mock_google_authenticated):
#         mock_google_authenticated.return_value = False
#         url = reverse(individual_metadata, args=['R0003_test'])
#         self.check_require_login(url)

#         response = self.client.get(url)
#         self.assertEqual(response.status_code, 403)
#         self.assertEqual(response.json()['error'], 'Permission Denied')

#         # Test collaborator access
#         self.login_collaborator()
#         response = self.client.get(url)
#         expected_individuals = {'NA20885', 'NA20888', 'NA20889', 'NA20870'}
#         self._has_expected_metadata_response(response, expected_individuals)

#         # Test airtable not returned for non-analysts
#         include_airtable_url = f'{url}?includeAirtable=true'
#         response = self.client.get(include_airtable_url)
#         self._has_expected_metadata_response(response, expected_individuals)

#         # Test all projects
#         all_projects_url = reverse(individual_metadata, args=['all'])
#         multi_project_individuals = {
#             'NA19679', 'NA20870', 'HG00732', 'NA20876', 'NA20874', 'NA20875', 'NA19678', 'NA19675_1', 'HG00731',
#             'NA20872', 'NA20881', 'HG00733', 'NA20878',
#         }
#         multi_project_individuals.update(expected_individuals)
#         response = self.client.get(all_projects_url)
#         self._has_expected_metadata_response(response, multi_project_individuals, has_duplicate=True)

#         # Test gregor projects no access
#         gregor_projects_url = reverse(individual_metadata, args=['gregor'])
#         response = self.client.get(gregor_projects_url)
#         self.assertEqual(response.status_code, 403)
#         self.assertEqual(response.json()['error'], 'Permission Denied')

#         # Test no gene for discovery variant
#         self.login_manager()
#         no_analyst_project_url = reverse(individual_metadata, args=['R0004_non_analyst_project'])
#         response = self.client.get(no_analyst_project_url)
#         self.assertEqual(response.status_code, 200)
#         rows = response.json()['rows']
#         self.assertEqual(len(rows), 2)
#         test_row = next(r for r in rows if r['participant_id'] == 'NA21234')
#         self.assertDictEqual(test_row, EXPECTED_NO_GENE_SAMPLE_METADATA_ROW)

#         # Test analyst access
#         self.login_analyst_user()
#         response = self.client.get(no_analyst_project_url)
#         self.assertEqual(response.status_code, 403)
#         self.assertEqual(response.json()['error'], 'Permission Denied')

#         response = self.client.get(url)
#         self._has_expected_metadata_response(response, expected_individuals)

#         # Test empty project
#         empty_project_url = reverse(individual_metadata, args=['R0002_empty'])
#         response = self.client.get(empty_project_url)
#         self.assertEqual(response.status_code, 200)
#         self.assertDictEqual(response.json(), {'rows': []})

#         # Test all projects
#         response = self.client.get(all_projects_url)
#         all_project_individuals = {*multi_project_individuals, *self.ADDITIONAL_SAMPLES}
#         self._has_expected_metadata_response(response, all_project_individuals, has_duplicate=True)

#         response = self.client.get(f'{all_projects_url}?includeAirtable=true')
#         self._has_expected_metadata_response(response, all_project_individuals, has_duplicate=True)

#         # Test invalid airtable responses
#         response = self.client.get(include_airtable_url)
#         self.assertEqual(response.status_code, 403)
#         self.assertEqual(response.json()['error'], 'Permission Denied')
#         mock_google_authenticated.return_value = True

#         responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL), status=402)
#         response = self.client.get(include_airtable_url)
#         self.assertEqual(response.status_code, 402)

#         self.reset_logs()
#         responses.reset()
#         responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL), status=200)
#         response = self.client.get(include_airtable_url)
#         self.assertEqual(response.status_code, 500)
#         error_message = 'Unable to retrieve airtable data: Expecting value: line 1 column 1 (char 0)'
#         self.assertIn(response.json()['error'], ['Unable to retrieve airtable data: No JSON object could be decoded',
#                                                  error_message])
#         self.assertFalse('traceback' in response.json())
#         self.assert_json_logs(self.analyst_user, [
#             ('Fetching Samples records 0-2 from airtable', None),
#             (error_message, {
#                 'httpRequest': mock.ANY,
#                 'traceback': mock.ANY,
#                 'severity': 'ERROR',
#                 '@type': 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent',
#                 'validate': lambda log_value: self.assertTrue(log_value['traceback'].startswith('Traceback'))
#             })
#         ])


#         responses.reset()
#         responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL),
#                       json=PAGINATED_AIRTABLE_SAMPLE_RECORDS, status=200)
#         responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL),
#                       json=AIRTABLE_SAMPLE_RECORDS, status=200)
#         responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Collaborator'.format(AIRTABLE_URL),
#                       json=AIRTABLE_COLLABORATOR_RECORDS, status=200)
#         response = self.client.get(include_airtable_url)
#         self.assertEqual(response.status_code, 500)
#         self.assertEqual(
#             response.json()['error'],
#             'Found multiple airtable records for sample NA19675 with mismatched values in field dbgap_study_id')
#         self.assertEqual(len(responses.calls), 4)
#         first_formula = "OR({CollaboratorSampleID}='NA20885',{CollaboratorSampleID}='NA20888')"
#         expected_fields = [
#             'CollaboratorSampleID', 'Collaborator', 'dbgap_study_id', 'dbgap_subject_id',
#             'dbgap_sample_id', 'SequencingProduct', 'dbgap_submission',
#         ]
#         self.assert_expected_airtable_call(0, first_formula, expected_fields)
#         self.assert_expected_airtable_call(1, first_formula, expected_fields, additional_params={'offset': 'abc123'})
#         self.assert_expected_airtable_call(2, "OR({CollaboratorSampleID}='NA20889')", expected_fields)
#         second_formula = "OR({SeqrCollaboratorSampleID}='NA20888',{SeqrCollaboratorSampleID}='NA20889')"
#         expected_fields[0] = 'SeqrCollaboratorSampleID'
#         self.assert_expected_airtable_call(3, second_formula, expected_fields)

#         # Test airtable success
#         response = self.client.get(include_airtable_url)
#         self._has_expected_metadata_response(response, expected_individuals, has_airtable=True)
#         self.assertEqual(len(responses.calls), 8)
#         self.assert_expected_airtable_call(
#             -1, "OR(RECORD_ID()='reca4hcBnbA2cnZf9')", ['CollaboratorID'])
#         self.assertSetEqual({call.request.headers['Authorization'] for call in responses.calls}, {'Bearer mock_key'})

#         # Test gregor projects
#         response = self.client.get(gregor_projects_url)
#         self._has_expected_metadata_response(response, multi_project_individuals, has_duplicate=True)

#         response = self.client.get(f'{gregor_projects_url}?includeAirtable=true')
#         self._has_expected_metadata_response(response, multi_project_individuals, has_airtable=True, has_duplicate=True)

#     def test_family_metadata(self):
#         url = reverse(family_metadata, args=['R0003_test'])
#         self.check_collaborator_login(url)

#         response = self.client.get(url)
#         self.assertEqual(response.status_code, 200)
#         response_json = response.json()
#         self.assertListEqual(list(response_json.keys()), ['rows'])
#         self.assertListEqual(sorted([r['familyGuid'] for r in response_json['rows']]), ['F000011_11', 'F000012_12'])
#         test_row = next(r for r in response_json['rows'] if r['familyGuid'] == 'F000012_12')
#         self.assertDictEqual(test_row, {
#             'projectGuid': 'R0003_test',
#             'internal_project_id': 'Test Reprocessed Project',
#             'familyGuid': 'F000012_12',
#             'family_id': '12',
#             'displayName': '12',
#             'solve_status': 'Unsolved',
#             'actual_inheritance': 'unknown',
#             'date_data_generation': '2017-02-05',
#             'data_type': 'WES',
#             'proband_id': 'NA20889',
#             'maternal_id': '',
#             'paternal_id': '',
#             'other_individual_ids': 'NA20870; NA20888',
#             'individual_count': 3,
#             'family_structure': 'other',
#             'family_history': 'Yes',
#             'genes': 'DEL:chr1:249045487-249045898; OR4G11P',
#             'pmid_id': None,
#             'phenotype_description': None,
#             'analysisStatus': 'Q',
#             'analysis_groups': '',
#             'consanguinity': 'Unknown',
#         })

#         # Test all projects
#         all_projects_url = reverse(family_metadata, args=['all'])
#         response = self.client.get(all_projects_url)
#         self.assertEqual(response.status_code, 200)
#         response_json = response.json()
#         self.assertListEqual(list(response_json.keys()), ['rows'])
#         all_project_families = [
#             'F000001_1', 'F000002_2', 'F000003_3', 'F000004_4', 'F000005_5', 'F000006_6', 'F000007_7', 'F000008_8',
#             'F000009_9', 'F000010_10', 'F000011_11', 'F000012_12', 'F000013_13']
#         self.assertListEqual(sorted([r['familyGuid'] for r in response_json['rows']]), all_project_families)
#         test_row = next(r for r in response_json['rows'] if r['familyGuid'] == 'F000003_3')
#         self.assertDictEqual(test_row, {
#             'projectGuid': 'R0001_1kg',
#             'internal_project_id': '1kg project nåme with uniçøde',
#             'familyGuid': 'F000003_3',
#             'family_id': '3',
#             'displayName': '3',
#             'solve_status': 'Unsolved',
#             'actual_inheritance': '',
#             'date_data_generation': '2017-02-05',
#             'data_type': 'WES',
#             'other_individual_ids': 'NA20870',
#             'individual_count': 1,
#             'family_structure': 'singleton',
#             'genes': '',
#             'pmid_id': None,
#             'phenotype_description': None,
#             'analysisStatus': 'Q',
#             'analysis_groups': 'Accepted; Test Group 1',
#             'consanguinity': 'Unknown',
#             'condition_id': 'OMIM:615123',
#             'known_condition_name': '',
#             'condition_inheritance': 'Unknown',
#         })

#         # Test analyst access
#         self.login_analyst_user()
#         response = self.client.get(all_projects_url)
#         self.assertEqual(response.status_code, 200)
#         self.assertListEqual(
#             sorted([r['familyGuid'] for r in response.json()['rows']]), all_project_families + self.ADDITIONAL_FAMILIES)

#         # Test empty project
#         empty_project_url = reverse(family_metadata, args=['R0002_empty'])
#         response = self.client.get(empty_project_url)
#         self.assertEqual(response.status_code, 200)
#         self.assertDictEqual(response.json(), {'rows': []})

#     def test_variant_metadata(self):
#         url = reverse(variant_metadata, args=[PROJECT_GUID])
#         self.check_collaborator_login(url)

#         response = self.client.get(url)
#         self.assertEqual(response.status_code, 200)
#         response_json = response.json()
#         self.assertListEqual(list(response_json.keys()), ['rows'])
#         row_ids = ['NA19675_1_21_3343353', 'HG00731_1_248367227', 'HG00731_19_1912634', 'HG00731_19_1912633', 'HG00731_19_1912632']
#         self.assertListEqual([r['genetic_findings_id'] for r in response_json['rows']], row_ids)
#         expected_row = {
#             **BASE_VARIANT_METADATA_ROW,
#             'additional_family_members_with_variant': 'HG00732',
#             'alt': 'T',
#             'chrom': '1',
#             'clinvar': {'alleleId': None, 'clinicalSignificance': '', 'goldStars': None, 'variationId': None},
#             'condition_id': 'MONDO:0044970',
#             'condition_inheritance': None,
#             'displayName': '2',
#             'familyGuid': 'F000002_2',
#             'family_id': '2',
#             'gene': 'RP11',
#             'gene_id': 'ENSG00000135953',
#             'gene_known_for_phenotype': 'Known',
#             'genetic_findings_id': 'HG00731_1_248367227',
#             'known_condition_name': 'mitochondrial disease',
#             'participant_id': 'HG00731',
#             'phenotype_contribution': 'Full',
#             'phenotype_description': 'microcephaly; seizures',
#             'pos': 248367227,
#             'projectGuid': 'R0001_1kg',
#             'internal_project_id': '1kg project nåme with uniçøde',
#             'ref': 'TC',
#             'tags': ['Known gene for phenotype'],
#             'variant_inheritance': 'paternal',
#             'variant_reference_assembly': 'GRCh37',
#             'zygosity': 'Homozygous',
#         }
#         self.assertDictEqual(response_json['rows'][1], expected_row)
#         expected_mnv = {
#             **BASE_VARIANT_METADATA_ROW,
#             'alt': 'T',
#             'chrom': '19',
#             'condition_id': 'MONDO:0044970',
#             'condition_inheritance': None,
#             'displayName': '2',
#             'end': 1912634,
#             'familyGuid': 'F000002_2',
#             'family_id': '2',
#             'gene': 'OR4G11P',
#             'gene_id': 'ENSG00000240361',
#             'gene_known_for_phenotype': 'Known',
#             'genetic_findings_id': 'HG00731_19_1912634',
#             'known_condition_name': 'mitochondrial disease',
#             'notes': 'The following variants are part of the multinucleotide variant 19-1912632-GC-TT (c.586_587delinsTT, p.Ala196Leu): 19-1912633-G-T, 19-1912634-C-T',
#             'participant_id': 'HG00731',
#             'phenotype_description': 'microcephaly; seizures',
#             'pos': 1912634,
#             'projectGuid': 'R0001_1kg',
#             'internal_project_id': '1kg project nåme with uniçøde',
#             'ref': 'C',
#             'tags': ['Known gene for phenotype'],
#             'transcript': 'ENST00000371839',
#             'variant_inheritance': 'unknown',
#             'variant_reference_assembly': 'GRCh38',
#             'zygosity': 'Heterozygous',
#         }
#         self.assertDictEqual(response_json['rows'][2], expected_mnv)

#         # Test gregor projects
#         gregor_projects_url = reverse(variant_metadata, args=['gregor'])
#         response = self.client.get(gregor_projects_url)
#         self.assertEqual(response.status_code, 403)

#         self.login_analyst_user()
#         response = self.client.get(gregor_projects_url)
#         self.assertEqual(response.status_code, 200)
#         response_json = response.json()
#         self.assertListEqual(list(response_json.keys()), ['rows'])
#         row_ids += ['NA20889_1_248367227', 'NA20889_1_249045487']
#         self.assertListEqual([r['genetic_findings_id'] for r in response_json['rows']], row_ids)
#         self.assertDictEqual(response_json['rows'][1], expected_row)
#         self.assertDictEqual(response_json['rows'][2], expected_mnv)
#         self.assertDictEqual(response_json['rows'][5], {
#             **BASE_VARIANT_METADATA_ROW,
#             'MME': True,
#             'alt': 'T',
#             'chrom': '1',
#             'clinvar': {'alleleId': None, 'clinicalSignificance': '', 'goldStars': None, 'variationId': None},
#             'condition_id': 'MONDO:0008788',
#             'displayName': '12',
#             'familyGuid': 'F000012_12',
#             'family_id': '12',
#             'family_history': 'Yes',
#             'gene': 'OR4G11P',
#             'gene_id': 'ENSG00000240361',
#             'gene_known_for_phenotype': 'Candidate',
#             'genetic_findings_id': 'NA20889_1_248367227',
#             'hgvsc': 'c.3955G>A',
#             'hgvsp': 'c.1586-17C>G',
#             'participant_id': 'NA20889',
#             'pos': 248367227,
#             'projectGuid': 'R0003_test',
#             'internal_project_id': 'Test Reprocessed Project',
#             'ref': 'TC',
#             'seqr_chosen_consequence': 'intron_variant',
#             'tags': ['Tier 1 - Novel gene and phenotype'],
#             'transcript': 'ENST00000505820',
#             'variant_inheritance': 'unknown',
#             'variant_reference_assembly': 'GRCh37',
#             'zygosity': 'Heterozygous',
#         })
#         self.assertDictEqual(response_json['rows'][6], {
#             **BASE_VARIANT_METADATA_ROW,
#             'alt': None,
#             'chrom': '1',
#             'condition_id': 'MONDO:0008788',
#             'displayName': '12',
#             'end': 249045898,
#             'familyGuid': 'F000012_12',
#             'family_id': '12',
#             'family_history': 'Yes',
#             'gene': None,
#             'gene_id': None,
#             'gene_known_for_phenotype': 'Candidate',
#             'genetic_findings_id': 'NA20889_1_249045487',
#             'participant_id': 'NA20889',
#             'pos': 249045487,
#             'projectGuid': 'R0003_test',
#             'internal_project_id': 'Test Reprocessed Project',
#             'ref': None,
#             'svType': 'DEL',
#             'sv_name': 'DEL:chr1:249045487-249045898',
#             'tags': ['Tier 1 - Novel gene and phenotype'],
#             'variant_inheritance': 'unknown',
#             'variant_reference_assembly': 'GRCh37',
#             'zygosity': 'Heterozygous',
#         })

#         # Test all projects
#         all_projects_url = reverse(variant_metadata, args=['all'])
#         response = self.client.get(all_projects_url)
#         self.assertEqual(response.status_code, 200)
#         response_json = response.json()
#         self.assertListEqual(list(response_json.keys()), ['rows'])
#         row_ids += self.ADDITIONAL_FINDINGS
#         self.assertListEqual([r['genetic_findings_id'] for r in response_json['rows']], row_ids)
#         self.assertDictEqual(response_json['rows'][1], expected_row)
#         self.assertDictEqual(response_json['rows'][2], expected_mnv)

#         # Test empty project
#         empty_project_url = reverse(family_metadata, args=['R0002_empty'])
#         response = self.client.get(empty_project_url)
#         self.assertEqual(response.status_code, 200)
#         self.assertDictEqual(response.json(), {'rows': []})


# # Tests for AnVIL access disabled
# class LocalSummaryDataAPITest(AuthenticationTestCase, SummaryDataAPITest):
#     fixtures = ['users', '1kg_project', 'reference_data', 'report_variants']
#     NUM_MANAGER_SUBMISSIONS = 4
#     ADDITIONAL_SAMPLES = ['NA21234', 'NA21987']
#     ADDITIONAL_FAMILIES = ['F000014_14']
#     ADDITIONAL_FINDINGS = ['NA21234_1_248367227']


def assert_has_expected_calls(self, users, skip_group_call_idxs=None):
    calls = [mock.call(user) for user in users]
    self.mock_list_workspaces.assert_has_calls(calls)
    group_calls = [call for i, call in enumerate(calls) if i in skip_group_call_idxs] if skip_group_call_idxs else calls
    self.mock_get_groups.assert_has_calls(group_calls)
    self.mock_get_ws_acl.assert_not_called()
    self.mock_get_group_members.assert_not_called()


# Test for permissions from AnVIL only
# class AnvilSummaryDataAPITest(AnvilAuthenticationTestCase, SummaryDataAPITest):
#     fixtures = ['users', 'social_auth', '1kg_project', 'reference_data', 'report_variants']
#     NUM_MANAGER_SUBMISSIONS = 4
#     ADDITIONAL_SAMPLES = []
#     ADDITIONAL_FAMILIES = []
#     ADDITIONAL_FINDINGS = []

#     def test_mme_details(self, *args):
#         super(AnvilSummaryDataAPITest, self).test_mme_details(*args)
#         assert_has_expected_calls(self, [self.no_access_user, self.manager_user, self.analyst_user])
#         self.mock_get_ws_access_level.assert_not_called()

#     def test_saved_variants_page(self):
#         super(AnvilSummaryDataAPITest, self).test_saved_variants_page()
#         assert_has_expected_calls(self, [
#             self.no_access_user, self.manager_user, self.manager_user, self.analyst_user, self.analyst_user
#         ], skip_group_call_idxs=[2])
#         self.mock_get_ws_access_level.assert_called_with(
#             self.analyst_user, 'my-seqr-billing', 'anvil-1kg project nåme with uniçøde')