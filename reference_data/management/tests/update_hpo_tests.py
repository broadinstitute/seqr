import mock
import responses
import tempfile

from django.core.management import call_command
from django.test import TestCase

from reference_data.models import HumanPhenotypeOntology

PHO_DATA = [
    'format-version: 1.2\n',
    'data-version: hp/releases/2020-03-27\n',
    'saved-by: Peter Robinson uni\xe7\xf8de, Sebastian Koehler, Sandra Doelken, Chris Mungall, Melissa Haendel, Nicole Vasilevsky, Monarch Initiative, et al.\n',
    'subsetdef: hposlim_core "Core clinical terminology"\n',
    'subsetdef: secondary_consequence "Consequence of a disorder in another organ system."\n',
    'synonymtypedef: abbreviation "abbreviation"\n',
    'synonymtypedef: layperson "layperson term"\n',
    'synonymtypedef: obsolete_synonym "discarded/obsoleted synonym"\n',
    'synonymtypedef: plural_form "plural form"\n',
    'synonymtypedef: uk_spelling "UK spelling"\n',
    'default-namespace: human_phenotype\n',
    'remark: Please see license of HPO at http://www.human-phenotype-ontology.org\n',
    'ontology: hp.obo\n',
    'property_value: http://purl.org/dc/elements/1.1/creator "Human Phenotype Ontology Consortium" xsd:string\n',
    'property_value: http://purl.org/dc/elements/1.1/creator "Monarch Initiative" xsd:string\n',
    'property_value: http://purl.org/dc/elements/1.1/creator "Peter Robinson" xsd:string\n',
    'property_value: http://purl.org/dc/elements/1.1/creator "Sebastian Kohler" xsd:string\n',
    'property_value: http://purl.org/dc/elements/1.1/description "The Human Phenotype Ontology (HPO) provides a standardized vocabulary of phenotypic abnormalities and clinical features encountered in human disease." xsd:string\n',
    'property_value: http://purl.org/dc/elements/1.1/license https://hpo.jax.org/app/license xsd:string\n',
    'property_value: http://purl.org/dc/elements/1.1/rights "Peter Robinson, Sebastian Koehler, The Human Phenotype Ontology Consortium, and The Monarch Initiative" xsd:string\n',
    'property_value: http://purl.org/dc/elements/1.1/subject "Phenotypic abnormalities encountered in human disease" xsd:string\n',
    'property_value: http://purl.org/dc/elements/1.1/title "Human Phenotype Ontology" xsd:string\n',
    'property_value: http://purl.org/dc/terms/license https://hpo.jax.org/app/license xsd:string\n',
    'logical-definition-view-relation: has_part\n',
    '\n',
    '[Term]\n',
    'id: HP:0000001\n',
    'name: All\n',
    'comment: Root of all terms in the Human Phenotype Ontology.\n',
    'xref: UMLS:C0444868\n',
    '\n',
    '[Term]\n',
    'id: HP:0000002\n',
    'name: Abnormality of body height\n',
    'def: "Deviation from the norm of height with respect to that which is expected according to age and gender norms." [HPO:probinson]\n',
    'synonym: "Abnormality of body height" EXACT layperson []\n',
    'xref: UMLS:C4025901\n',
    'is_a: HP:0000003 ! Growth abnormality\n',
    'created_by: peter\n',
    'creation_date: 2008-02-27T02:20:00Z\n',
    '\n',
    '[Term]\n',
    'id: HP:0000003\n',
    'name: Multicystic kidney dysplasia\n',
    'alt_id: HP:0004715\n',
    'def: "Multicystic dysplasia of the kidney is characterized by multiple cysts of varying size in the kidney and the absence of a normal pelvicaliceal system. The condition is associated with ureteral or ureteropelvic atresia, and the affected kidney is nonfunctional." [HPO:curators]\n',
    'comment: Multicystic kidney dysplasia is the result of abnormal fetal renal development in which the affected kidney is replaced by multiple cysts and has little or no residual function. The vast majority of multicystic kidneys are unilateral. Multicystic kidney can be diagnosed on prenatal ultrasound.\n',
    'synonym: "Multicystic dysplastic kidney" EXACT []\n',
    'synonym: "Multicystic kidneys" EXACT []\n',
    'synonym: "Multicystic renal dysplasia" EXACT []\n',
    'xref: MSH:D021782\n',
    'xref: SNOMEDCT_US:204962002\n',
    'xref: SNOMEDCT_US:82525005\n',
    'xref: UMLS:C3714581\n',
    'is_a: HP:0000001 ! Renal cyst\n',
    '\n',
    '[Term]\n', # no is_a
    'id: HP:0000005\n',
    'name: Mode of inheritance\n',
    'alt_id: HP:0001453\n',
    'alt_id: HP:0001461\n',
    'def: "The pattern in which a particular genetic trait or disorder is passed from one generation to the next." [HPO:probinson]\n',
    'synonym: "Inheritance" EXACT []\n',
    'xref: UMLS:C1708511\n',
    '\n',
    '[Term]\n', # is_a == "HP:0000118"
    'id: HP:0000152\n',
    'name: Abnormality of head or neck\n',
    'def: "An abnormality of head and neck." [HPO:probinson]\n',
    'synonym: "Abnormality of head or neck" EXACT layperson []\n',
    'synonym: "Head and neck abnormality" EXACT layperson []\n',
    'xref: UMLS:C4021817\n',
    'is_a: HP:0000118 ! Phenotypic abnormality\n',
]

EXPECTED_DB_DATA = {
    'HP:0000152': {
        'is_category': True,
        'definition': '"An abnormality of head and neck." [HPO:probinson]',
        'name': 'Abnormality of head or neck',
        'parent_id': 'HP:0000118',
        'hpo_id': 'HP:0000152',
        'category_id': 'HP:0000152'
    },
    'HP:0000005': {
        'is_category': False,
        'definition': '"The pattern in which a particular genetic trait or disorder is passed from one generation to the next." [HPO:probinson]',
        'name': 'Mode of inheritance',
        'parent_id': None,
        'hpo_id': 'HP:0000005',
        'category_id': None,
    },
    'HP:0000001': {
        'is_category': False,
        'definition': None,
        'parent_id': None,
        'name': 'All',
        'hpo_id': 'HP:0000001',
        'category_id': None,
    },
    'HP:0000002': {
        'is_category': False,
        'definition': '"Deviation from the norm of height with respect to that which is expected according to age and gender norms." [HPO:probinson]',
        'name': 'Abnormality of body height',
        'parent_id': 'HP:0000003',
        'hpo_id': 'HP:0000002',
        'category_id': None
    },
    'HP:0000003': {
        'is_category': False,
        'definition': '"Multicystic dysplasia of the kidney is characterized by multiple cysts of varying size in the kidney and the absence of a normal pelvicaliceal system. The condition is associated with ureteral or ureteropelvic atresia, and the affected kidney is nonfunctional." [HPO:curators]',
        'name': 'Multicystic kidney dysplasia',
        'parent_id': 'HP:0000001',
        'hpo_id': 'HP:0000003',
        'category_id': None
    }
}

class UpdateHpoTest(TestCase):
    databases = '__all__'
    fixtures = ['users', 'reference_data']

    @responses.activate
    @mock.patch('reference_data.management.commands.update_human_phenotype_ontology.logger')
    @mock.patch('reference_data.management.commands.utils.download_utils.tempfile')
    def test_update_hpo_command(self, mock_tempfile, mock_logger):
        tmp_dir = tempfile.gettempdir()
        mock_tempfile.gettempdir.return_value = tmp_dir
        tmp_file = '{}/hp.obo'.format(tmp_dir)

        url = 'http://purl.obolibrary.org/obo/hp.obo'
        responses.add(responses.HEAD, url, headers={"Content-Length": "1024"})
        responses.add(responses.GET, url, body=''.join(PHO_DATA[:40]))
        responses.add(responses.GET, url, body=''.join(PHO_DATA))

        # test data which causes exception (missing parent hpo id)
        with self.assertRaises(ValueError) as ve:
            call_command('update_human_phenotype_ontology')
        self.assertEqual(str(ve.exception), "Strange id: HP:0000003")

        # test without a file_path parameter
        call_command('update_human_phenotype_ontology')

        calls = [
            mock.call('Deleting HumanPhenotypeOntology table with 12 records and creating new table with 5 records'),
            mock.call('Done'),
        ]
        mock_logger.info.assert_has_calls(calls)

        # test with a hpo_file_path parameter
        responses.remove(responses.GET, url)
        mock_logger.reset_mock()
        call_command('update_human_phenotype_ontology', tmp_file)

        calls = [
            mock.call('Deleting HumanPhenotypeOntology table with 5 records and creating new table with 5 records'),
            mock.call('Done'),
        ]
        mock_logger.info.assert_has_calls(calls)

        records = {record.hpo_id: {
            'is_category': record.is_category,
            'definition': record.definition,
            'name': record.name,
            'parent_id': record.parent_id,
            'hpo_id': record.hpo_id,
            'category_id': record.category_id
        } for record in HumanPhenotypeOntology.objects.all()}
        self.assertDictEqual(records, EXPECTED_DB_DATA)
