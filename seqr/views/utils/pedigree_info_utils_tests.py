from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.test import TestCase
import mock
from openpyxl import load_workbook
from io import BytesIO

from seqr.models import Project
from seqr.views.utils.pedigree_info_utils import parse_pedigree_table


FILENAME = 'test.csv'


class PedigreeInfoUtilsTest(TestCase):
    fixtures = ['users', '1kg_project']

    def test_parse_pedigree_table(self):
        records, errors, warnings = parse_pedigree_table(
            [['family_id', 'individual_id', 'sex', 'affected'],
             ['fam1', 'ind1', 'male']], FILENAME)
        self.assertListEqual(records, [])
        self.assertListEqual(
            errors, ['Error while parsing file: {}. Row 1 contains 3 columns: fam1, ind1, male, while header contains 4: family_id, individual_id, sex, affected'.format(FILENAME)])
        self.assertListEqual(warnings, [])
        records, errors, warnings = parse_pedigree_table(
            [['family_id', 'individual_id', 'sex', 'affected', 'father', 'mother'],
             ['', '', 'male', 'u', '.', 'ind2']], FILENAME)
        self.assertListEqual(records, [])
        self.assertIn(
            errors[0], ["Error while converting {} rows to json: Family Id not specified in row #1:\n{{'familyId': '', 'individualId': '', 'sex': 'male', 'affected': 'u', 'paternalId': '', 'maternalId': 'ind2'}}".format(FILENAME),
                        "Error while converting {} rows to json: Family Id not specified in row #1:\n{{u'affected': u'u', u'maternalId': u'ind2', u'individualId': u'', u'sex': u'male', u'familyId': u'', u'paternalId': u''}}".format(FILENAME)])
        self.assertListEqual(warnings, [])

        records, errors, warnings = parse_pedigree_table(
            [['family_id', 'individual_id', 'sex', 'affected', 'father', 'mother'],
             ['fam1', '', 'male', 'u', '.', 'ind2']], FILENAME)
        self.assertListEqual(records, [])
        self.assertIn(
            errors[0], ["Error while converting {} rows to json: Individual Id not specified in row #1:\n{{'familyId': 'fam1', 'individualId': '', 'sex': 'male', 'affected': 'u', 'paternalId': '', 'maternalId': 'ind2'}}".format(FILENAME),
                     "Error while converting {} rows to json: Individual Id not specified in row #1:\n{{u'affected': u'u', u'maternalId': u'ind2', u'individualId': u'', u'sex': u'male', u'familyId': u'fam1', u'paternalId': u''}}".format(FILENAME)])
        self.assertListEqual(warnings, [])

        records, errors, warnings = parse_pedigree_table(
            [['family_id', 'individual_id', 'sex', 'affected', 'father', 'mother'],
             ['fam1', 'ind1', 'boy', 'u', '.', 'ind2']], FILENAME)
        self.assertListEqual(records, [])
        self.assertListEqual(
            errors, ["Error while converting {} rows to json: Invalid value 'boy' for sex in row #1".format(FILENAME)])
        self.assertListEqual(warnings, [])

        records, errors, warnings = parse_pedigree_table(
            [['family_id', 'individual_id', 'sex', 'affected', 'father', 'mother'],
             ['fam1', 'ind1', 'male', 'no', '.', 'ind2']], FILENAME)
        self.assertListEqual(records, [])
        self.assertListEqual(
            errors, ["Error while converting {} rows to json: Invalid value 'no' for affected status in row #1".format(FILENAME)])

        records, errors, warnings = parse_pedigree_table(
            [['family_id', 'individual_id', 'sex', 'affected', 'father', 'mother', 'proband_relation'],
             ['fam1', 'ind1', 'male', 'aff.', 'ind3', 'ind2', 'mom']], FILENAME)
        self.assertListEqual(records, [])
        self.assertListEqual(errors, [
            'Error while converting {} rows to json: Invalid value "mom" for proband relationship in row #1'.format(
                FILENAME)])

        records, errors, warnings = parse_pedigree_table(
            [['family_id', 'individual_id', 'sex', 'affected', 'father', 'mother', 'proband_relation'],
             ['fam1', 'ind1', 'male', 'aff.', 'ind3', 'ind2', 'mother'],
             ['fam2', 'ind2', 'male', 'unknown', '.', '', '']],
            FILENAME)
        self.assertListEqual(records, [
            {'familyId': 'fam1', 'individualId': 'ind1', 'sex': 'M', 'affected': 'A', 'paternalId': 'ind3',
             'maternalId': 'ind2', 'probandRelationship': 'M'},
            {'familyId': 'fam2', 'individualId': 'ind2', 'sex': 'M', 'affected': 'U', 'paternalId': '',
             'maternalId': '', 'probandRelationship': ''},
        ])
        self.assertListEqual(errors, [
            'Invalid proband relationship "Mother" for ind1 with given gender Male',
            'ind2 is recorded as Male and also as the mother of ind1',
            'ind2 is recorded as the mother of ind1 but they have different family ids: fam2 and fam1',
        ])
        self.assertListEqual(warnings, ["ind3 is the father of ind1 but doesn't have a separate record in the table"])

        records, errors, warnings = parse_pedigree_table(
            [['A pedigree file'], ['# Some comments'],
             ['#family_id', '#individual_id', 'previous_individual_id', 'notes_for_import', 'other_data', 'sex', 'affected', 'father', 'mother', 'phenotype: coded', 'proband_relation'],
             ['fam1', 'ind1', 'ind1_old_id', 'some notes', 'some more notes', 'male', 'aff.', '.', 'ind2', 'HPO:12345', ''],
             ['fam1', 'ind2', '', ' ', '', 'female', 'u', '.', '', 'HPO:56789', 'mother']], FILENAME)
        self.assertListEqual(records, [
            {'familyId': 'fam1', 'individualId': 'ind1', 'sex': 'M', 'affected': 'A', 'paternalId': '',
             'maternalId': 'ind2', 'notes': 'some notes', 'codedPhenotype': 'HPO:12345', 'probandRelationship': '',
             'previousIndividualId': 'ind1_old_id'},
            {'familyId': 'fam1', 'individualId': 'ind2', 'sex': 'F', 'affected': 'N', 'paternalId': '',
             'maternalId': '', 'notes': '', 'codedPhenotype': 'HPO:56789', 'probandRelationship': 'M',
             'previousIndividualId': ''},
        ])
        self.assertListEqual(errors, [])
        self.assertListEqual(warnings, [])

    @mock.patch('seqr.views.utils.pedigree_info_utils.UPLOADED_PEDIGREE_FILE_RECIPIENTS', ['recipient@test.com'])
    @mock.patch('seqr.views.utils.pedigree_info_utils.EmailMultiAlternatives')
    def test_parse_sample_manifest(self, mock_email):
        header_1 = [
            'Do not modify - Broad use', '', '', 'Please fill in columns D - O', '', '', '', '', '', '', '', '', '',
            '', '']
        header_2 = [
            'Kit ID', 'Well', 'Sample ID', 'Family ID', 'Alias', 'Alias', 'Paternal Sample ID', 'Maternal Sample ID',
            'Gender', 'Affected Status', 'Volume', 'Concentration', 'Notes', 'Coded Phenotype', 'Data Use Restrictions']
        header_3 = [
            '', 'Position', '', '', 'Collaborator Participant ID', 'Collaborator Sample ID', '', '', '', '', 'ul',
            'ng/ul', '', '', 'indicate study/protocol number']

        records, errors, warnings = parse_pedigree_table([
            header_1,
            ['Kit ID', 'Well', 'Sample ID', 'Family ID', 'Alias', 'Maternal Sample ID',
             'Gender', 'Affected Status', 'Volume', 'Concentration', 'Notes', 'Coded Phenotype',
             'Data Use Restrictions'],
            header_3,
        ], FILENAME)
        self.assertListEqual(errors, [
            'Error while parsing file: {}. Expected vs. actual header columns: | Sample ID| Family ID| Alias|-Alias|-Paternal Sample ID| Maternal Sample ID| Gender| Affected Status'.format(
                FILENAME)])
        self.assertListEqual(warnings, [])
        self.assertListEqual(records, [])

        records, errors, warnings = parse_pedigree_table([
            header_1, header_2, ['', 'Position', '', '', 'Collaborator Sample ID', '', '', '', '', 'ul', 'ng/ul', '',
                                 '', 'indicate study/protocol number']], FILENAME)
        self.assertListEqual(errors, [
            'Error while parsing file: {}. Expected vs. actual header columns: |-Collaborator Participant ID| Collaborator Sample ID|+'.format(
                FILENAME)])
        self.assertListEqual(warnings, [])
        self.assertListEqual(records, [])

        original_data = [
            header_1, header_2, header_3,
            ['SK-3QVD', 'A02', 'SM-IRW6C', 'PED073', 'SCO_PED073B_GA0339', 'SCO_PED073B_GA0339_1', '', '', 'male',
             'unaffected', '20', '94.8', 'probably dad', '', '1234'],
            ['SK-3QVD', 'A03', 'SM-IRW69', 'PED073', 'SCO_PED073C_GA0340', 'SCO_PED073C_GA0340_1',
             'SCO_PED073B_GA0339_1', 'SCO_PED073A_GA0338_1', 'female', 'affected', '20', '98', '', 'Perinatal death', ''
             ]]

        records, errors, warnings = parse_pedigree_table(
            original_data, FILENAME, user=User.objects.get(id=10), project=Project.objects.get(id=1))
        self.assertListEqual(records, [
            {'affected': 'N', 'maternalId': '', 'notes': 'probably dad', 'individualId': 'SCO_PED073B_GA0339_1',
             'sex': 'M', 'familyId': 'PED073', 'paternalId': '', 'codedPhenotype': ''},
            {'affected': 'A', 'maternalId': 'SCO_PED073A_GA0338_1', 'notes': '', 'individualId': 'SCO_PED073C_GA0340_1',
             'sex': 'F', 'familyId': 'PED073', 'paternalId': 'SCO_PED073B_GA0339_1', 'codedPhenotype': 'Perinatal death'
             }])
        self.assertListEqual(
            warnings,
            ["SCO_PED073A_GA0338_1 is the mother of SCO_PED073C_GA0340_1 but doesn't have a separate record in the table"])
        self.assertListEqual(errors, [])

        mock_email.assert_called_with(
            subject='SK-3QVD Merged Sample Pedigree File',
            body=mock.ANY,
            to=['recipient@test.com'],
            attachments=[
                ('SK-3QVD.xlsx', mock.ANY,
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ('test.xlsx', mock.ANY,
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ])
        self.assertEqual(
            mock_email.call_args.kwargs['body'],
            """User test_user@test.com just uploaded pedigree info to 1kg project n\xe5me with uni\xe7\xf8de.This email has 2 attached files:
    
    SK-3QVD.xlsx is the sample manifest file in a format that can be sent to GP.
    
    test.csv is the original merged pedigree-sample-manifest file that the user uploaded.
    """)
        mock_email.return_value.attach_alternative.assert_called_with(
            """User test_user@test.com just uploaded pedigree info to 1kg project n\xe5me with uni\xe7\xf8de.<br />This email has 2 attached files:<br />
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

    def test_parse_datstat_pedigree_table(self):
        records, errors, warnings = parse_pedigree_table(
        [['DATSTAT_ALTPID', 'FAMILY_ID', 'DDP_CREATED', 'DDP_LASTUPDATED', 'RELATIONSHIP', 'RELATIONSHIP_SPECIFY', 'PATIENT_WEBSITE', 'DESCRIPTION', 'CLINICAL_DIAGNOSES', 'CLINICAL_DIAGNOSES_SPECIFY', 'GENETIC_DIAGNOSES', 'GENETIC_DIAGNOSES_SPECIFY', 'FIND_OUT.DOCTOR', 'FIND_OUT_DOCTOR_DETAILS', 'PATIENT_AGE', 'CONDITION_AGE', 'PATIENT_DECEASED', 'DECEASED_AGE', 'DECEASED_CAUSE', 'DECEASED_STORED_SAMPLE', 'PATIENT_SEX', 'RACE_LIST', 'PTETHNICITY', 'DOCTOR_TYPES_LIST', 'DOCTOR_TYPES_SPECIFY', 'TESTS.NONE', 'TESTS.NOT_SURE', 'TESTS.KARYOTYPE', 'TESTS.SINGLE_GENE_TESTING', 'TESTS.GENE_PANEL_TESTING', 'TESTS.MITOCHON_GENOME_SEQUENCING', 'TESTS.MICROARRAY', 'TESTS_MICROARRAY_YEAR', 'TESTS_MICROARRAY_LAB', 'TESTS_MICROARRAY_RELATIVE_LIST', 'TESTS_MICROARRAY_RELATIVE_SPEC', 'TESTS.WEXOME_SEQUENCING', 'TESTS_WEXOME_SEQUENCING_YEAR', 'TESTS_WEXOME_SEQUENCING_LAB', 'TESTS_WEXOME_SEQUENCING_REL_LI', 'TESTS_WEXOME_SEQUENCING_REL_SP', 'TESTS.WGENOME_SEQUENCING', 'TESTS_WGENOME_SEQUENCING_YEAR', 'TESTS_WGENOME_SEQUENCING_LAB', 'TESTS_WGENOME_SEQUENCING_REL_L', 'TESTS_WGENOME_SEQUENCING_REL_S', 'TESTS.OTHER', 'TEST_OTHER_SPECIFY', 'BIOPSY.NONE', 'BIOPSY', 'BIOPSY.OTHER', 'BIOPSY_OTHER_SPECIFY', 'OTHER_GENETIC_STUDIES', 'OTHER_GENETIC_STUDIES_SPECIFY', 'EXPECTING_GENETIC_RESULTS', 'SAME_CONDITION_MOM', 'CONDITION_AGE_MOM', 'ABLE_TO_PARTICIPATE_MOM', 'DECEASED_MOM', 'STORED_DNA_MOM', 'SAME_CONDITION_DAD', 'CONDITION_AGE_DAD', 'ABLE_TO_PARTICIPATE_DAD', 'DECEASED_DAD', 'STORED_DNA_DAD', 'NO_SIBLINGS', 'SIBLING_LIST', 'NO_CHILDREN', 'CHILD_LIST', 'NO_RELATIVE_AFFECTED', 'RELATIVE_LIST', 'FAMILY_INFO'],
        ['1518231365', '123', '2019-07-31T03:54:21UTC', '2019-08-01T14:12:40UTC', '6', 'Grandchild', 'wwww.myblog.com', 'I have a really debilitating probably genetic condition. I\xe2ve seen many specialists.', '1', 'SMA\xe2s', '1', 'Dwarfism\xe2', '1', 'Dr John Smith', '34', '21', '1', '33', 'heart attack', '2', '1', '["White","Asian","Pacific"]', '2', '["ClinGen","Neurologist","Cardiologist","Other"]', 'Pediatrician', '0', '0', '0', '1', '1', '0', '0', '', '', '', '', '1', '2018', 'UDN\xe2s lab', '["Parent","AuntUncle","NieceNephew","Other"]', 'Grandmother', '1', '', '', '', 'Grandmother', '1', 'Blood work', '0', 'MUSCLE,SKIN,OTHER: Muscle Biopsy, Skin Biopsy, Other Tissue Biopsy', '1', 'Bone\xe2s', '1', 'Undiagnosed Diseases Network', '2', '1', '19', '1', '', '', '2', '', '', '1', '2', '0', '[{"sex":"Female","age":"21","races":["White"],"ethnicity":"NonHispanic","sameCondition":"Yes","ageOnsetCondition":null,"ableToParticipate":"No","siblingId":"d18b9f4b-0995-45e9-9b00-e710d0004a3f"},{"sex":"","age":"17","races":["White"],"ethnicity":"NonHispanic","sameCondition":"","ageOnsetCondition":null,"ableToParticipate":"Yes","siblingId":"3ddc9015-3c2c-484c-b1de-502ba9ffc1e4"}]', '1', '', '0', '[{"sex":"Male","age":"44","races":["White"],"ethnicity":"NonHispanic","sameCondition":"No","ageOnsetCondition":null,"ableToParticipate":null,"siblingId":"bb87c69f-6c52-48b4-8854-e639d998abe7"}]', 'patient\xe2s uncle (dads brother) died from Fahrs disease at 70'],
        ['b392fd78b440', '987', '2019-08-06T14:30:44UTC', '2019-08-06T15:18:48UTC', '8', 'Grandchild', '', '', '3', 'SMA', '2', 'Dwarfism', '0', 'Dr John Smith', '47', '2', '0', '33', 'heart attack', '2', '3', '["White"]', '3', '[]', 'Pediatrician', '0', '1', '0', '1', '1', '0', '0', '', '', '', '', '1', '2018', 'UDN', '["Parent","AuntUncle","NieceNephew","Other"]', 'Grandmother', '1', '', '', '', 'Grandmother', '1', 'Blood work', '1', 'NONE: This individual hasn\'t had a biopsy', '1', 'Bone', '0', 'Undiagnosed Diseases Network', '2', '3', '19', '2', '3', '', '', '', '', '', '1', '1', '[{"sex":"Female","age":"21","races":["White"],"ethnicity":"NonHispanic","sameCondition":"Yes","ageOnsetCondition":null,"ableToParticipate":"No","siblingId":"d18b9f4b-0995-45e9-9b00-e710d0004a3f"},{"sex":"","age":"17","races":["White"],"ethnicity":"NonHispanic","sameCondition":"","ageOnsetCondition":null,"ableToParticipate":"Yes","siblingId":"3ddc9015-3c2c-484c-b1de-502ba9ffc1e4"}]', '0: No', '[{"sex":"Male","age":"12","races":["White"],"ethnicity":"NonHispanic","sameCondition":"No","ageOnsetCondition":null,"ableToParticipate":"Unsure","siblingId":"bb87c69f-6c52-48b4-8854-e639d998abe7"}]', '1', '', '']], FILENAME)

        note_1 = """#### Clinical Information
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Patient is my:__ Grandchild (male)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Current Age:__ Patient is deceased, age 33, due to heart attack, sample not available
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Age of Onset:__ 21
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Race/Ethnicity:__ White, Asian, Pacific; Not Hispanic
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Case Description:__ I have a really debilitating probably genetic condition. I\xe2ve seen many specialists.
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Clinical Diagnoses:__ Yes; SMA\xe2s
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Genetic Diagnoses:__ Yes; Dwarfism\xe2
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Website/Blog:__ Yes
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Additional Information:__ patient\xe2s uncle (dads brother) died from Fahrs disease at 70
#### Prior Testing
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Referring Physician:__ Dr John Smith
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Doctors Seen:__ Clinical geneticist, Neurologist, Cardiologist, Other: Pediatrician
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Previous Testing:__ Yes;
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Single gene testing
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Gene panel testing
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Whole exome sequencing. Year: 2018, Lab: UDN\xe2s lab, Relatives: Parent, Aunt or Uncle, Niece or Nephew, Other: Grandmother
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Whole genome sequencing. Year: unspecified, Lab: unspecified, Relatives: not specified
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Other tests: Blood work
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Biopsies Available:__ Muscle Biopsy, Skin Biopsy, Other Tissue Biopsy: Bone\xe2s
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
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Clinical Diagnoses:__ Unknown/Unsure
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
        self.maxDiff = None
        self.assertListEqual(records, [
            {'familyId': 'RGP_123', 'individualId': 'RGP_123_1', 'sex': 'F', 'affected': 'N'},
            {'familyId': 'RGP_123', 'individualId': 'RGP_123_2', 'sex': 'M', 'affected': 'N'},
            {'familyId': 'RGP_123', 'individualId': 'RGP_123_3', 'sex': 'M', 'affected': 'A', 'maternalId': 'RGP_123_1', 'paternalId': 'RGP_123_2', 'familyNotes': note_1},
            {'familyId': 'RGP_987', 'individualId': 'RGP_987_1', 'sex': 'F', 'affected': 'N'},
            {'familyId': 'RGP_987', 'individualId': 'RGP_987_2', 'sex': 'M', 'affected': 'N'},
            {'familyId': 'RGP_987', 'individualId': 'RGP_987_3', 'sex': 'U', 'affected': 'A', 'maternalId': 'RGP_987_1', 'paternalId': 'RGP_987_2', 'familyNotes': note_2},
        ])
        self.assertListEqual(errors, [])
        self.assertListEqual(warnings, [])
