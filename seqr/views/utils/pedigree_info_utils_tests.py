import datetime
from django.contrib.auth.models import User
from django.test import TestCase
import mock
from openpyxl import load_workbook
from io import BytesIO

from seqr.models import Project
from seqr.views.utils.pedigree_info_utils import parse_pedigree_table, ErrorsWarningsException

FILENAME = 'test.csv'


class PedigreeInfoUtilsTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_parse_pedigree_table(self):
        user = User.objects.get(id=10)
        with self.assertRaises(ErrorsWarningsException) as ec:
            parse_pedigree_table(
                [['family_id', 'individual_id', 'sex', 'affected'],
                 ['fam1', 'ind1', 'male']], FILENAME, user)
        self.assertListEqual(
            ec.exception.errors, ['Error while parsing file: {}. Row 1 contains 3 columns: fam1, ind1, male, while header contains 4: family_id, individual_id, sex, affected'.format(FILENAME)])
        self.assertListEqual(ec.exception.warnings, [])

        with self.assertRaises(ErrorsWarningsException) as ec:
            parse_pedigree_table(
                [['family_id', 'individual_id', 'sex', 'affected', 'father', 'mother'],
                ['', '', 'male', 'u', '.', 'ind2']], FILENAME, user)
        self.assertEqual(len(ec.exception.errors), 1)
        self.assertEqual(ec.exception.errors[0].split('\n')[0],
                         "Error while converting {} rows to json: Family Id not specified in row #1:".format(FILENAME))
        self.assertListEqual(ec.exception.warnings, [])

        with self.assertRaises(ErrorsWarningsException) as ec:
            parse_pedigree_table(
                [['family_id', 'individual_id', 'sex', 'affected', 'father', 'mother'],
                 ['fam1', '', 'male', 'u', '.', 'ind2']], FILENAME, user)
        self.assertEqual(len(ec.exception.errors), 1)
        self.assertEqual(ec.exception.errors[0].split('\n')[0],
                         "Error while converting {} rows to json: Individual Id not specified in row #1:".format(FILENAME))
        self.assertListEqual(ec.exception.warnings, [])

        with self.assertRaises(ErrorsWarningsException) as ec:
            parse_pedigree_table(
                [['family_id', 'individual_id', 'sex', 'affected', 'father', 'mother'],
                 ['fam1', 'ind1', 'boy', 'u', '.', 'ind2']], FILENAME, user)
        self.assertListEqual(
            ec.exception.errors, ["Error while converting {} rows to json: Invalid value 'boy' for sex in row #1".format(FILENAME)])
        self.assertListEqual(ec.exception.warnings, [])

        with self.assertRaises(ErrorsWarningsException) as ec:
            parse_pedigree_table(
                [['family_id', 'individual_id', 'sex', 'affected', 'father', 'mother'],
                 ['fam1', 'ind1', 'male', 'no', '.', 'ind2']], FILENAME, user)
        self.assertListEqual(
            ec.exception.errors, ["Error while converting {} rows to json: Invalid value 'no' for affected status in row #1".format(FILENAME)])

        with self.assertRaises(ErrorsWarningsException) as ec:
            parse_pedigree_table(
                [['family_id', 'individual_id', 'sex', 'affected', 'father', 'mother', 'proband_relation'],
                 ['fam1', 'ind1', 'male', 'aff.', 'ind3', 'ind2', 'mom']], FILENAME, user)
        self.assertListEqual(ec.exception.errors, [
            'Error while converting {} rows to json: Invalid value "mom" for proband relationship in row #1'.format(
                FILENAME)])

        with self.assertRaises(ErrorsWarningsException) as ec:
            parse_pedigree_table(
                [['family_id', 'individual_id', 'sex', 'affected', 'father', 'mother', 'proband_relation'],
                 ['fam1', 'ind1', 'male', 'aff.', 'ind3', 'ind2', 'mother'],
                 ['fam2', 'ind2', 'male', 'unknown', 'ind2', '.', '']],
                FILENAME, user)
        self.assertListEqual(ec.exception.errors, [
            'Invalid proband relationship "Mother" for ind1 with given gender Male',
            'ind2 is recorded as Male and also as the mother of ind1',
            'ind2 is recorded as the mother of ind1 but they have different family ids: fam2 and fam1',
            'ind2 is recorded as their own father',
        ])
        self.assertListEqual(ec.exception.warnings, ["ind3 is the father of ind1 but doesn't have a separate record in the table"])

        no_error_data = [['A pedigree file'], ['# Some comments'],
             ['#family_id', '#individual_id', 'previous_individual_id', 'notes_for_import', 'other_data', 'sex', 'affected', 'father', 'mother', 'phenotype: coded', 'proband_relation'],
             ['fam1', 'ind1', 'ind1_old_id', 'some notes', 'some more notes', 'male', 'aff.', '.', 'ind2', 'HPO:12345', ''],
             ['fam1', 'ind2', '', ' ', '', 'female', 'u', '.', 'ind3', 'HPO:56789', 'mother']]
        no_error_warnings = ["ind3 is the mother of ind2 but doesn't have a separate record in the table"]
        records, warnings = parse_pedigree_table(no_error_data, FILENAME, user)
        self.assertListEqual(records, [
            {'familyId': 'fam1', 'individualId': 'ind1', 'sex': 'M', 'affected': 'A', 'paternalId': '',
             'maternalId': 'ind2', 'notes': 'some notes', 'codedPhenotype': 'HPO:12345', 'probandRelationship': '',
             'previousIndividualId': 'ind1_old_id'},
            {'familyId': 'fam1', 'individualId': 'ind2', 'sex': 'F', 'affected': 'N', 'paternalId': '',
             'maternalId': 'ind3', 'notes': '', 'codedPhenotype': 'HPO:56789', 'probandRelationship': 'M',
             'previousIndividualId': ''},
        ])
        self.assertListEqual(warnings, no_error_warnings)

        with self.assertRaises(ErrorsWarningsException) as ec:
            parse_pedigree_table(no_error_data, FILENAME, user, fail_on_warnings=True)
        self.assertListEqual(ec.exception.errors, no_error_warnings)


    @mock.patch('seqr.views.utils.pedigree_info_utils.PM_USER_GROUP', 'project-managers')
    @mock.patch('seqr.views.utils.permissions_utils.PM_USER_GROUP')
    @mock.patch('seqr.utils.communication_utils.EmailMultiAlternatives')
    def test_parse_sample_manifest(self, mock_email, mock_pm_group):
        header_1 = [
            'Do not modify - Broad use', '', '', 'Please fill in columns D - O', '', '', '', '', '', '', '', '', '',
            '', '']
        header_2 = [
            'Kit ID', 'Well', 'Sample ID', 'Family ID', 'Alias', 'Alias', 'Paternal Sample ID', 'Maternal Sample ID',
            'Gender', 'Affected Status', 'Volume', 'Concentration', 'Notes', 'Coded Phenotype', 'Data Use Restrictions']
        header_3 = [
            '', 'Position', '', '', 'Collaborator Participant ID', 'Collaborator Sample ID', '', '', '', '', 'ul',
            'ng/ul', '', '', 'indicate study/protocol number']

        with self.assertRaises(ErrorsWarningsException) as ec:
            parse_pedigree_table([header_1], FILENAME, user = User.objects.get(id=10))
        self.assertListEqual(ec.exception.errors, ['Error while parsing file: {}. Unsupported file format'.format(FILENAME)])
        self.assertListEqual(ec.exception.warnings, [])

        user = User.objects.get(username='test_pm_user')
        with self.assertRaises(ErrorsWarningsException) as ec:
            parse_pedigree_table([
                header_1,
                ['Kit ID', 'Well', 'Sample ID', 'Family ID', 'Alias', 'Maternal Sample ID',
                 'Gender', 'Affected Status', 'Volume', 'Concentration', 'Notes', 'Coded Phenotype',
                 'Data Use Restrictions'],
                header_3,
            ], FILENAME, user)
        self.assertListEqual(ec.exception.errors, ['Error while parsing file: {}. Unsupported file format'.format(FILENAME)])
        self.assertListEqual(ec.exception.warnings, [])

        mock_pm_group.__bool__.return_value = True
        mock_pm_group.resolve_expression.return_value = 'project-managers'
        with self.assertRaises(ErrorsWarningsException) as ec:
            parse_pedigree_table([
                header_1,
                ['Kit ID', 'Well', 'Sample ID', 'Family ID', 'Alias', 'Maternal Sample ID',
                 'Gender', 'Affected Status', 'Volume', 'Concentration', 'Notes', 'Coded Phenotype',
                 'Data Use Restrictions'],
                header_3,
            ], FILENAME, user)
        self.assertListEqual(ec.exception.errors, [
            'Error while parsing file: {}. Expected vs. actual header columns: | Sample ID| Family ID| Alias|-Alias|-Paternal Sample ID| Maternal Sample ID| Gender| Affected Status'.format(
                FILENAME)])
        self.assertListEqual(ec.exception.warnings, [])

        with self.assertRaises(ErrorsWarningsException) as ec:
            parse_pedigree_table([
                header_1, header_2, ['', 'Position', '', '', 'Collaborator Sample ID', '', '', '', '', 'ul', 'ng/ul', '',
                                     '', 'indicate study/protocol number']], FILENAME, user)
        self.assertListEqual(ec.exception.errors, [
            'Error while parsing file: {}. Expected vs. actual header columns: |-Collaborator Participant ID| Collaborator Sample ID|+'.format(
                FILENAME)])
        self.assertListEqual(ec.exception.warnings, [])

        original_data = [
            header_1, header_2, header_3,
            ['SK-3QVD', 'A02', 'SM-IRW6C', 'PED073', 'SCO_PED073B_GA0339', 'SCO_PED073B_GA0339_1', '', '', 'male',
             'unaffected', '20', '94.8', 'probably dad', '', '1234'],
            ['SK-3QVD', 'A03', 'SM-IRW69', 'PED073', 'SCO_PED073C_GA0340', 'SCO_PED073C_GA0340_1',
             'SCO_PED073B_GA0339_1', 'SCO_PED073A_GA0338_1', 'female', 'affected', '20', '98', '', 'Perinatal death', ''
             ]]

        records, warnings = parse_pedigree_table(
            original_data, FILENAME, user, project=Project.objects.get(id=1))
        self.assertListEqual(records, [
            {'affected': 'N', 'maternalId': '', 'notes': 'probably dad', 'individualId': 'SCO_PED073B_GA0339_1',
             'sex': 'M', 'familyId': 'PED073', 'paternalId': '', 'codedPhenotype': ''},
            {'affected': 'A', 'maternalId': 'SCO_PED073A_GA0338_1', 'notes': '', 'individualId': 'SCO_PED073C_GA0340_1',
             'sex': 'F', 'familyId': 'PED073', 'paternalId': 'SCO_PED073B_GA0339_1', 'codedPhenotype': 'Perinatal death'
             }])
        self.assertListEqual(
            warnings,
            ["SCO_PED073A_GA0338_1 is the mother of SCO_PED073C_GA0340_1 but doesn't have a separate record in the table"])

        mock_email.assert_called_with(
            subject='SK-3QVD Merged Sample Pedigree File',
            body=mock.ANY,
            to=['test_pm_user@test.com'],
            attachments=[
                ('SK-3QVD.xlsx', mock.ANY,
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ('test.xlsx', mock.ANY,
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ])
        self.assertEqual(
            mock_email.call_args.kwargs['body'],
            '\n'.join([
                'User test_pm_user@test.com just uploaded pedigree info to 1kg project n\xe5me with uni\xe7\xf8de.This email has 2 attached files:',
                '    ', '    SK-3QVD.xlsx is the sample manifest file in a format that can be sent to GP.', '    ',
                '    test.csv is the original merged pedigree-sample-manifest file that the user uploaded.', '    ',
            ]))
        mock_email.return_value.attach_alternative.assert_called_with(
            """User test_pm_user@test.com just uploaded pedigree info to 1kg project n\xe5me with uni\xe7\xf8de.<br />This email has 2 attached files:<br />
    <br />
    <b>SK-3QVD.xlsx</b> is the sample manifest file in a format that can be sent to GP.<br />
    <br />
    <b>test.csv</b> is the original merged pedigree-sample-manifest file that the user uploaded.<br />
    """, 'text/html')
        mock_email.return_value.send.assert_called()

        # Test sent sample manifest is correct
        sample_wb = load_workbook(BytesIO(mock_email.call_args.kwargs['attachments'][0][1]))
        sample_ws = sample_wb.active
        sample_ws.title = 'Sample Info'
        self.assertListEqual(
            [[cell.value or '' for cell in row] for row in sample_ws],
            [['Well', 'Sample ID', 'Alias', 'Alias', 'Gender', 'Volume', 'Concentration'],
             ['Position', '', 'Collaborator Participant ID', 'Collaborator Sample ID', '', 'ul', 'ng/ul'],
             ['A02', 'SM-IRW6C', 'SCO_PED073B_GA0339', 'SCO_PED073B_GA0339_1', 'male', '20', '94.8'],
             ['A03', 'SM-IRW69', 'SCO_PED073C_GA0340', 'SCO_PED073C_GA0340_1', 'female', '20', '98']])

        # Test original file copy is correct
        original_wb = load_workbook(BytesIO(mock_email.call_args.kwargs['attachments'][1][1]))
        original_ws = original_wb.active
        self.assertListEqual([[cell.value or '' for cell in row] for row in original_ws], original_data)

    @mock.patch('seqr.views.utils.pedigree_info_utils.date')
    def test_parse_datstat_pedigree_table(self, mock_date):
        mock_date.today.return_value = datetime.date(2020, 1, 1)
        user = User.objects.get(id=10)

        records, warnings = parse_pedigree_table(
        [['participant_guid', 'familyId', 'RELATIONSHIP', 'RELATIONSHIP_OTHER_DETAILS', 'WEBSITE', 'DESCRIPTION', 'CLINICAL_DIAGNOSES', 'CLINICAL_DIAGNOSES_DETAILS', 'GENETIC_DIAGNOSES', 'GENETIC_DIAGNOSES_DETAILS', 'FIND_OUT_DOCTOR_DETAILS', 'PATIENT_AGE', 'CONDITION_AGE', 'PATIENT_DECEASED', 'DECEASED_AGE', 'DECEASED_CAUSE', 'DECEASED_DNA', 'PATIENT_SEX', 'RACE', 'ETHNICITY', 'DOCTOR_TYPES', 'DOCTOR_TYPES_OTHER_DETAILS', 'TESTS', 'TESTS_MICROARRAY_YEAR', 'TESTS_MICROARRAY_LAB', 'TESTS_MICROARRAY_FAMILY', 'TESTS_MICROARRAY_FAMILY_OTHER_DETAILS',  'TESTS_WEXOME_YEAR', 'TESTS_WEXOME_LAB', 'TESTS_WEXOME_FAMILY', 'TESTS_WEXOME_FAMILY_OTHER_DETAILS', 'TESTS_WGENOME_YEAR', 'TESTS_WGENOME_LAB', 'TESTS_WGENOME_FAMILY', 'TESTS_WGENOME_FAMILY_OTHER_DETAILS', 'TESTS_OTHER_DETAILS', 'BIOPSY', 'BIOPSY_OTHER_DETAILS', 'OTHER_STUDIES', 'OTHER_STUDIES_DESCRIBE', 'EXPECT_RESULTS', 'MOTHER_SAME_CONDITION', 'MOTHER_CONDITION_AGE', 'MOTHER_RACE', 'MOTHER_ETHNICITY', 'MOTHER_CAN_PARTICIPATE', 'MOTHER_DECEASED', 'MOTHER_DECEASED_DNA', 'FATHER_SAME_CONDITION', 'FATHER_CONDITION_AGE', 'FATHER_RACE', 'FATHER_ETHNICITY', 'FATHER_CAN_PARTICIPATE', 'FATHER_DECEASED', 'FATHER_DECEASED_DNA', 'NO_SIBLINGS', 'SIBLING', 'NO_CHILDREN', 'CHILD', 'NO_RELATIVE_AFFECTED', 'RELATIVE', 'FAMILY_INFO'],
        ['1518231365', '123', 'OTHER', 'Grandchild', 'wwww.myblog.com', 'I have a really debilitating probably genetic condition. I\xe2ve seen many specialists.', 'YES', 'SMA\xe2s', 'YES', 'Dwarfism\xe2', 'Dr John Smith', '34', '21', 'YES', '33', 'heart attack', 'NO', 'MALE', 'WHITE,ASIAN,PACIFIC', 'NOT_HISPANIC', 'CLIN_GEN,NEURO,CARDIO,OTHER', 'Pediatrician', 'SINGLE_GENE,GENE_PANEL,WEXOME,WGENOME,OTHER', '', '', '', '', '2018', 'UDN\xe2s lab', 'PARENT,AUNT_UNCLE,NIECE_NEPHEW,OTHER', 'Grandmother',  '', '', '', 'Grandmother', 'Blood work', 'MUSCLE,SKIN,OTHER', 'Bone\xe2s', 'YES', 'Undiagnosed Diseases Network', 'NO', 'YES', '19', 'WHITE,ASIAN', 'NOT_HISPANIC', 'YES', '', '', 'NO', '', '', 'BLACK', 'PREFER_NOT_ANSWER', 'YES', 'NO', '', '[{"SIBLING_SEX":"FEMALE","SIBLING_AGE":"21","SIBLING_RACE":"WHITE","SIBLING_ETHNICITY":"NOT_HISPANIC","SIBLING_SAME_CONDITION":"YES","SIBLING_CONDITION_AGE":null,"SIBLING_CAN_PARTICIPATE":"NO"},{"SIBLING_SEX":"","SIBLING_AGE":"17","SIBLING_RACE": "WHITE","SIBLING_ETHNICITY":"NOT_HISPANIC","SIBLING_SAME_CONDITION":"","SIBLING_CONDITION_AGE":"","SIBLING_CAN_PARTICIPATE":"YES"}]', 'YES', '', 'NO', '[{"RELATIVE_SEX":"MALE","RELATIVE_AGE":"44","RELATIVE_RACE": "WHITE", "RELATIVE_ETHNICITY":"NOT_HISPANIC","RELATIVE_CONDITION_AGE":null,"RELATIVE_CAN_PARTICIPATE":null}]', 'patient\xe2s uncle (dads brother) died from Fahrs disease at 70'],
        ['b392fd78b440', '987', 'ADULT_CHILD', 'Grandchild', '', '', 'UNSURE', 'SMA', 'NO', 'Dwarfism', '', '47', '2', '', '33', 'heart attack', 'NO', 'PREFER_NOT_ANSWER', 'WHITE', 'UNKNOWN', '', 'Pediatrician', 'NOT_SURE,MICROARRAY,WEXOME', '', '', '', '', '2018', 'UDN', 'PARENT,AUNT_UNCLE,OTHER', 'Grandmother', '', '', '', 'Grandmother', 'Blood work', 'NONE', '', 'NO', 'Undiagnosed Diseases Network', 'NO', 'UNSURE', '19', '', 'UNKNOWN', 'NO', 'UNSURE', '', '', '', '', '', '', '', 'YES', 'YES', '[{"SIBLING_SEX":"FEMALE","SIBLING_AGE":"21","SIBLING_RACE":"WHITE","SIBLING_ETHNICITY":"NOT_HISPANIC","SIBLING_SAME_CONDITION":"YES","SIBLING_CONDITION_AGE":null,"SIBLING_CAN_PARTICIPATE":"NO"}]', 'NO', '[{"CHILD_SEX":"MALE","CHILD_AGE":"12","CHILD_RACE":"WHITE","CHILD_ETHNICITY":"NOT_HISPANIC","CHILD_SAME_CONDITION":"NO","CHILD_CONDITION_AGE":null,"CHILD_CAN_PARTICIPATE":"UNSURE"}]', 'YES', '', '']],
            FILENAME, user)

        self.assertListEqual(warnings, [])

        note_1 = """#### Clinical Information
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Patient is my:__ Grandchild (male)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Current Age:__ Patient is deceased, age 33, due to heart attack, sample not available
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Age of Onset:__ 21
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Race/Ethnicity:__ White, Asian, Pacific; Not Hispanic
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Case Description:__ I have a really debilitating probably genetic condition. Ive seen many specialists.
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Clinical Diagnoses:__ Yes; SMAs
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Genetic Diagnoses:__ Yes; Dwarfism
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Website/Blog:__ Yes
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Additional Information:__ patients uncle (dads brother) died from Fahrs disease at 70
#### Prior Testing
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Referring Physician:__ Dr John Smith
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Doctors Seen:__ Clinical geneticist, Neurologist, Cardiologist, Other: Pediatrician
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Previous Testing:__ Yes;
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Single gene testing
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Gene panel testing
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Whole exome sequencing. Year: 2018, Lab: UDNs lab, Relatives: Parent, Aunt or Uncle, Niece or Nephew, Other: Grandmother
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Whole genome sequencing. Year: unspecified, Lab: unspecified, Relatives: None Specified
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Other tests: Blood work
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Biopsies Available:__ Muscle Biopsy, Skin Biopsy, Other Tissue Biopsy: Bones
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Other Research Studies:__ Yes, Name of studies: Undiagnosed Diseases Network, Expecting results: No
#### Family Information
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Mother:__ affected, onset age 19, available
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Father:__ unaffected, unavailable, deceased, sample not available
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Siblings:__ 
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Sister, age 21, affected, unavailable
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Sibling (unspecified sex), age 17, unspecified affected status, available
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Children:__ None
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Relatives:__ 
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Male, age 44, affected, unspecified availability"""

        note_2 = """#### Clinical Information
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Patient is my:__ Adult Child (unspecified sex) - unable to provide consent
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Current Age:__ 47
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Age of Onset:__ 2
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Race/Ethnicity:__ White; Unknown
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Case Description:__ 
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Clinical Diagnoses:__ Unsure
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Genetic Diagnoses:__ No
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Website/Blog:__ No
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Additional Information:__ None specified
#### Prior Testing
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Referring Physician:__ None
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Doctors Seen:__ 
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Previous Testing:__ Not sure
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Biopsies Available:__ None
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Other Research Studies:__ No
#### Family Information
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Mother:__ unknown affected status, unavailable, unknown deceased status
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Father:__ unknown affected status, unavailable, unspecified deceased status
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Siblings:__ None
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Children:__ 
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Son, age 12, unaffected, unspecified availability
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Relatives:__ None"""

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
