from django.test import TestCase

from seqr.views.utils.pedigree_info_utils import _parse_pedigree_table_rows

EXPECTED_ROWS = [
    {
        "family_id": "FAM001",
        "individual_id": "IND001",
        "paternal_id": "IND002",
        "maternal_id": "IND003",
        "sex": "M",
        "affected": "A",
    },
    {
        "family_id": "FAM001",
        "individual_id": "IND002",
        "paternal_id": "",
        "maternal_id": "",
        "sex": "M",
        "affected": "U",
    },
    {
        "family_id": "FAM001",
        "individual_id": "IND003",
        "paternal_id": "",
        "maternal_id": "",
        "sex": "F",
        "affected": "U",
    },
]


class ParsePedigreeTableRowsTest(TestCase):
    def setUp(self):
        self.filename = "test_file"
        self.header = [
            "family_id",
            "individual_id",
            "paternal_id",
            "maternal_id",
            "sex",
            "affected",
        ]
        self.parsed_file_with_whitespace = [
            self.header,
            ["FAM001", " IND001 ", " IND002 ", " IND003 ", "M", "A"],
            ["FAM001", " IND002 ", "", "", "M", "U"],
            ["FAM001", " IND003 ", "", "", "F", "U"],
        ]

    def test_parse_pedigree_table_rows_with_rows(self):
        rows = self.parsed_file_with_whitespace[1:]
        result, header = _parse_pedigree_table_rows(
            self.parsed_file_with_whitespace, self.filename, self.header, rows
        )
        self.assertEqual(result, EXPECTED_ROWS)
        self.assertEqual(header, self.header)

    def test_parse_pedigree_table_rows_without_rows(self):
        result, header = _parse_pedigree_table_rows(
            self.parsed_file_with_whitespace, self.filename, self.header
        )
        self.assertEqual(result, EXPECTED_ROWS)
        self.assertEqual(header, self.header)
