import mock

from django.core.management import call_command
from django.test import TestCase

from reference_data.models import HumanPhenotypeOntology

import os
import tempfile
import shutil

PHO_DATA = [
    u'format-version: 1.2\n',
    u'data-version: hp/releases/2020-03-27\n',
    u'saved-by: Peter Robinson, Sebastian Koehler, Sandra Doelken, Chris Mungall, Melissa Haendel, Nicole Vasilevsky, Monarch Initiative, et al.\n',
    u'subsetdef: hposlim_core "Core clinical terminology"\n',
    u'subsetdef: secondary_consequence "Consequence of a disorder in another organ system."\n',
    u'synonymtypedef: abbreviation "abbreviation"\n',
    u'synonymtypedef: layperson "layperson term"\n',
    u'synonymtypedef: obsolete_synonym "discarded/obsoleted synonym"\n',
    u'synonymtypedef: plural_form "plural form"\n',
    u'synonymtypedef: uk_spelling "UK spelling"\n',
    u'default-namespace: human_phenotype\n',
    u'remark: Please see license of HPO at http://www.human-phenotype-ontology.org\n',
    u'ontology: hp.obo\n',
    u'property_value: http://purl.org/dc/elements/1.1/creator "Human Phenotype Ontology Consortium" xsd:string\n',
    u'property_value: http://purl.org/dc/elements/1.1/creator "Monarch Initiative" xsd:string\n',
    u'property_value: http://purl.org/dc/elements/1.1/creator "Peter Robinson" xsd:string\n',
    u'property_value: http://purl.org/dc/elements/1.1/creator "Sebastian Kohler" xsd:string\n',
    u'property_value: http://purl.org/dc/elements/1.1/description "The Human Phenotype Ontology (HPO) provides a standardized vocabulary of phenotypic abnormalities and clinical features encountered in human disease." xsd:string\n',
    u'property_value: http://purl.org/dc/elements/1.1/license https://hpo.jax.org/app/license xsd:string\n',
    u'property_value: http://purl.org/dc/elements/1.1/rights "Peter Robinson, Sebastian Koehler, The Human Phenotype Ontology Consortium, and The Monarch Initiative" xsd:string\n',
    u'property_value: http://purl.org/dc/elements/1.1/subject "Phenotypic abnormalities encountered in human disease" xsd:string\n',
    u'property_value: http://purl.org/dc/elements/1.1/title "Human Phenotype Ontology" xsd:string\n',
    u'property_value: http://purl.org/dc/terms/license https://hpo.jax.org/app/license xsd:string\n',
    u'logical-definition-view-relation: has_part\n',
    u'\n',
    u'[Term]\n',
    u'id: HP:0000001\n',
    u'name: All\n',
    u'comment: Root of all terms in the Human Phenotype Ontology.\n',
    u'xref: UMLS:C0444868\n',
    u'\n',
    u'[Term]\n',
    u'id: HP:0000002\n',
    u'name: Abnormality of body height\n',
    u'def: "Deviation from the norm of height with respect to that which is expected according to age and gender norms." [HPO:probinson]\n',
    u'synonym: "Abnormality of body height" EXACT layperson []\n',
    u'xref: UMLS:C4025901\n',
    u'is_a: HP:0000003 ! Growth abnormality\n',
    u'created_by: peter\n',
    u'creation_date: 2008-02-27T02:20:00Z\n',
    u'\n',
    u'[Term]\n',
    u'id: HP:0000003\n',
    u'name: Multicystic kidney dysplasia\n',
    u'alt_id: HP:0004715\n',
    u'def: "Multicystic dysplasia of the kidney is characterized by multiple cysts of varying size in the kidney and the absence of a normal pelvicaliceal system. The condition is associated with ureteral or ureteropelvic atresia, and the affected kidney is nonfunctional." [HPO:curators]\n',
    u'comment: Multicystic kidney dysplasia is the result of abnormal fetal renal development in which the affected kidney is replaced by multiple cysts and has little or no residual function. The vast majority of multicystic kidneys are unilateral. Multicystic kidney can be diagnosed on prenatal ultrasound.\n',
    u'synonym: "Multicystic dysplastic kidney" EXACT []\n',
    u'synonym: "Multicystic kidneys" EXACT []\n',
    u'synonym: "Multicystic renal dysplasia" EXACT []\n',
    u'xref: MSH:D021782\n',
    u'xref: SNOMEDCT_US:204962002\n',
    u'xref: SNOMEDCT_US:82525005\n',
    u'xref: UMLS:C3714581\n',
    u'is_a: HP:0000001 ! Renal cyst\n',
    u'\n',
    u'[Term]\n', # no is_a
    u'id: HP:0000005\n',
    u'name: Mode of inheritance\n',
    u'alt_id: HP:0001453\n',
    u'alt_id: HP:0001461\n',
    u'def: "The pattern in which a particular genetic trait or disorder is passed from one generation to the next." [HPO:probinson]\n',
    u'synonym: "Inheritance" EXACT []\n',
    u'xref: UMLS:C1708511\n',
    u'\n',
    u'[Term]\n', # is_a == "HP:0000118"
    u'id: HP:0000152\n',
    u'name: Abnormality of head or neck\n',
    u'def: "An abnormality of head and neck." [HPO:probinson]\n',
    u'synonym: "Abnormality of head or neck" EXACT layperson []\n',
    u'synonym: "Head and neck abnormality" EXACT layperson []\n',
    u'xref: UMLS:C4021817\n',
    u'is_a: HP:0000118 ! Phenotypic abnormality\n',
]

EXPECTED_DB_DATA = [
    {
        'is_category': True,
        'definition': u'"An abnormality of head and neck." [HPO:probinson]',
        'name': u'Abnormality of head or neck',
        'parent_id': u'HP:0000118',
        'hpo_id': u'HP:0000152',
        'category_id': u'HP:0000152'
    },
    {
        'is_category': False,
        'definition': u'"The pattern in which a particular genetic trait or disorder is passed from one generation to the next." [HPO:probinson]',
        'name': u'Mode of inheritance',
        'parent_id': None,
        'hpo_id': u'HP:0000005',
        'category_id': None,
    },
    {
        'is_category': False,
        'definition': None,
        'parent_id': None,
        'name': u'All',
        'hpo_id': u'HP:0000001',
        'category_id': None,
    },
    {
        'is_category': False,
        'definition': u'"Deviation from the norm of height with respect to that which is expected according to age and gender norms." [HPO:probinson]',
        'name': u'Abnormality of body height',
        'parent_id': u'HP:0000003',
        'hpo_id': u'HP:0000002',
        'category_id': None
    },
    {
        'is_category': False,
        'definition': u'"Multicystic dysplasia of the kidney is characterized by multiple cysts of varying size in the kidney and the absence of a normal pelvicaliceal system. The condition is associated with ureteral or ureteropelvic atresia, and the affected kidney is nonfunctional." [HPO:curators]',
        'name': u'Multicystic kidney dysplasia',
        'parent_id': u'HP:0000001',
        'hpo_id': u'HP:0000003',
        'category_id': None
    }
]

class UpdateHpoTest(TestCase):
    fixtures = ['users', 'reference_data']
    multi_db = True

    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()

        # Prepare normal test data
        self.temp_file_path = os.path.join(self.test_dir, 'hp.obo')
        with open(self.temp_file_path, 'w') as f:
            f.write(u''.join(PHO_DATA))

    def tearDown(self):
        # Close the file, the directory will be removed after the test
        shutil.rmtree(self.test_dir)

    @mock.patch('reference_data.management.commands.update_human_phenotype_ontology.logger')
    @mock.patch('reference_data.management.commands.update_human_phenotype_ontology.download_file')
    def test_update_hpo_command(self, mock_download, mock_logger):
        temp_bad_file_path = os.path.join(self.test_dir, 'bad_hp.obo')
        mock_download.return_value = temp_bad_file_path
        # Prepare data which causes exception (missing parent hpo id)
        with open(temp_bad_file_path, 'w') as f:
            f.write(u''.join(PHO_DATA[:40]))
        with self.assertRaises(ValueError) as ve:
            call_command('update_human_phenotype_ontology')
        self.assertEqual(ve.exception.message, "Strange id: HP:0000003")

        # test without a file_path parameter
        mock_download.reset_mock()
        mock_download.return_value = self.temp_file_path
        call_command('update_human_phenotype_ontology')
        mock_download.assert_called_with(url='http://purl.obolibrary.org/obo/hp.obo')

        calls = [
            mock.call('Deleting HumanPhenotypeOntology table with 11 records and creating new table with 5 records'),
            mock.call('Done'),
        ]
        mock_logger.info.assert_has_calls(calls)

        # test with a hpo_file_path parameter
        mock_download.reset_mock()
        mock_logger.reset_mock()
        call_command('update_human_phenotype_ontology', self.temp_file_path)
        mock_download.assert_not_called()

        calls = [
            mock.call('Deleting HumanPhenotypeOntology table with 5 records and creating new table with 5 records'),
            mock.call('Done'),
        ]
        mock_logger.info.assert_has_calls(calls)

        records = [{
            'is_category': record.is_category,
            'definition': record.definition,
            'name': record.name,
            'parent_id': record.parent_id,
            'hpo_id': record.hpo_id,
            'category_id': record.category_id
        } for record in HumanPhenotypeOntology.objects.all()]
        self.assertListEqual(records, EXPECTED_DB_DATA)
