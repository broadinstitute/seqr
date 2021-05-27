from django.urls.base import reverse
from django.utils.dateparse import parse_datetime
import mock
import pytz
import responses
from settings import AIRTABLE_URL

from seqr.views.apis.report_api import seqr_stats, get_cmg_projects, discovery_sheet, anvil_export, \
    sample_metadata_export
from seqr.views.utils.test_utils import AuthenticationTestCase


PROJECT_GUID = 'R0001_1kg'
NON_PROJECT_GUID ='NON_GUID'
PROJECT_EMPTY_GUID = 'R0002_empty'
COMPOUND_HET_PROJECT_GUID = 'R0003_test'
NO_ANALYST_PROJECT_GUID = 'R0004_non_analyst_project'

EXPECTED_DISCOVERY_SHEET_ROW = \
    {'project_guid': 'R0001_1kg', 'pubmed_ids': '', 'posted_publicly': '',
     'solved': 'TIER 1 GENE', 'head_or_neck': 'N', 'analysis_complete_status': 'complete',
     'cardiovascular_system': 'N', 'n_kindreds_overlapping_sv_similar_phenotype': '2',
     'biochemical_function': 'Y', 'omim_number_post_discovery': '615120,615123',
     'genome_wide_linkage': 'NA 2', 'metabolism_homeostasis': 'N', 'growth': 'N',
     't0': '2017-02-05T06:42:55.397Z', 'months_since_t0': 38, 'sample_source': 'CMG',
     'integument': 'N', 'voice': 'N', 'skeletal_system': 'N',
     'expected_inheritance_model': 'Autosomal recessive inheritance',
     'extras_variant_tag_list': ['21-3343353-GAGA-G  RP11-206L10.5  tier 1 - novel gene and phenotype'],
     'protein_interaction': 'N', 'n_kindreds': '1', 'num_individuals_sequenced': 3,
     'musculature': 'Y', 'sequencing_approach': 'WES', 'neoplasm': 'N',
     'collaborator': '1kg project n\xe5me with uni\xe7\xf8de',
     'actual_inheritance_model': 'de novo', 'novel_mendelian_gene': 'Y',
     'endocrine_system': 'N', 'patient_cells': 'N', 'komp_early_release': 'N',
     'connective_tissue': 'N', 'prenatal_development_or_birth': 'N', 'rescue': 'N',
     'family_guid': 'F000001_1', 'immune_system': 'N',
     'analysis_summary': '<b>\r\n                        F\xe5mily analysis summ\xe5ry.\r\n                    </b>',
     'gene_count': 'NA', 'gene_id': 'ENSG00000135953', 'abdomen': 'N', 'limbs': 'N',
     'blood': 'N', 'phenotype_class': 'KNOWN', 'submitted_to_mme': 'Y',
     'n_unrelated_kindreds_with_causal_variants_in_gene': '3',
     'row_id': 'F000001_1ENSG00000135953', 'eye_defects': 'N', 'omim_number_initial': '12345',
     'p_value': 'NA', 'respiratory': 'N', 'nervous_system': 'Y', 'ear_defects': 'N',
     'thoracic_cavity': 'N', 'non_patient_cell_model': 'N',
     't0_copy': '2017-02-05T06:42:55.397Z', 'extras_pedigree_url': '/media/ped_1.png',
     'family_id': '1', 'genitourinary_system': 'N', 'coded_phenotype': '',
     'animal_model': 'N', 'non_human_cell_culture_model': 'N', 'expression': 'N',
     'gene_name': 'RP11-206L10.5', 'breast': 'N'}

EXPECTED_DISCOVERY_SHEET_COMPOUND_HET_ROW = {
    'project_guid': 'R0003_test', 'pubmed_ids': '', 'posted_publicly': '', 'solved': 'TIER 1 GENE', 'head_or_neck': 'N',
    'analysis_complete_status': 'complete', 'cardiovascular_system': 'Y',
    'n_kindreds_overlapping_sv_similar_phenotype': 'NA', 'biochemical_function': 'N', 'omim_number_post_discovery': 'NA',
    'genome_wide_linkage': 'NA', 'metabolism_homeostasis': 'N', 'growth': 'N', 't0': '2020-02-05T06:42:55.397Z',
    'months_since_t0': 2, 'sample_source': 'CMG', 'integument': 'N', 'voice': 'N', 'skeletal_system': 'N',
    'expected_inheritance_model': 'multiple', 'num_individuals_sequenced': 1, 'sequencing_approach': 'REAN',
    'extras_variant_tag_list': ['1-248367227-TC-T  OR4G11P  tier 1 - novel gene and phenotype',
        'prefix_19107_DEL  OR4G11P  tier 1 - novel gene and phenotype'], 'protein_interaction': 'N', 'n_kindreds': '1',
    'neoplasm': 'N', 'collaborator': 'Test Reprocessed Project', 'actual_inheritance_model': 'AR-comphet',
    'novel_mendelian_gene': 'Y', 'endocrine_system': 'N', 'komp_early_release': 'N', 'connective_tissue': 'N',
    'prenatal_development_or_birth': 'N', 'rescue': 'N', 'family_guid': 'F000011_11', 'immune_system': 'N',
    'analysis_summary': '', 'gene_count': 'NA', 'gene_id': 'ENSG00000240361', 'abdomen': 'N', 'limbs': 'N',
    'phenotype_class': 'New', 'submitted_to_mme': 'Y', 'n_unrelated_kindreds_with_causal_variants_in_gene': '1',
    'blood': 'N',  'row_id': 'F000011_11ENSG00000240361', 'eye_defects': 'N', 'omim_number_initial': 'NA',
    'p_value': 'NA', 'respiratory': 'N', 'nervous_system': 'N', 'ear_defects': 'N', 'thoracic_cavity': 'N',
    'non_patient_cell_model': 'N', 't0_copy': '2020-02-05T06:42:55.397Z', 'extras_pedigree_url': '/media/ped.png',
    'family_id': '11', 'genitourinary_system': 'N', 'coded_phenotype': '', 'animal_model': 'N', 'expression': 'N',
    'non_human_cell_culture_model': 'N', 'gene_name': 'OR4G11P', 'breast': 'N', 'musculature': 'N', 'patient_cells': 'N',}

AIRTABLE_SAMPLE_RECORDS = {
  "records": [
    {
      "id": "rec2B6OGmQpAkQW3s",
      "fields": {
        "SeqrCollaboratorSampleID": "NA19675",
        "CollaboratorSampleID": "VCGS_FAM203_621_D1",
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
        "CollaboratorSampleID": "VCGS_FAM203_621_D2",
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
      'id': 'rec2B6OGmQpfuRW3s',
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

EXPECTED_SAMPLE_METADATA_ROW = {
    "project_guid": "R0003_test",
    "num_saved_variants": 2,
    "dbgap_submission": "No",
    "solve_state": "Tier 1",
    "sample_id": "NA20885",
    "Gene_Class-1": "Tier 1 - Candidate",
    "Gene_Class-2": "Tier 1 - Candidate",
    "sample_provider": "",
    "inheritance_description-1": "Autosomal recessive (compound heterozygous)",
    "inheritance_description-2": "Autosomal recessive (compound heterozygous)",
    "hpo_absent": "",
    "novel_mendelian_gene-1": "Y",
    "novel_mendelian_gene-2": "Y",
    "hgvsc-1": "c.3955G>A",
    "date_data_generation": "2020-02-05",
    "Zygosity-1": "Heterozygous",
    "Zygosity-2": "Heterozygous",
    "variant_genome_build-1": "GRCh37",
    "variant_genome_build-2": "GRCh37",
    "Ref-1": "TC",
    "sv_type-2": "Deletion",
    "sv_name-2": "DEL:chr12:49045487-49045898",
    "multiple_datasets": "No",
    "ancestry_detail": "Ashkenazi Jewish",
    "maternal_id": "",
    "paternal_id": "",
    "hgvsp-1": "c.1586-17C>G",
    "entity:family_id": "11",
    "entity:discovery_id": "NA20885",
    "project_id": "Test Reprocessed Project",
    "Pos-1": "248367227",
    "data_type": "WES",
    "family_guid": "F000011_11",
    "congenital_status": "Unknown",
    "hpo_present": "HP:0011675 (Arrhythmia)|HP:0001509 ()",
    "Transcript-1": "ENST00000505820",
    "ancestry": "Ashkenazi Jewish",
    "phenotype_group": "",
    "sex": "Male",
    "entity:subject_id": "NA20885",
    "entity:sample_id": "NA20885",
    "Chrom-1": "1",
    "Alt-1": "T",
    "Gene-1": "OR4G11P",
    "pmid_id": "",
    "phenotype_description": "",
    "affected_status": "Affected",
    "family_id": "11",
    "MME": "Y",
    "subject_id": "NA20885",
    "proband_relationship": "",
    "consanguinity": "None suspected",
    "sequencing_center": "Broad",
  }


class ReportAPITest(AuthenticationTestCase):
    fixtures = ['users', '1kg_project', 'reference_data']

    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP')
    def test_seqr_stats(self, mock_analyst_group):
        url = reverse(seqr_stats)
        self.check_analyst_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        mock_analyst_group.__bool__.return_value = True
        mock_analyst_group.resolve_expression.return_value = 'analysts'

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'individualCount', 'familyCount', 'sampleCountByType'})
        self.assertEqual(response_json['individualCount'], 18)
        self.assertEqual(response_json['familyCount'], 14)
        self.assertDictEqual(response_json['sampleCountByType'], {'WES': 8})

    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP')
    def test_get_cmg_projects(self, mock_analyst_group):
        url = reverse(get_cmg_projects)
        self.check_analyst_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        mock_analyst_group.__bool__.return_value = True
        mock_analyst_group.resolve_expression.return_value = 'analysts'

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['projectGuids'])
        self.assertSetEqual(set(response_json['projectGuids']), {PROJECT_GUID, COMPOUND_HET_PROJECT_GUID})

    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP')
    @mock.patch('seqr.views.apis.report_api.timezone')
    def test_discovery_sheet(self, mock_timezone, mock_analyst_group):
        non_project_url = reverse(discovery_sheet, args=[NON_PROJECT_GUID])
        self.check_analyst_login(non_project_url)

        response = self.client.get(non_project_url)
        self.assertEqual(response.status_code, 403)
        mock_analyst_group.__bool__.return_value = True
        mock_analyst_group.resolve_expression.return_value = 'analysts'

        mock_timezone.now.return_value = pytz.timezone("US/Eastern").localize(parse_datetime("2020-04-27 20:16:01"), is_dst=None)
        response = self.client.get(non_project_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase, 'Invalid project {}'.format(NON_PROJECT_GUID))
        response_json = response.json()
        self.assertEqual(response_json['error'], 'Invalid project {}'.format(NON_PROJECT_GUID))

        unauthorized_project_url = reverse(discovery_sheet, args=[NO_ANALYST_PROJECT_GUID])
        response = self.client.get(unauthorized_project_url)
        self.assertEqual(response.status_code, 403)

        empty_project_url = reverse(discovery_sheet, args=[PROJECT_EMPTY_GUID])

        response = self.client.get(empty_project_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'rows', 'errors'})
        self.assertListEqual(response_json['rows'], [])
        self.assertListEqual(response_json['errors'], ["No data loaded for project: Empty Project"])

        url = reverse(discovery_sheet, args=[PROJECT_GUID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'rows', 'errors'})
        self.assertListEqual(response_json['errors'], ['No data loaded for family: no_individuals. Skipping...'])
        self.assertEqual(len(response_json['rows']), 10)
        self.assertIn(EXPECTED_DISCOVERY_SHEET_ROW, response_json['rows'])

        # test compound het reporting
        url = reverse(discovery_sheet, args=[COMPOUND_HET_PROJECT_GUID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'rows', 'errors'})
        self.assertListEqual(response_json['errors'], ['HPO category field not set for some HPO terms in 11'])
        self.assertEqual(len(response_json['rows']), 2)
        self.assertIn(EXPECTED_DISCOVERY_SHEET_COMPOUND_HET_ROW, response_json['rows'])

    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP')
    @mock.patch('seqr.views.utils.export_utils.zipfile.ZipFile')
    @mock.patch('seqr.views.apis.report_api.is_google_authenticated')
    @responses.activate
    def test_anvil_export(self, mock_google_authenticated,  mock_zip, mock_analyst_group):
        mock_google_authenticated.return_value = False
        url = reverse(anvil_export, args=[PROJECT_GUID])
        self.check_analyst_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'User has insufficient permission')
        mock_analyst_group.__bool__.return_value = True
        mock_analyst_group.resolve_expression.return_value = 'analysts'

        unauthorized_project_url = reverse(anvil_export, args=[NO_ANALYST_PROJECT_GUID])
        response = self.client.get(unauthorized_project_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()['error'], 'test_user does not have sufficient permissions for Non-Analyst Project')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()['error'], 'Error: To access airtable user must login with Google authentication.')
        mock_google_authenticated.return_value = True

        responses.add(responses.GET, '{}/Samples'.format(AIRTABLE_URL), json=AIRTABLE_SAMPLE_RECORDS, status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('content-disposition'),
            'attachment; filename="1kg project nme with unide_AnVIL_Metadata.zip"'
        )

        mock_write_zip = mock_zip.return_value.__enter__.return_value.writestr
        self.assertEqual(mock_write_zip.call_count, 4)
        mock_write_zip.assert_has_calls([
            mock.call('1kg project n\xe5me with uni\xe7\xf8de_PI_Subject.tsv', mock.ANY),
            mock.call('1kg project n\xe5me with uni\xe7\xf8de_PI_Sample.tsv', mock.ANY),
            mock.call('1kg project n\xe5me with uni\xe7\xf8de_PI_Family.tsv', mock.ANY),
            mock.call('1kg project n\xe5me with uni\xe7\xf8de_PI_Discovery.tsv', mock.ANY),
        ])

        subject_file = mock_write_zip.call_args_list[0][0][1].split('\n')
        self.assertEqual(subject_file[0], '\t'.join([
            'entity:subject_id', '01-subject_id', '02-prior_testing', '03-project_id', '04-pmid_id',
            '05-dbgap_submission', '06-dbgap_study_id', '07-dbgap_subject_id', '08-multiple_datasets',
            '09-family_id', '10-paternal_id', '11-maternal_id', '12-twin_id', '13-proband_relationship', '14-sex',
            '15-ancestry', '16-ancestry_detail', '17-age_at_last_observation', '18-phenotype_group', '19-disease_id',
            '20-disease_description', '21-affected_status', '22-congenital_status', '23-age_of_onset', '24-hpo_present',
            '25-hpo_absent', '26-phenotype_description', '27-solve_state']))
        self.assertIn(u'\t'.join([
            'NA19675_1', 'NA19675_1', '-', u'1kg project nme with unide', '-', 'Yes', 'dbgap_stady_id_1',
            'dbgap_subject_id_1', 'No', '1', 'NA19678', 'NA19679', '-', 'Self', 'Male', '-', '-', '-', '-',
            'OMIM:615120;OMIM:615123', 'Myasthenic syndrome; congenital; 8; with pre- and postsynaptic defects;',
            'Affected', 'Adult onset', '-', 'HP:0001631|HP:0002011|HP:0001636', 'HP:0011675|HP:0001674|HP:0001508', '-',
            'Tier 1']), subject_file)

        sample_file = mock_write_zip.call_args_list[1][0][1].split('\n')
        self.assertEqual(sample_file[0], '\t'.join([
            'entity:sample_id', '01-subject_id', '02-sample_id', '03-dbgap_sample_id', '04-sequencing_center',
            '05-sample_source', '06-tissue_affected_status',]))
        self.assertIn(
            '\t'.join(['NA19675_1', 'NA19675_1', 'NA19675', 'SM-A4GQ4', 'Broad', '-', '-']),
            sample_file,
        )

        family_file = mock_write_zip.call_args_list[2][0][1].split('\n')
        self.assertEqual(family_file[0], '\t'.join([
            'entity:family_id', '01-family_id', '02-consanguinity', '03-consanguinity_detail', '04-pedigree_image',
            '05-pedigree_detail', '06-family_history', '07-family_onset']))
        self.assertIn('\t'.join([
            '1', '1', 'Present', '-', '-', '-', '-', '-',
        ]), family_file)

        discovery_file = mock_write_zip.call_args_list[3][0][1].split('\n')
        self.assertEqual(discovery_file[0], '\t'.join([
            'entity:discovery_id', '01-subject_id', '02-sample_id', '03-Gene', '04-Gene_Class',
            '05-inheritance_description', '06-Zygosity', '07-variant_genome_build', '08-Chrom', '09-Pos',
            '10-Ref', '11-Alt', '12-hgvsc', '13-hgvsp', '14-Transcript', '15-sv_name', '16-sv_type',
            '17-significance']))
        self.assertIn('\t'.join([
            'HG00731', 'HG00731', 'HG00731', 'RP11-206L10.5', 'Known', 'Autosomal recessive (homozygous)',
            'Homozygous', 'GRCh37', '1', '248367227', 'TC', 'T', 'c.375_377delTCT', 'p.Leu126del', 'ENST00000258436',
            '-', '-', '-']), discovery_file)
        self.assertIn('\t'.join([
            'NA19675_1', 'NA19675_1', 'NA19675', 'RP11-206L10.5', 'Tier 1 - Candidate', 'de novo',
            'Heterozygous', 'GRCh37', '21', '3343353', 'GAGA', 'G', 'c.375_377delTCT', 'p.Leu126del', 'ENST00000258436',
            '-', '-', '-']), discovery_file)

        # Test non-broad analysts do not have access
        self.login_pm_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()['error'], 'Error: To access airtable user must login with Google authentication.')

    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_PROJECT_CATEGORY', 'analyst-projects')
    @mock.patch('seqr.views.utils.permissions_utils.ANALYST_USER_GROUP')
    @mock.patch('seqr.views.apis.report_api.is_google_authenticated')
    @responses.activate
    def test_sample_metadata_export(self, mock_google_authenticated, mock_analyst_group):
        mock_google_authenticated.return_value = False
        url = reverse(sample_metadata_export, args=[COMPOUND_HET_PROJECT_GUID])
        self.check_analyst_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'User has insufficient permission')
        mock_analyst_group.__bool__.return_value = True
        mock_analyst_group.resolve_expression.return_value = 'analysts'

        unauthorized_project_url = reverse(sample_metadata_export, args=[NO_ANALYST_PROJECT_GUID])
        response = self.client.get(unauthorized_project_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()['error'], 'test_user does not have sufficient permissions for Non-Analyst Project')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()['error'], 'Error: To access airtable user must login with Google authentication.')
        mock_google_authenticated.return_value = True

        # Test invalid airtable responses
        responses.add(responses.GET, '{}/Samples'.format(AIRTABLE_URL), status=402)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 402)

        responses.reset()
        responses.add(responses.GET, '{}/Samples'.format(AIRTABLE_URL), status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        self.assertIn(response.json()['error'], ['Unable to retrieve airtable data: No JSON object could be decoded',
                                        'Unable to retrieve airtable data: Expecting value: line 1 column 1 (char 0)'])

        responses.reset()
        responses.add(responses.GET, '{}/Samples'.format(AIRTABLE_URL),
                      json=PAGINATED_AIRTABLE_SAMPLE_RECORDS, status=200)
        responses.add(responses.GET, '{}/Samples'.format(AIRTABLE_URL),
                      json=AIRTABLE_SAMPLE_RECORDS, status=200)
        responses.add(responses.GET, '{}/Collaborator'.format(AIRTABLE_URL),
                      json=AIRTABLE_COLLABORATOR_RECORDS, status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()['error'],
            'Found multiple airtable records for sample NA19675 with mismatched values in field dbgap_study_id')
        self.assertEqual(len(responses.calls), 2)
        self.assertIsNone(responses.calls[0].request.params.get('offset'))
        self.assertEqual(responses.calls[1].request.params.get('offset'), 'abc123')

        # Test success
        responses.add(responses.GET, '{}/Collaborator'.format(AIRTABLE_URL),
                      json=AIRTABLE_COLLABORATOR_RECORDS, status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])
        self.assertIn(EXPECTED_SAMPLE_METADATA_ROW, response_json['rows'])

        # Test non-broad analysts do not have access
        self.login_pm_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()['error'], 'Error: To access airtable user must login with Google authentication.')
