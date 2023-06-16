import datetime
import mock
from openpyxl import load_workbook
from io import BytesIO

from seqr.models import Project
from seqr.views.utils.pedigree_info_utils import parse_pedigree_table, ErrorsWarningsException
from seqr.views.utils.test_utils import AuthenticationTestCase, AnvilAuthenticationTestCase

FILENAME = 'test.csv'


class PedigreeInfoUtilsTest(object):

    @mock.patch('seqr.views.utils.pedigree_info_utils.date')
    def test_parse_datstat_pedigree_table(self, mock_date):
        mock_date.today.return_value = datetime.date(2020, 1, 1)

        records, warnings = parse_pedigree_table(
        [['participant_guid', 'familyId', 'RELATIONSHIP', 'RELATIONSHIP_OTHER_DETAILS', 'WEBSITE', 'DESCRIPTION', 'CLINICAL_DIAGNOSES', 'CLINICAL_DIAGNOSES_DETAILS', 'GENETIC_DIAGNOSES', 'GENETIC_DIAGNOSES_DETAILS', 'FIND_OUT_DOCTOR_DETAILS', 'PATIENT_AGE', 'CONDITION_AGE', 'PATIENT_DECEASED', 'DECEASED_AGE', 'DECEASED_CAUSE', 'DECEASED_DNA', 'PATIENT_SEX', 'RACE', 'ETHNICITY', 'DOCTOR_TYPES', 'DOCTOR_TYPES_OTHER_DETAILS', 'TESTS', 'TESTS_MICROARRAY_YEAR', 'TESTS_MICROARRAY_LAB', 'TESTS_MICROARRAY_FAMILY', 'TESTS_MICROARRAY_FAMILY_OTHER_DETAILS',  'TESTS_WEXOME_YEAR', 'TESTS_WEXOME_LAB', 'TESTS_WEXOME_FAMILY', 'TESTS_WEXOME_FAMILY_OTHER_DETAILS', 'TESTS_WGENOME_YEAR', 'TESTS_WGENOME_LAB', 'TESTS_WGENOME_FAMILY', 'TESTS_WGENOME_FAMILY_OTHER_DETAILS', 'TESTS_OTHER_DETAILS', 'BIOPSY', 'BIOPSY_OTHER_DETAILS', 'OTHER_STUDIES', 'OTHER_STUDIES_DESCRIBE', 'EXPECT_RESULTS', 'MOTHER_SAME_CONDITION', 'MOTHER_CONDITION_AGE', 'MOTHER_RACE', 'MOTHER_ETHNICITY', 'MOTHER_CAN_PARTICIPATE', 'MOTHER_DECEASED', 'MOTHER_DECEASED_DNA', 'FATHER_SAME_CONDITION', 'FATHER_CONDITION_AGE', 'FATHER_RACE', 'FATHER_ETHNICITY', 'FATHER_CAN_PARTICIPATE', 'FATHER_DECEASED', 'FATHER_DECEASED_DNA', 'NO_SIBLINGS', 'SIBLING', 'NO_CHILDREN', 'CHILD', 'NO_RELATIVE_AFFECTED', 'RELATIVE', 'FAMILY_INFO'],
        ['1518231365', '123', 'OTHER', 'Grandchild', 'wwww.myblog.com', 'I have a really debilitating probably genetic condition. I\xe2ve seen many specialists.', 'YES', 'SMA\xe2s', 'YES', 'Dwarfism\xe2', 'Dr John Smith', '34', '21', 'YES', '33', 'heart attack', 'NO', 'MALE', 'WHITE,ASIAN,PACIFIC', 'NOT_HISPANIC', 'CLIN_GEN,NEURO,CARDIO,OTHER', 'Pediatrician', 'SINGLE_GENE,GENE_PANEL,WEXOME,WGENOME,OTHER', '', '', '', '', '2018', 'UDN\xe2s lab', 'PARENT,AUNT_UNCLE,NIECE_NEPHEW,OTHER', 'Grandmother',  '', '', '', 'Grandmother', 'Blood work', 'MUSCLE,SKIN,OTHER', 'Bone\xe2s', 'YES', 'Undiagnosed Diseases Network', 'NO', 'YES', '19', 'WHITE,ASIAN', 'NOT_HISPANIC', 'YES', '', '', 'NO', '', '', 'BLACK', 'PREFER_NOT_ANSWER', 'YES', 'NO', '', '[{"SIBLING_SEX":"FEMALE","SIBLING_AGE":"21","SIBLING_RACE":"WHITE","SIBLING_ETHNICITY":"NOT_HISPANIC","SIBLING_SAME_CONDITION":"YES","SIBLING_CONDITION_AGE":null,"SIBLING_CAN_PARTICIPATE":"NO"},{"SIBLING_SEX":"","SIBLING_AGE":"17","SIBLING_RACE": "WHITE","SIBLING_ETHNICITY":"NOT_HISPANIC","SIBLING_SAME_CONDITION":"","SIBLING_CONDITION_AGE":"","SIBLING_CAN_PARTICIPATE":"YES"}]', 'YES', '', 'NO', '[{"RELATIVE_SEX":"MALE","RELATIVE_AGE":"44","RELATIVE_RACE": "WHITE", "RELATIVE_ETHNICITY":"NOT_HISPANIC","RELATIVE_CONDITION_AGE":null,"RELATIVE_CAN_PARTICIPATE":null}]', 'patient\xe2s uncle (dads brother) died from Fahrs disease at 70'],
        ['b392fd78b440', '987', 'ADULT_CHILD', 'Grandchild', '', '', 'UNSURE', 'SMA', 'NO', 'Dwarfism', '', '47', '2', '', '33', 'heart attack', 'NO', 'PREFER_NOT_ANSWER', 'WHITE', 'UNKNOWN', '', 'Pediatrician', 'NOT_SURE,MICROARRAY,WEXOME', '', '', '', '', '2018', 'UDN', 'PARENT,AUNT_UNCLE,OTHER', 'Grandmother', '', '', '', 'Grandmother', 'Blood work', 'NONE', '', 'NO', 'Undiagnosed Diseases Network', 'NO', 'UNSURE', '19', '', 'UNKNOWN', 'NO', 'UNSURE', '', '', '', '', '', '', '', 'YES', 'YES', '[{"SIBLING_SEX":"FEMALE","SIBLING_AGE":"21","SIBLING_RACE":"WHITE","SIBLING_ETHNICITY":"NOT_HISPANIC","SIBLING_SAME_CONDITION":"YES","SIBLING_CONDITION_AGE":null,"SIBLING_CAN_PARTICIPATE":"NO"}]', 'NO', '[{"CHILD_SEX":"MALE","CHILD_AGE":"12","CHILD_RACE":"WHITE","CHILD_ETHNICITY":"NOT_HISPANIC","CHILD_SAME_CONDITION":"NO","CHILD_CONDITION_AGE":null,"CHILD_CAN_PARTICIPATE":"UNSURE"}]', 'YES', '', '']],
            FILENAME, self.collaborator_user)

        self.assertListEqual(warnings, [])

        note_1 = """#### Clinical Information
* __Patient is my:__ Grandchild (male)
* __Current Age:__ Patient is deceased, age 33, due to heart attack, sample not available
* __Age of Onset:__ 21
* __Race/Ethnicity:__ White, Asian, Pacific; Not Hispanic
* __Case Description:__ I have a really debilitating probably genetic condition. Ive seen many specialists.
* __Clinical Diagnoses:__ Yes; SMAs
* __Genetic Diagnoses:__ Yes; Dwarfism
* __Website/Blog:__ Yes
* __Additional Information:__ patients uncle (dads brother) died from Fahrs disease at 70
#### Prior Testing
* __Referring Physician:__ Dr John Smith
* __Doctors Seen:__ Clinical geneticist, Neurologist, Cardiologist, Other: Pediatrician
* __Previous Testing:__ Yes;
* * Single gene testing
* * Gene panel testing
* * Whole exome sequencing. Year: 2018, Lab: UDNs lab, Relatives: Parent, Aunt or Uncle, Niece or Nephew, Other: Grandmother
* * Whole genome sequencing. Year: unspecified, Lab: unspecified, Relatives: None Specified
* * Other tests: Blood work
* __Biopsies Available:__ Muscle Biopsy, Skin Biopsy, Other Tissue Biopsy: Bones
* __Other Research Studies:__ Yes, Name of studies: Undiagnosed Diseases Network, Expecting results: No
#### Family Information
* __Mother:__ affected, onset age 19, available
* __Father:__ unaffected, unavailable, deceased, sample not available
* __Siblings:__ 
* * Sister, age 21, affected, unavailable
* * Sibling (unspecified sex), age 17, unspecified affected status, available
* __Children:__ None
* __Relatives:__ 
* * Male, age 44, affected, unspecified availability"""

        note_2 = """#### Clinical Information
* __Patient is my:__ Adult Child (unspecified sex) - unable to provide consent
* __Current Age:__ 47
* __Age of Onset:__ 2
* __Race/Ethnicity:__ White; Unknown
* __Case Description:__ 
* __Clinical Diagnoses:__ Unsure
* __Genetic Diagnoses:__ No
* __Website/Blog:__ No
* __Additional Information:__ None specified
#### Prior Testing
* __Referring Physician:__ None
* __Doctors Seen:__ 
* __Previous Testing:__ Not sure
* __Biopsies Available:__ None
* __Other Research Studies:__ No
#### Family Information
* __Mother:__ unknown affected status, unavailable, unknown deceased status
* __Father:__ unknown affected status, unavailable, unspecified deceased status
* __Siblings:__ None
* __Children:__ 
* * Son, age 12, unaffected, unspecified availability
* __Relatives:__ None"""

        self.assertListEqual(records, [
            {'familyId': 'RGP_123', 'individualId': 'RGP_123_1', 'sex': 'F', 'affected': 'N'},
            {'familyId': 'RGP_123', 'individualId': 'RGP_123_2', 'sex': 'M', 'affected': 'N'},
            {
                'familyId': 'RGP_123', 'individualId': 'RGP_123_3', 'sex': 'M', 'affected': 'A',
                'maternalId': 'RGP_123_1', 'paternalId': 'RGP_123_2', 'familyNotes': note_1,
                'maternalEthnicity': ['White', 'Asian', 'Not Hispanic'], 'paternalEthnicity': ['Black'],
                'birthYear': 1986, 'deathYear': 2019, 'onsetAge': 'A', 'affectedRelatives': True,
            },
            {'familyId': 'RGP_987', 'individualId': 'RGP_987_1', 'sex': 'F', 'affected': 'N'},
            {'familyId': 'RGP_987', 'individualId': 'RGP_987_2', 'sex': 'M', 'affected': 'N'},
            {
                'familyId': 'RGP_987', 'individualId': 'RGP_987_3', 'sex': 'U', 'affected': 'A',
                'maternalId': 'RGP_987_1', 'paternalId': 'RGP_987_2', 'familyNotes': note_2,
                'maternalEthnicity': None, 'paternalEthnicity': None, 'birthYear': 1973, 'deathYear': None,
                'onsetAge': 'C', 'affectedRelatives': False,
            },
        ])


class LocalPedigreeInfoUtilsTest(AuthenticationTestCase, PedigreeInfoUtilsTest):
    fixtures = ['users', '1kg_project']


class AnvilPedigreeInfoUtilsTest(AnvilAuthenticationTestCase, PedigreeInfoUtilsTest):
    fixtures = ['users', 'social_auth', '1kg_project']
