from django.urls.base import reverse
from django.utils.dateparse import parse_datetime
import json
import mock
import pytz
import responses
from settings import AIRTABLE_URL

from seqr.models import Project
from seqr.views.apis.report_api import seqr_stats, get_category_projects, discovery_sheet, anvil_export, \
    sample_metadata_export, gregor_export
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase


PROJECT_GUID = 'R0001_1kg'
NON_PROJECT_GUID ='NON_GUID'
PROJECT_EMPTY_GUID = 'R0002_empty'
COMPOUND_HET_PROJECT_GUID = 'R0003_test'
NO_ANALYST_PROJECT_GUID = 'R0004_non_analyst_project'

EXPECTED_DISCOVERY_SHEET_ROW = \
    {'project_guid': 'R0001_1kg', 'pubmed_ids': '34415322; 33665635', 'posted_publicly': '',
     'solved': 'TIER 1 GENE', 'head_or_neck': 'N', 'analysis_complete_status': 'complete',
     'cardiovascular_system': 'N', 'n_kindreds_overlapping_sv_similar_phenotype': '2',
     'biochemical_function': 'Y', 'omim_number_post_discovery': '615120,615123',
     'genome_wide_linkage': 'NA 2', 'metabolism_homeostasis': 'N', 'growth': 'N',
     't0': '2017-02-05T06:42:55.397Z', 'months_since_t0': 38, 'sample_source': 'CMG',
     'integument': 'N', 'voice': 'N', 'skeletal_system': 'N',
     'expected_inheritance_model': 'Autosomal recessive inheritance',
     'extras_variant_tag_list': ['21-3343353-GAGA-G  RP11  tier 1 - novel gene and phenotype'],
     'protein_interaction': 'N', 'n_kindreds': '1', 'num_individuals_sequenced': 3,
     'musculature': 'Y', 'sequencing_approach': 'WES', 'neoplasm': 'N',
     'collaborator': '1kg project n\xe5me with uni\xe7\xf8de',
     'actual_inheritance_model': 'de novo', 'novel_mendelian_gene': 'Y',
     'endocrine_system': 'N', 'patient_cells': 'N', 'komp_early_release': 'N',
     'connective_tissue': 'N', 'prenatal_development_or_birth': 'N', 'rescue': 'N',
     'family_guid': 'F000001_1', 'immune_system': 'N',
     'analysis_summary': '*\r\nF\u00e5mily analysis summ\u00e5ry.\r\n*; Some additional follow up',
     'gene_count': 'NA', 'gene_id': 'ENSG00000135953', 'abdomen': 'N', 'limbs': 'N',
     'blood': 'N', 'phenotype_class': 'KNOWN', 'submitted_to_mme': 'Y',
     'n_unrelated_kindreds_with_causal_variants_in_gene': '3',
     'row_id': 'F000001_1ENSG00000135953', 'eye_defects': 'N', 'omim_number_initial': '12345',
     'p_value': 'NA', 'respiratory': 'N', 'nervous_system': 'Y', 'ear_defects': 'N',
     'thoracic_cavity': 'N', 'non_patient_cell_model': 'N',
     't0_copy': '2017-02-05T06:42:55.397Z', 'extras_pedigree_url': '/media/ped_1.png',
     'family_id': '1', 'genitourinary_system': 'N', 'coded_phenotype': 'myopathy',
     'animal_model': 'N', 'non_human_cell_culture_model': 'N', 'expression': 'N',
     'gene_name': 'RP11', 'breast': 'N'}

EXPECTED_DISCOVERY_SHEET_COMPOUND_HET_ROW = {
    'project_guid': 'R0003_test', 'pubmed_ids': '', 'posted_publicly': '', 'solved': 'TIER 1 GENE', 'head_or_neck': 'N',
    'analysis_complete_status': 'complete', 'cardiovascular_system': 'Y',
    'n_kindreds_overlapping_sv_similar_phenotype': 'NA', 'biochemical_function': 'N', 'omim_number_post_discovery': 'NA',
    'genome_wide_linkage': 'NA', 'metabolism_homeostasis': 'N', 'growth': 'N', 't0': '2017-02-05T06:42:55.397Z',
    'months_since_t0': 38, 'sample_source': 'CMG', 'integument': 'N', 'voice': 'N', 'skeletal_system': 'N',
    'expected_inheritance_model': 'multiple', 'num_individuals_sequenced': 2, 'sequencing_approach': 'REAN',
    'extras_variant_tag_list': ['1-248367227-TC-T  OR4G11P  tier 1 - novel gene and phenotype',
        'prefix_19107_DEL  OR4G11P  tier 1 - novel gene and phenotype'], 'protein_interaction': 'N', 'n_kindreds': '1',
    'neoplasm': 'N', 'collaborator': 'Test Reprocessed Project', 'actual_inheritance_model': 'AR-comphet',
    'novel_mendelian_gene': 'Y', 'endocrine_system': 'N', 'komp_early_release': 'N', 'connective_tissue': 'N',
    'prenatal_development_or_birth': 'N', 'rescue': 'N', 'family_guid': 'F000012_12', 'immune_system': 'N',
    'analysis_summary': '', 'gene_count': 'NA', 'gene_id': 'ENSG00000240361', 'abdomen': 'N', 'limbs': 'N',
    'phenotype_class': 'New', 'submitted_to_mme': 'Y', 'n_unrelated_kindreds_with_causal_variants_in_gene': '1',
    'blood': 'N',  'row_id': 'F000012_12ENSG00000240361', 'eye_defects': 'N', 'omim_number_initial': 'NA',
    'p_value': 'NA', 'respiratory': 'N', 'nervous_system': 'N', 'ear_defects': 'N', 'thoracic_cavity': 'N',
    'non_patient_cell_model': 'N', 't0_copy': '2017-02-05T06:42:55.397Z', 'extras_pedigree_url': '',
    'family_id': '12', 'genitourinary_system': 'N', 'coded_phenotype': '', 'animal_model': 'N', 'expression': 'N',
    'non_human_cell_culture_model': 'N', 'gene_name': 'OR4G11P', 'breast': 'N', 'musculature': 'N', 'patient_cells': 'N',}

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


AIRTABLE_GREGOR_SAMPLE_RECORDS = {
  "records": [
    {
      "id": "rec2B6OGmQpAkQW3s",
      "fields": {
        "SeqrCollaboratorSampleID": "VCGS_FAM203_621_D1",
        "CollaboratorSampleID": "NA19675_1",
        'SMID': 'SM-AGHT',
        'Recontactable': 'Yes',
      },
    },
    {
      "id": "rec2Nkg10N1KssPc3",
      "fields": {
        "SeqrCollaboratorSampleID": "HG00731",
        "CollaboratorSampleID": "VCGS_FAM203_621_D2",
        'SMID': 'SM-JDBTM',
      },
    }
]}
AIRTABLE_GREGOR_RECORDS = {
  "records": [
    {
      "id": "rec2B6OGmQpAkQW3s",
      "fields": {
        'SMID': 'SM-JDBTM',
        'seq_library_prep_kit_method': 'Kapa HyperPrep',
        'read_length': '151',
        'experiment_type': 'exome',
        'targeted_regions_method': 'Twist',
        'targeted_region_bed_file': 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/SR_experiment.bed',
        'date_data_generation': '2022-08-15',
        'target_insert_size': '385',
        'sequencing_platform': 'NovaSeq',
        'aligned_dna_short_read_file': 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_COL_FAM1_1_D1.cram',
        'aligned_dna_short_read_index_file': 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_COL_FAM1_1_D1.crai',
        'md5sum': '129c28163df082',
        'reference_assembly': 'GRCh38',
        'alignment_software': 'BWA-MEM-2.3',
        'mean_coverage': '42.4',
        'analysis_details': 'DOI:10.5281/zenodo.4469317',
        'called_variants_dna_short_read_id': 'SX2-3',
        'aligned_dna_short_read_set_id': 'BCM_H7YG5DSX2',
        'called_variants_dna_file': 'gs://fc-fed09429-e563-44a7-aaeb-776c8336ba02/COL_FAM1_1_D1.SV.vcf',
        'caller_software': 'gatk4.1.2',
        'variant_types': 'SNV',
      },
    },
    {
      "id": "rec2B6OGmCVzkQW3s",
      "fields": {
        'SMID': 'SM-AGHT',
      },
    },
]}

EXPECTED_NO_AIRTABLE_SAMPLE_METADATA_ROW = {
    "project_guid": "R0003_test",
    "num_saved_variants": 2,
    "solve_state": "Tier 1",
    "sample_id": "NA20889",
    "Gene_Class-1": "Tier 1 - Candidate",
    "Gene_Class-2": "Tier 1 - Candidate",
    "inheritance_description-1": "Autosomal recessive (compound heterozygous)",
    "inheritance_description-2": "Autosomal recessive (compound heterozygous)",
    "hpo_absent": "",
    "novel_mendelian_gene-1": "Y",
    "novel_mendelian_gene-2": "Y",
    "hgvsc-1": "c.3955G>A",
    "date_data_generation": "2017-02-05",
    "Zygosity-1": "Heterozygous",
    "Zygosity-2": "Heterozygous",
    "variant_genome_build-1": "GRCh37",
    "variant_genome_build-2": "GRCh37",
    "Ref-1": "TC",
    "sv_type-2": "Deletion",
    "sv_name-2": "DEL:chr12:49045487-49045898",
    "ancestry_detail": "Ashkenazi Jewish",
    "maternal_id": "",
    "paternal_id": "",
    "hgvsp-1": "c.1586-17C>G",
    "entity:family_id": "12",
    "entity:discovery_id": "NA20889",
    "project_id": "Test Reprocessed Project",
    "Pos-1": "248367227",
    "data_type": "WES",
    "family_guid": "F000012_12",
    "congenital_status": "Unknown",
    "family_history": "Yes",
    "hpo_present": "HP:0011675 (Arrhythmia)|HP:0001509 ()",
    "Transcript-1": "ENST00000505820",
    "ancestry": "Ashkenazi Jewish",
    "phenotype_group": "",
    "sex": "Female",
    "entity:subject_id": "NA20889",
    "entity:sample_id": "NA20889",
    "Chrom-1": "1",
    "Alt-1": "T",
    "Gene-1": "OR4G11P",
    "pmid_id": None,
    "phenotype_description": None,
    "affected_status": "Affected",
    "family_id": "12",
    "MME": "Y",
    "subject_id": "NA20889",
    "proband_relationship": "",
    "consanguinity": "None suspected",
    "sequencing_center": "Broad",
}
EXPECTED_SAMPLE_METADATA_ROW = {
    "dbgap_submission": "No",
    "dbgap_study_id": "",
    "dbgap_subject_id": "",
    "sample_provider": "",
    "multiple_datasets": "No",
}
EXPECTED_SAMPLE_METADATA_ROW.update(EXPECTED_NO_AIRTABLE_SAMPLE_METADATA_ROW)

MOCK_DATA_MODEL_URL = 'http://raw.githubusercontent.com/gregor_data_model.json'
MOCK_DATA_MODEL = {
    'name': 'test data model',
    'tables': [
        {
            'table': 'subject',
            'required': True,
            'columns': [{'column': 'subject_id', 'required': True}],
        },
        {
            'table': 'participant',
            'required': True,
            'columns': [
                {'column': 'participant_id', 'required': True},
                {'column': 'internal_project_id'},
                {'column': 'gregor_center', 'required': True, 'enumerations': ['BCM', 'BROAD', 'UW']},
                {'column': 'consent_code', 'required': True, 'enumerations': ['GRU', 'HMB']},
                {'column': 'recontactable', 'enumerations': ['Yes', 'No']},
                {'column': 'prior_testing'},
                {'column': 'family_id', 'required': True},
                {'column': 'paternal_id'},
                {'column': 'maternal_id'},
                {'column': 'proband_relationship', 'required': True},
                {'column': 'sex', 'required': True, 'enumerations': ['Male', 'Female', 'Unknown']},
                {'column': 'reported_race', 'enumerations': ['Asian', 'White', 'Black']},
                {'column': 'reported_ethnicity', 'enumerations': ['Hispanic or Latino', 'Not Hispanic or Latino']},
                {'column': 'ancestry_metadata'},
                {'column': 'affected_status', 'required': True, 'enumerations': ['Affected', 'Unaffected', 'Unknown']},
                {'column': 'phenotype_description'},
                {'column': 'age_at_enrollment'},
            ],
        },
        {
            'table': 'aligned_dna_short_read_set',
            'columns': [
                {'column': 'aligned_dna_short_read_set_id', 'required': True},
                {'column': 'aligned_dna_short_read_id', 'required': True},
            ],
        },
        {
            'table': 'dna_read_data',
            'columns': [{'column': 'analyte_id', 'required': True}],
        },
    ]
}


def _get_list_param(call, param):
    query_params = call.url.split('?')[1].split('&')
    param_str = f'{param}='
    return [p.replace(param_str, '') for p in query_params if p.startswith(param_str)]


class ReportAPITest(object):

    def _get_zip_files(self, mock_zip, filenames):
        mock_write_zip = mock_zip.return_value.__enter__.return_value.writestr
        self.assertEqual(mock_write_zip.call_count, len(filenames))
        mock_write_zip.assert_has_calls([mock.call(file, mock.ANY) for file in filenames])

        return (
            [row.split('\t') for row in mock_write_zip.call_args_list[i][0][1].split('\n') if row]
            for i in range(len(filenames))
        )

    def _assert_expected_airtable_call(self, call_index, filter_formula, fields, additional_params=None):
        expected_params = {
            'fields[]': mock.ANY,
            'pageSize': '100',
            'filterByFormula': filter_formula,
        }
        if additional_params:
            expected_params.update(additional_params)
        self.assertDictEqual(responses.calls[call_index].request.params, expected_params)
        self.assertListEqual(_get_list_param(responses.calls[call_index].request, 'fields%5B%5D'), fields)

    def test_seqr_stats(self):
        no_access_project = Project.objects.get(id=2)
        no_access_project.workspace_namespace = None
        no_access_project.save()

        url = reverse(seqr_stats)
        self.check_analyst_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'projectsCount', 'individualsCount', 'familiesCount', 'sampleCountsByType'})
        self.assertDictEqual(response_json['projectsCount'], self.STATS_DATA['projectsCount'])
        self.assertDictEqual(response_json['individualsCount'], self.STATS_DATA['individualsCount'])
        self.assertDictEqual(response_json['familiesCount'], self.STATS_DATA['familiesCount'])
        self.assertDictEqual(response_json['sampleCountsByType'], self.STATS_DATA['sampleCountsByType'])

        self.check_no_analyst_no_access(url)

    def test_get_category_projects(self):
        url = reverse(get_category_projects, args=['GREGoR'])
        self.check_analyst_login(url)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['projectGuids'])
        self.assertSetEqual(set(response_json['projectGuids']), {PROJECT_GUID, COMPOUND_HET_PROJECT_GUID})

        self.check_no_analyst_no_access(url)

    @mock.patch('seqr.views.apis.report_api.timezone')
    def test_discovery_sheet(self, mock_timezone):
        non_project_url = reverse(discovery_sheet, args=[NON_PROJECT_GUID])
        self.check_analyst_login(non_project_url)

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
        self.assertListEqual(response_json['errors'], ['No data loaded for family: 9. Skipping...', 'No data loaded for family: no_individuals. Skipping...'])
        self.assertEqual(len(response_json['rows']), 10)
        self.assertIn(EXPECTED_DISCOVERY_SHEET_ROW, response_json['rows'])

        # test compound het reporting
        url = reverse(discovery_sheet, args=[COMPOUND_HET_PROJECT_GUID])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertSetEqual(set(response_json.keys()), {'rows', 'errors'})
        self.assertListEqual(response_json['errors'], [
            'HPO category field not set for some HPO terms in 11', 'HPO category field not set for some HPO terms in 12',
        ])
        self.assertEqual(len(response_json['rows']), 2)
        self.assertIn(EXPECTED_DISCOVERY_SHEET_COMPOUND_HET_ROW, response_json['rows'])

        self.check_no_analyst_no_access(url)

    @mock.patch('seqr.views.utils.export_utils.zipfile.ZipFile')
    @mock.patch('seqr.views.utils.airtable_utils.is_google_authenticated')
    @responses.activate
    def test_anvil_export(self, mock_google_authenticated,  mock_zip):
        mock_google_authenticated.return_value = False
        url = reverse(anvil_export, args=[PROJECT_GUID])
        self.check_analyst_login(url)

        unauthorized_project_url = reverse(anvil_export, args=[NO_ANALYST_PROJECT_GUID])
        response = self.client.get(unauthorized_project_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')
        mock_google_authenticated.return_value = True

        responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL), json=AIRTABLE_SAMPLE_RECORDS, status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get('content-disposition'),
            'attachment; filename="1kg project nme with unide_AnVIL_Metadata.zip"'
        )

        subject_file, sample_file, family_file, discovery_file = self._get_zip_files(mock_zip, [
            '1kg project n\xe5me with uni\xe7\xf8de_PI_Subject.tsv',
            '1kg project n\xe5me with uni\xe7\xf8de_PI_Sample.tsv',
            '1kg project n\xe5me with uni\xe7\xf8de_PI_Family.tsv',
            '1kg project n\xe5me with uni\xe7\xf8de_PI_Discovery.tsv',
        ])

        self.assertEqual(subject_file[0], [
            'entity:subject_id', '01-subject_id', '02-prior_testing', '03-project_id', '04-pmid_id',
            '05-dbgap_study_id', '06-dbgap_subject_id', '07-multiple_datasets',
            '08-family_id', '09-paternal_id', '10-maternal_id', '11-twin_id', '12-proband_relationship', '13-sex',
            '14-ancestry', '15-ancestry_detail', '16-age_at_last_observation', '17-phenotype_group', '18-disease_id',
            '19-disease_description', '20-affected_status', '21-congenital_status', '22-age_of_onset', '23-hpo_present',
            '24-hpo_absent', '25-phenotype_description', '26-solve_state'])
        self.assertIn([
            'NA19675_1', 'NA19675_1', '-', u'1kg project nme with unide', '34415322', 'dbgap_stady_id_1',
            'dbgap_subject_id_1', 'No', '1', 'NA19678', 'NA19679', '-', 'Self', 'Male', 'Other', 'Middle Eastern', '-',
            '-', 'OMIM:615120;OMIM:615123', 'Myasthenic syndrome; congenital; 8; with pre- and postsynaptic defects;',
            'Affected', 'Adult onset', '-', 'HP:0001631|HP:0002011|HP:0001636', 'HP:0011675|HP:0001674|HP:0001508',
            'myopathy', 'Tier 1'], subject_file)

        self.assertEqual(sample_file[0], [
            'entity:sample_id', '01-subject_id', '02-sample_id', '03-dbgap_sample_id', '04-sequencing_center',
            '05-sample_source', '06-tissue_affected_status',])
        self.assertIn(
            ['NA19675_1', 'NA19675_1', 'NA19675', 'SM-A4GQ4', 'Broad', '-', '-'],
            sample_file,
        )

        self.assertEqual(family_file[0], [
            'entity:family_id', '01-family_id', '02-consanguinity', '03-consanguinity_detail', '04-pedigree_image',
            '05-pedigree_detail', '06-family_history', '07-family_onset'])
        self.assertIn([
            '1', '1', 'Present', '-', '-', '-', '-', '-',
        ], family_file)

        self.assertEqual(len(discovery_file), 6)
        self.assertEqual(discovery_file[0], [
            'entity:discovery_id', '01-subject_id', '02-sample_id', '03-Gene', '04-Gene_Class',
            '05-inheritance_description', '06-Zygosity', '07-variant_genome_build', '08-Chrom', '09-Pos',
            '10-Ref', '11-Alt', '12-hgvsc', '13-hgvsp', '14-Transcript', '15-sv_name', '16-sv_type',
            '17-significance', '18-discovery_notes'])
        self.assertIn([
            'HG00731', 'HG00731', 'HG00731', 'RP11', 'Known', 'Autosomal recessive (homozygous)',
            'Homozygous', 'GRCh37', '1', '248367227', 'TC', 'T', '-', '-', '-', '-', '-', '-', '-'], discovery_file)
        self.assertIn([
            'NA19675_1', 'NA19675_1', 'NA19675', 'RP11', 'Tier 1 - Candidate', 'de novo',
            'Heterozygous', 'GRCh37', '21', '3343353', 'GAGA', 'G', 'c.375_377delTCT', 'p.Leu126del', 'ENST00000258436',
            '-', '-', '-', '-'], discovery_file)
        self.assertIn([
            'HG00733', 'HG00733', 'HG00733', 'OR4G11P', 'Known', 'Unknown / Other', 'Heterozygous', 'GRCh38.p12', '19',
            '1912633', 'G', 'T', '-', '-', 'ENST00000371839', '-', '-', '-',
            'The following variants are part of the multinucleotide variant 19-1912632-GC-TT '
            '(c.586_587delinsTT, p.Ala196Leu): 19-1912633-G-T, 19-1912634-C-T'],
            discovery_file)
        self.assertIn([
            'HG00733', 'HG00733', 'HG00733', 'OR4G11P', 'Known', 'Unknown / Other', 'Heterozygous', 'GRCh38.p12', '19',
            '1912634', 'C', 'T', '-', '-', 'ENST00000371839', '-', '-', '-',
            'The following variants are part of the multinucleotide variant 19-1912632-GC-TT (c.586_587delinsTT, '
            'p.Ala196Leu): 19-1912633-G-T, 19-1912634-C-T'],
            discovery_file)

        self.check_no_analyst_no_access(url)

        # Test non-broad analysts do not have access
        self.login_pm_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

    @mock.patch('seqr.views.utils.airtable_utils.MAX_OR_FILTERS', 2)
    @mock.patch('seqr.views.utils.airtable_utils.AIRTABLE_API_KEY', 'mock_key')
    @mock.patch('seqr.views.utils.airtable_utils.is_google_authenticated')
    @responses.activate
    def test_sample_metadata_export(self, mock_google_authenticated):
        mock_google_authenticated.return_value = False
        url = reverse(sample_metadata_export, args=[COMPOUND_HET_PROJECT_GUID])
        self.check_analyst_login(url)

        unauthorized_project_url = reverse(sample_metadata_export, args=[NO_ANALYST_PROJECT_GUID])
        response = self.client.get(unauthorized_project_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual( response.json()['error'], 'Permission Denied')
        mock_google_authenticated.return_value = True

        # Test invalid airtable responses
        responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL), status=402)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 402)

        responses.reset()
        responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL), status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        self.assertIn(response.json()['error'], ['Unable to retrieve airtable data: No JSON object could be decoded',
                                        'Unable to retrieve airtable data: Expecting value: line 1 column 1 (char 0)'])

        responses.reset()
        responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL),
                      json=PAGINATED_AIRTABLE_SAMPLE_RECORDS, status=200)
        responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL),
                      json=AIRTABLE_SAMPLE_RECORDS, status=200)
        responses.add(responses.GET, '{}/app3Y97xtbbaOopVR/Collaborator'.format(AIRTABLE_URL),
                      json=AIRTABLE_COLLABORATOR_RECORDS, status=200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()['error'],
            'Found multiple airtable records for sample NA19675 with mismatched values in field dbgap_study_id')
        self.assertEqual(len(responses.calls), 4)
        first_formula = "OR({CollaboratorSampleID}='NA20885',{CollaboratorSampleID}='NA20888')"
        expected_fields = [
            'CollaboratorSampleID', 'Collaborator', 'dbgap_study_id', 'dbgap_subject_id',
            'dbgap_sample_id', 'SequencingProduct', 'dbgap_submission',
        ]
        self._assert_expected_airtable_call(0, first_formula, expected_fields)
        self._assert_expected_airtable_call(1, first_formula, expected_fields, additional_params={'offset': 'abc123'})
        self._assert_expected_airtable_call(2, "OR({CollaboratorSampleID}='NA20889')", expected_fields)
        second_formula = "OR({SeqrCollaboratorSampleID}='NA20888',{SeqrCollaboratorSampleID}='NA20889')"
        expected_fields[0] = 'SeqrCollaboratorSampleID'
        self._assert_expected_airtable_call(3, second_formula, expected_fields)

        # Test success
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])
        self.assertEqual(len(response_json['rows']), 3)
        expected_samples = {'NA20885', 'NA20888', 'NA20889'}
        self.assertSetEqual({r['sample_id'] for r in response_json['rows']}, expected_samples)
        test_row = next(r for r in response_json['rows'] if r['sample_id'] == 'NA20889')
        self.assertDictEqual(EXPECTED_SAMPLE_METADATA_ROW, test_row)
        self.assertEqual(len(responses.calls), 8)
        self._assert_expected_airtable_call(
            -1, "OR(RECORD_ID()='recW24C2CJW5lT64K',RECORD_ID()='reca4hcBnbA2cnZf9')", ['CollaboratorID'])
        self.assertSetEqual({call.request.headers['Authorization'] for call in responses.calls}, {'Bearer mock_key'})

        # Test omit airtable columns
        responses.reset()
        response = self.client.get(f'{url}?omitAirtable=true')
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])
        self.assertEqual(len(response_json['rows']), 3)
        expected_samples = {'NA20885', 'NA20888', 'NA20889'}
        self.assertSetEqual({r['sample_id'] for r in response_json['rows']}, expected_samples)
        test_row = next(r for r in response_json['rows'] if r['sample_id'] == 'NA20889')
        self.assertDictEqual(EXPECTED_NO_AIRTABLE_SAMPLE_METADATA_ROW, test_row)

        # Test empty project
        empty_project_url = reverse(sample_metadata_export, args=[PROJECT_EMPTY_GUID])
        response = self.client.get(empty_project_url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {'rows': []})

        # Test all projects
        all_projects_url = reverse(sample_metadata_export, args=['all'])
        response = self.client.get(all_projects_url)
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertListEqual(list(response_json.keys()), ['rows'])
        expected_samples.update({
            'NA19679', 'NA20870', 'HG00732', 'NA20876', 'NA20874', 'NA20875', 'NA19678', 'NA19675', 'HG00731',
            'NA20872', 'NA20881', 'HG00733',
        })
        expected_samples.update(self.ADDITIONAL_SAMPLES)
        self.assertSetEqual({r['sample_id'] for r in response_json['rows']}, expected_samples)
        test_row = next(r for r in response_json['rows'] if r['sample_id'] == 'NA20889')
        self.assertDictEqual(EXPECTED_NO_AIRTABLE_SAMPLE_METADATA_ROW, test_row)

        self.check_no_analyst_no_access(url)

        # Test non-broad analysts do not have access
        self.login_pm_user()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

    @mock.patch('seqr.views.apis.report_api.GREGOR_DATA_MODEL_URL', MOCK_DATA_MODEL_URL)
    @mock.patch('seqr.views.utils.airtable_utils.is_google_authenticated')
    @mock.patch('seqr.views.apis.report_api.datetime')
    @mock.patch('seqr.views.utils.export_utils.open')
    @mock.patch('seqr.views.utils.export_utils.TemporaryDirectory')
    @mock.patch('seqr.utils.file_utils.subprocess.Popen')
    @responses.activate
    def test_gregor_export(self, mock_subprocess, mock_temp_dir, mock_open, mock_datetime, mock_google_authenticated):
        mock_datetime.now.return_value.year = 2020
        mock_google_authenticated.return_value = False
        mock_temp_dir.return_value.__enter__.return_value = '/mock/tmp'
        mock_subprocess.return_value.wait.return_value = 1

        responses.add(
            responses.GET, '{}/app3Y97xtbbaOopVR/Samples'.format(AIRTABLE_URL), json=AIRTABLE_GREGOR_SAMPLE_RECORDS,
            status=200)
        responses.add(
            responses.GET, '{}/app3Y97xtbbaOopVR/GREGoR Data Model'.format(AIRTABLE_URL), json=AIRTABLE_GREGOR_RECORDS,
            status=200)
        responses.add(responses.GET, MOCK_DATA_MODEL_URL, json=MOCK_DATA_MODEL, status=200)

        url = reverse(gregor_export)
        self.check_analyst_login(url)

        response = self.client.post(url, content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Missing required field(s): consentCode, deliveryPath'])

        body = {'consentCode': 'HMB', 'deliveryPath': '/test/file'}
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Delivery Path must be a valid google bucket path (starts with gs://)'])

        body['deliveryPath'] = 'gs://anvil-upload'
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        self.assertListEqual(response.json()['errors'], ['Invalid Delivery Path: folder not found'])

        mock_subprocess.return_value.wait.return_value = 0
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission Denied')

        mock_google_authenticated.return_value = True
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 400)
        expected_files = [
            'participant', 'family', 'phenotype', 'analyte', 'experiment_dna_short_read',
            'aligned_dna_short_read', 'aligned_dna_short_read_set', 'called_variants_dna_short_read',
        ]
        skipped_file_validation_warnings = [
            f'No data model found for "{file}" table so no validation was performed' for file in expected_files
        ]
        self.assertListEqual(response.json()['warnings'], [
            'The following tables are required in the data model but absent from the reports: subject',
            'The following columns are included in the "participant" table but are missing from the data model: age_at_last_observation, ancestry_detail, pmid_id, proband_relationship_detail, sex_detail, twin_id',
            'The following columns are included in the "participant" data model but are missing in the report: ancestry_metadata',
            'The following entries are missing recommended "recontactable" in the "participant" table: Broad_HG00731, Broad_HG00732, Broad_HG00733, Broad_NA19678, Broad_NA19679, Broad_NA20870, Broad_NA20872, Broad_NA20874, Broad_NA20875, Broad_NA20876, Broad_NA20877, Broad_NA20881',
            'The following entries are missing recommended "reported_race" in the "participant" table: Broad_HG00732, Broad_HG00733, Broad_NA19678, Broad_NA19679, Broad_NA20870, Broad_NA20872, Broad_NA20874, Broad_NA20875, Broad_NA20876, Broad_NA20877, Broad_NA20881',
            'The following entries are missing recommended "phenotype_description" in the "participant" table: Broad_HG00731, Broad_HG00732, Broad_HG00733, Broad_NA20870, Broad_NA20872, Broad_NA20874, Broad_NA20875, Broad_NA20876, Broad_NA20877, Broad_NA20881',
            'The following entries are missing recommended "age_at_enrollment" in the "participant" table: Broad_HG00731, Broad_NA20870, Broad_NA20872, Broad_NA20875, Broad_NA20876, Broad_NA20877, Broad_NA20881',
        ] + skipped_file_validation_warnings[1:6] + skipped_file_validation_warnings[7:])
        self.assertListEqual(response.json()['errors'], [
            'The following entries are missing required "proband_relationship" in the "participant" table: Broad_HG00731, Broad_HG00732, Broad_HG00733, Broad_NA19678, Broad_NA19679, Broad_NA20870, Broad_NA20872, Broad_NA20874, Broad_NA20875, Broad_NA20876, Broad_NA20877, Broad_NA20881',
            'The following entries have invalid values for "reported_race" in the "participant" table. Allowed values: Asian, White, Black. Invalid values: Broad_NA19675_1 (Middle Eastern or North African)',
            'The following entries are missing required "aligned_dna_short_read_set_id" (from Airtable) in the "aligned_dna_short_read_set" table: NA19675_1',
        ])

        responses.add(responses.GET, MOCK_DATA_MODEL_URL, status=404)
        responses.calls.reset()
        mock_subprocess.reset_mock()
        mock_google_authenticated.return_value = True
        response = self.client.post(url, content_type='application/json', data=json.dumps(body))
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {
            'info': ['Successfully validated and uploaded Gregor Report for 9 families'],
            'warnings': [
                'Unable to load data model for validation: 404 Client Error: Not Found for url: http://raw.githubusercontent.com/gregor_data_model.json',
            ] + skipped_file_validation_warnings,
        })

        self.assertListEqual(
            mock_open.call_args_list, [mock.call(f'/mock/tmp/{file}.tsv', 'w') for file in expected_files])
        files = [
            [row.split('\t') for row in write_call.args[0].split('\n')]
            for write_call in mock_open.return_value.__enter__.return_value.write.call_args_list
        ]
        participant_file, family_file, phenotype_file, analyte_file, experiment_file, read_file, read_set_file, called_file = files

        self.assertEqual(len(participant_file), 14)
        self.assertEqual(participant_file[0], [
            'participant_id', 'internal_project_id', 'gregor_center', 'consent_code', 'recontactable', 'prior_testing',
            'pmid_id', 'family_id', 'paternal_id', 'maternal_id', 'twin_id', 'proband_relationship',
            'proband_relationship_detail', 'sex', 'sex_detail', 'reported_race', 'reported_ethnicity', 'ancestry_detail',
            'age_at_last_observation', 'affected_status', 'phenotype_description', 'age_at_enrollment',
        ])
        row = next(r for r in participant_file if r[0] == 'Broad_NA19675_1')
        self.assertListEqual([
            'Broad_NA19675_1', 'Broad_1kg project nme with unide', 'BROAD', 'HMB', 'Yes', 'IKBKAP|CCDC102B|CMA - normal',
            '34415322|33665635', 'Broad_1', 'Broad_NA19678', 'Broad_NA19679', '', 'Self', '', 'Male', '',
            'Middle Eastern or North African', '', '', '21', 'Affected', 'myopathy', '18',
        ], row)
        hispanic_row = next(r for r in participant_file if r[0] == 'Broad_HG00731')
        self.assertListEqual([
            'Broad_HG00731', 'Broad_1kg project nme with unide', 'BROAD', 'HMB', '', '', '', 'Broad_2', 'Broad_HG00732',
            'Broad_HG00733', '', '', '', 'Female', '', '', 'Hispanic or Latino', 'Other', '', 'Affected', '', '',
        ], hispanic_row)

        self.assertEqual(len(family_file), 10)
        self.assertEqual(family_file[0], [
            'family_id', 'consanguinity', 'consanguinity_detail', 'pedigree_file', 'pedigree_file_detail',
            'family_history_detail',
        ])
        self.assertIn(['Broad_1', 'Present', '', '', '', ''], family_file)

        self.assertEqual(len(phenotype_file), 10)
        self.assertEqual(phenotype_file[0], [
            'phenotype_id', 'participant_id', 'term_id', 'presence', 'ontology', 'additional_details',
            'onset_age_range', 'additional_modifiers',
        ])
        self.assertIn([
            '', 'Broad_NA19675_1', 'HP:0002011', 'Present', 'HPO', '', 'HP:0003593', 'HP:0012825|HP:0003680',
        ], phenotype_file)
        self.assertIn([
            '', 'Broad_NA19675_1', 'HP:0001674', 'Absent', 'HPO', 'originally indicated', '', '',
        ], phenotype_file)

        self.assertEqual(len(analyte_file), 14)
        self.assertEqual(analyte_file[0], [
            'analyte_id', 'participant_id', 'analyte_type', 'analyte_processing_details', 'primary_biosample',
            'primary_biosample_id', 'primary_biosample_details', 'tissue_affected_status', 'age_at_collection',
            'participant_drugs_intake', 'participant_special_diet', 'hours_since_last_meal', 'passage_number',
            'time_to_freeze', 'sample_transformation_detail', 'quality_issues',
        ])
        row = next(r for r in analyte_file if r[1] == 'Broad_NA19675_1')
        self.assertListEqual(
            ['Broad_SM-AGHT', 'Broad_NA19675_1', 'DNA', '', 'UBERON:0003714', '', '', 'No', '', '', '', '', '', '', '', ''],
            row)

        self.assertEqual(len(experiment_file), 3)
        self.assertEqual(experiment_file[0], [
            'experiment_dna_short_read_id', 'analyte_id', 'experiment_sample_id', 'seq_library_prep_kit_method',
            'read_length', 'experiment_type', 'targeted_regions_method', 'targeted_region_bed_file',
            'date_data_generation', 'target_insert_size', 'sequencing_platform',
        ])
        self.assertIn([
            'Broad_exome_VCGS_FAM203_621_D2', 'Broad_SM-JDBTM', 'VCGS_FAM203_621_D2', 'Kapa HyperPrep', '151', 'exome',
            'Twist', 'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/SR_experiment.bed', '2022-08-15', '385', 'NovaSeq',
        ], experiment_file)
        self.assertIn(['Broad_NA_NA19675_1', 'Broad_SM-AGHT', 'NA19675_1', '', '', '', '', '', '', '', ''], experiment_file)

        self.assertEqual(len(read_file), 3)
        self.assertEqual(read_file[0], [
            'aligned_dna_short_read_id', 'experiment_dna_short_read_id', 'aligned_dna_short_read_file',
            'aligned_dna_short_read_index_file', 'md5sum', 'reference_assembly', 'reference_assembly_uri', 'reference_assembly_details',
            'alignment_software', 'mean_coverage', 'analysis_details',  'quality_issues',
        ])
        self.assertIn([
            'Broad_exome_VCGS_FAM203_621_D2_1', 'Broad_exome_VCGS_FAM203_621_D2',
            'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_COL_FAM1_1_D1.cram',
            'gs://fc-eb352699-d849-483f-aefe-9d35ce2b21ac/Broad_COL_FAM1_1_D1.crai', '129c28163df082', 'GRCh38',
            '', '', 'BWA-MEM-2.3', '42.4', 'DOI:10.5281/zenodo.4469317', '',
        ], read_file)

        self.assertEqual(len(read_set_file), 3)
        self.assertEqual(read_set_file[0], ['aligned_dna_short_read_set_id', 'aligned_dna_short_read_id'])
        self.assertIn(['BCM_H7YG5DSX2', 'Broad_exome_VCGS_FAM203_621_D2_1'], read_set_file)

        self.assertEqual(len(called_file), 2)
        self.assertEqual(called_file[0], [
            'called_variants_dna_short_read_id', 'aligned_dna_short_read_set_id', 'called_variants_dna_file', 'md5sum',
            'caller_software', 'variant_types', 'analysis_details',
        ])
        self.assertEqual(called_file[1], [
            'SX2-3', 'BCM_H7YG5DSX2', 'gs://fc-fed09429-e563-44a7-aaeb-776c8336ba02/COL_FAM1_1_D1.SV.vcf',
            '129c28163df082', 'gatk4.1.2', 'SNV', 'DOI:10.5281/zenodo.4469317',
        ])

        # test airtable calls
        self.assertEqual(len(responses.calls), 4)
        sample_filter = "OR({CollaboratorSampleID}='HG00731',{CollaboratorSampleID}='HG00732',{CollaboratorSampleID}='HG00733'," \
                        "{CollaboratorSampleID}='NA19675_1',{CollaboratorSampleID}='NA19678',{CollaboratorSampleID}='NA19679'," \
                        "{CollaboratorSampleID}='NA20870',{CollaboratorSampleID}='NA20872',{CollaboratorSampleID}='NA20874'," \
                        "{CollaboratorSampleID}='NA20875',{CollaboratorSampleID}='NA20876',{CollaboratorSampleID}='NA20877'," \
                        "{CollaboratorSampleID}='NA20881')"
        sample_fields = ['CollaboratorSampleID', 'SMID', 'CollaboratorSampleID', 'Recontactable']
        self._assert_expected_airtable_call(0, sample_filter, sample_fields)
        secondary_sample_filter = "OR({SeqrCollaboratorSampleID}='HG00731',{SeqrCollaboratorSampleID}='HG00732'," \
                        "{SeqrCollaboratorSampleID}='HG00733',{SeqrCollaboratorSampleID}='NA19678'," \
                        "{SeqrCollaboratorSampleID}='NA19679',{SeqrCollaboratorSampleID}='NA20870',{SeqrCollaboratorSampleID}='NA20872'," \
                        "{SeqrCollaboratorSampleID}='NA20874',{SeqrCollaboratorSampleID}='NA20875',{SeqrCollaboratorSampleID}='NA20876'," \
                        "{SeqrCollaboratorSampleID}='NA20877',{SeqrCollaboratorSampleID}='NA20881')"
        sample_fields[0] = 'SeqrCollaboratorSampleID'
        self._assert_expected_airtable_call(1, secondary_sample_filter, sample_fields)
        metadata_fields = [
            'SMID', 'aligned_dna_short_read_file', 'aligned_dna_short_read_index_file', 'aligned_dna_short_read_set_id',
            'alignment_software', 'analysis_details', 'analysis_details', 'called_variants_dna_file',
            'called_variants_dna_short_read_id', 'caller_software', 'date_data_generation', 'experiment_type',
            'md5sum', 'md5sum', 'mean_coverage', 'read_length', 'reference_assembly', 'seq_library_prep_kit_method',
            'sequencing_platform', 'target_insert_size', 'targeted_region_bed_file', 'targeted_regions_method',
            'variant_types',
        ]
        self._assert_expected_airtable_call(2, "OR(SMID='SM-AGHT',SMID='SM-JDBTM')", metadata_fields)

        self.assertEqual(responses.calls[3].request.url, MOCK_DATA_MODEL_URL)

        # test gsutil commands
        mock_subprocess.assert_has_calls([
            mock.call('gsutil ls gs://anvil-upload', stdout=-1, stderr=-2, shell=True),
            mock.call().wait(),
            mock.call('gsutil mv /mock/tmp/* gs://anvil-upload', stdout=-1, stderr=-2, shell=True),
            mock.call().wait(),
        ])

        self.check_no_analyst_no_access(url)


class LocalReportAPITest(AuthenticationTestCase, ReportAPITest):
    fixtures = ['users', '1kg_project', 'reference_data', 'report_variants']
    ADDITIONAL_SAMPLES = ['NA21234']
    STATS_DATA = {
        'projectsCount': {'non_demo': 3, 'demo': 1},
        'familiesCount': {'non_demo': 12, 'demo': 2},
        'individualsCount': {'non_demo': 16, 'demo': 4},
        'sampleCountsByType': {
            'WES__VARIANTS': {'demo': 1, 'non_demo': 7},
            'WGS__MITO': {'non_demo': 1},
            'WES__SV': {'non_demo': 3},
            'WGS__SV': {'non_demo': 1},
            'RNA__VARIANTS': {'non_demo': 4},
        },
    }


class AnvilReportAPITest(AnvilAuthenticationTestCase, ReportAPITest):
    fixtures = ['users', 'social_auth', '1kg_project', 'reference_data', 'report_variants']
    ADDITIONAL_SAMPLES = []
    STATS_DATA = {
        'projectsCount': {'internal': 1, 'external': 1, 'no_anvil': 1, 'demo': 1},
        'familiesCount': {'internal': 11, 'external': 1, 'no_anvil': 0, 'demo': 2},
        'individualsCount': {'internal': 14, 'external': 2, 'no_anvil': 0, 'demo': 4},
        'sampleCountsByType': {
            'WES__VARIANTS': {'internal': 7, 'demo': 1},
            'WGS__MITO': {'internal': 1},
            'WES__SV': {'internal': 3},
            'WGS__SV': {'external': 1},
            'RNA__VARIANTS': {'internal': 4},
        },
    }
