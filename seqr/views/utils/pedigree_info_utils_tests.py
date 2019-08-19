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

    # TODO test datstat upload
