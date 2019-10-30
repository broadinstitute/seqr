from django.test import TestCase

from seqr.views.utils.pedigree_info_utils import parse_pedigree_table


FILENAME = 'test.csv'


class JSONUtilsTest(TestCase):

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
        self.assertListEqual(
            errors, ["Error while converting {} rows to json: Family Id not specified in row #1:\n{{'affected': 'u', 'maternalId': 'ind2', 'individualId': '', 'sex': 'male', 'familyId': '', 'paternalId': ''}}".format(FILENAME)])
        self.assertListEqual(warnings, [])

        records, errors, warnings = parse_pedigree_table(
            [['family_id', 'individual_id', 'sex', 'affected', 'father', 'mother'],
             ['fam1', '', 'male', 'u', '.', 'ind2']], FILENAME)
        self.assertListEqual(records, [])
        self.assertListEqual(
            errors, ["Error while converting {} rows to json: Individual Id not specified in row #1:\n{{'affected': 'u', 'maternalId': 'ind2', 'individualId': '', 'sex': 'male', 'familyId': 'fam1', 'paternalId': ''}}".format(FILENAME)])
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
            [['family_id', 'individual_id', 'sex', 'affected', 'father', 'mother'],
             ['fam1', 'ind1', 'male', 'aff.', 'ind3', 'ind2'], ['fam2', 'ind2', 'male', 'u', '.', '']], FILENAME)
        self.assertListEqual(records, [
            {'familyId': 'fam1', 'individualId': 'ind1', 'sex': 'M', 'affected': 'A', 'paternalId': 'ind3', 'maternalId': 'ind2'},
            {'familyId': 'fam2', 'individualId': 'ind2', 'sex': 'M', 'affected': 'N', 'paternalId': '', 'maternalId': ''},
        ])
        self.assertListEqual(errors, [
            'ind2 is recorded as Male and also as the mother of ind1',
            'ind2 is recorded as the mother of ind1 but they have different family ids: fam2 and fam1',
        ])
        self.assertListEqual(warnings, ["ind3 is the father of ind1 but doesn't have a separate record in the table"])

        records, errors, warnings = parse_pedigree_table(
            [['family_id', 'individual_id', 'notes_for_import', 'other_data', 'sex', 'affected', 'father', 'mother', 'phenotype: coded'],
             ['fam1', 'ind1', 'some notes', 'some more notes', 'male', 'aff.', '.', 'ind2', 'HPO:12345'],
             ['fam1', 'ind2', ' ', '', 'female', 'u', '.', '', 'HPO:56789']], FILENAME)
        self.assertListEqual(records, [
            {'familyId': 'fam1', 'individualId': 'ind1', 'sex': 'M', 'affected': 'A', 'paternalId': '', 'maternalId': 'ind2', 'notes': 'some notes', 'codedPhenotype': 'HPO:12345'},
            {'familyId': 'fam1', 'individualId': 'ind2', 'sex': 'F', 'affected': 'N', 'paternalId': '', 'maternalId': '', 'notes': '', 'codedPhenotype': 'HPO:56789'},
        ])
        self.assertListEqual(errors, [])
        self.assertListEqual(warnings, [])

    # TODO test sample manifest upload

    def test_parse_datstat_pedigree_table(self):
        records, errors, warnings = parse_pedigree_table(
        [['DATSTAT_ALTPID', 'FAMILY_ID', 'DDP_CREATED', 'DDP_LASTUPDATED', 'RELATIONSHIP', 'RELATIONSHIP_SPECIFY', 'PATIENT_WEBSITE', 'DESCRIPTION', 'CLINICAL_DIAGNOSES', 'CLINICAL_DIAGNOSES_SPECIFY', 'GENETIC_DIAGNOSES', 'GENETIC_DIAGNOSES_SPECIFY', 'FIND_OUT.DOCTOR', 'FIND_OUT_DOCTOR_DETAILS', 'PATIENT_AGE', 'CONDITION_AGE', 'PATIENT_DECEASED', 'DECEASED_AGE', 'DECEASED_CAUSE', 'DECEASED_STORED_SAMPLE', 'PATIENT_SEX', 'RACE_LIST', 'PTETHNICITY', 'DOCTOR_TYPES_LIST', 'DOCTOR_TYPES_SPECIFY', 'TESTS.NONE', 'TESTS.NOT_SURE', 'TESTS.KARYOTYPE', 'TESTS.SINGLE_GENE_TESTING', 'TESTS.GENE_PANEL_TESTING', 'TESTS.MITOCHON_GENOME_SEQUENCING', 'TESTS.MICROARRAY', 'TESTS_MICROARRAY_YEAR', 'TESTS_MICROARRAY_LAB', 'TESTS_MICROARRAY_RELATIVE_LIST', 'TESTS_MICROARRAY_RELATIVE_SPEC', 'TESTS.WEXOME_SEQUENCING', 'TESTS_WEXOME_SEQUENCING_YEAR', 'TESTS_WEXOME_SEQUENCING_LAB', 'TESTS_WEXOME_SEQUENCING_REL_LI', 'TESTS_WEXOME_SEQUENCING_REL_SP', 'TESTS.WGENOME_SEQUENCING', 'TESTS_WGENOME_SEQUENCING_YEAR', 'TESTS_WGENOME_SEQUENCING_LAB', 'TESTS_WGENOME_SEQUENCING_REL_L', 'TESTS_WGENOME_SEQUENCING_REL_S', 'TESTS.OTHER', 'TEST_OTHER_SPECIFY', 'BIOPSY.NONE', 'BIOPSY', 'BIOPSY.OTHER', 'BIOPSY_OTHER_SPECIFY', 'OTHER_GENETIC_STUDIES', 'OTHER_GENETIC_STUDIES_SPECIFY', 'EXPECTING_GENETIC_RESULTS', 'SAME_CONDITION_MOM', 'CONDITION_AGE_MOM', 'ABLE_TO_PARTICIPATE_MOM', 'DECEASED_MOM', 'STORED_DNA_MOM', 'SAME_CONDITION_DAD', 'CONDITION_AGE_DAD', 'ABLE_TO_PARTICIPATE_DAD', 'DECEASED_DAD', 'STORED_DNA_DAD', 'NO_SIBLINGS', 'SIBLING_LIST', 'NO_CHILDREN', 'CHILD_LIST', 'NO_RELATIVE_AFFECTED', 'RELATIVE_LIST', 'FAMILY_INFO'],
        ['1518231365', '123', '2019-07-31T03:54:21UTC', '2019-08-01T14:12:40UTC', '6', 'Grandchild', 'wwww.myblog.com', u'I have a really debilitating probably genetic condition. I\xe2ve seen many specialists.', '1', u'SMA\xe2s', '1', u'Dwarfism\xe2', '1', 'Dr John Smith', '34', '21', '1', '33', 'heart attack', '2', '1', '["White","Asian","Pacific"]', '2', '["ClinGen","Neurologist","Cardiologist","Other"]', 'Pediatrician', '0', '0', '0', '1', '1', '0', '0', '', '', '', '', '1', '2018', u'UDN\xe2s lab', '["Parent","AuntUncle","NieceNephew","Other"]', 'Grandmother', '1', '', '', '', 'Grandmother', '1', 'Blood work', '0', 'MUSCLE,SKIN,OTHER: Muscle Biopsy, Skin Biopsy, Other Tissue Biopsy', '1', u'Bone\xe2s', '1', 'Undiagnosed Diseases Network', '2', '1', '19', '1', '', '', '2', '', '', '1', '2', '0', '[{"sex":"Female","age":"21","races":["White"],"ethnicity":"NonHispanic","sameCondition":"Yes","ageOnsetCondition":null,"ableToParticipate":"No","siblingId":"d18b9f4b-0995-45e9-9b00-e710d0004a3f"},{"sex":"","age":"17","races":["White"],"ethnicity":"NonHispanic","sameCondition":"","ageOnsetCondition":null,"ableToParticipate":"Yes","siblingId":"3ddc9015-3c2c-484c-b1de-502ba9ffc1e4"}]', '1', '', '0', '[{"sex":"Male","age":"44","races":["White"],"ethnicity":"NonHispanic","sameCondition":"No","ageOnsetCondition":null,"ableToParticipate":"","siblingId":"bb87c69f-6c52-48b4-8854-e639d998abe7"}]', u'patient\xe2s uncle (dads brother) died from Fahrs disease at 70'],
        ['b392fd78b440', '987', '2019-08-06T14:30:44UTC', '2019-08-06T15:18:48UTC', '2', 'Grandchild', '', '', '3', 'SMA', '2', 'Dwarfism', '0', 'Dr John Smith', '47', '2', '0', '33', 'heart attack', '2', '3', '["White"]', '3', '[]', 'Pediatrician', '0', '1', '0', '1', '1', '0', '0', '', '', '', '', '1', '2018', 'UDN', '["Parent","AuntUncle","NieceNephew","Other"]', 'Grandmother', '1', '', '', '', 'Grandmother', '1', 'Blood work', '0', 'NONE: This individual hasn\'t had a biopsy', '1', 'Bone', '0', 'Undiagnosed Diseases Network', '2', '3', '19', '2', '3', '', '', '', '', '', '1', '1', '[{"sex":"Female","age":"21","races":["White"],"ethnicity":"NonHispanic","sameCondition":"Yes","ageOnsetCondition":null,"ableToParticipate":"No","siblingId":"d18b9f4b-0995-45e9-9b00-e710d0004a3f"},{"sex":"","age":"17","races":["White"],"ethnicity":"NonHispanic","sameCondition":"","ageOnsetCondition":null,"ableToParticipate":"Yes","siblingId":"3ddc9015-3c2c-484c-b1de-502ba9ffc1e4"}]', '0: No', '[{"sex":"Male","age":"12","races":["White"],"ethnicity":"NonHispanic","sameCondition":"No","ageOnsetCondition":null,"ableToParticipate":"Unsure","siblingId":"bb87c69f-6c52-48b4-8854-e639d998abe7"}]', '1', '', '']], FILENAME)

        note_1 = u"""#### Clinical Information
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

        note_2 = u"""#### Clinical Information
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; __Patient is my:__ Child (unspecified sex)
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
