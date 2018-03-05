import os

from deploy.utils.constants import REFERENCE_DATA_FILES

ensembl_rest_host = "beta.rest.ensembl.org"
ensembl_rest_port = 80
ensembl_db_host = "useastdb.ensembl.org"
ensembl_db_port = 3306
ensembl_db_user = "anonymous"
ensembl_db_password = ""

db_host = os.environ.get('MONGO_SERVICE_HOSTNAME', 'localhost')
db_port = 27017
db_name = 'xbrowse_reference'

install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
reference_data_dir = os.path.join(install_dir, 'data/reference_data')

gencode_gtf_file = os.path.join(reference_data_dir, REFERENCE_DATA_FILES['gencode'])

gene_tags = [
    {
        'slug': 'high_variability',
        'name': 'High Variability Genes',
        'storage_type': 'gene_list_file',
        'data_type': 'bool',
        'file_path': os.path.join(reference_data_dir, REFERENCE_DATA_FILES['high_variability_genes']),
    },
    {
        'slug': 'constraint',
        'name': 'Constraint Score',
        'data_type': 'test_statistic',
        'file_path': os.path.join(reference_data_dir, REFERENCE_DATA_FILES['gene_constraint_scores'])
    },
    {
        'slug': 'lof_constraint',
        'name': 'LoF Constraint Score',
        'data_type': 'test_statistic',
        'file_path': os.path.join(reference_data_dir, REFERENCE_DATA_FILES['lof_constraint_scores'])
    },
    {
        'slug': 'missense_constraint',
        'name': 'Missense Constraint Score',
        'data_type': 'test_statistic',
        'file_path': os.path.join(reference_data_dir, REFERENCE_DATA_FILES['missense_constraint_scores'])
    }
]

gtex_expression_file = os.path.join(reference_data_dir, REFERENCE_DATA_FILES['gtex_expression'])
gtex_samples_file = os.path.join(reference_data_dir, REFERENCE_DATA_FILES['gtex_samples'])

omim_genemap_file = os.path.join(reference_data_dir, REFERENCE_DATA_FILES['omim_genmap'])
clinvar_tsv_file = os.path.join(reference_data_dir, REFERENCE_DATA_FILES['clinvar'])
dbnsfp_gene_file = os.path.join(reference_data_dir, REFERENCE_DATA_FILES['dbnsfp'])

has_phenotype_data = False
