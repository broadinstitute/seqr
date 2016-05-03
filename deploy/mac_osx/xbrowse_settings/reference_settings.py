import os
from django.conf import settings

ensembl_rest_host = "beta.rest.ensembl.org"
ensembl_rest_port = 80
ensembl_db_host = "useastdb.ensembl.org"
ensembl_db_port = 3306
ensembl_db_user = "anonymous"
ensembl_db_password = ""

db_host = settings.DB_HOST
db_port = settings.DB_PORT
db_name = 'xbrowse_reference'

xbrowse_install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
xbrowse_reference_data_dir = os.path.join(xbrowse_install_dir, 'data/reference_data')

gencode_gtf_file = os.path.join(xbrowse_reference_data_dir, 'gencode.v19.annotation.gtf.gz')

gene_tags = [
	{
		'slug': 'high_variability',
		'name': 'High Variability Genes',
		'storage_type': 'gene_list_file',
		'data_type': 'bool',
		'file_path': os.path.join(xbrowse_reference_data_dir, 'high_variability.genes.txt'),
	},
	{
		'slug': 'constraint',
		'name': 'Constraint Score',
		'data_type': 'test_statistic',
		'file_path': os.path.join(xbrowse_reference_data_dir, 'gene_constraint_scores.csv')
	}
]

gtex_expression_file = os.path.join(xbrowse_reference_data_dir, 'RPKM_GeneLevel_September.gct')
gtex_samples_file = os.path.join(xbrowse_reference_data_dir, 'gtex_samples.txt')

has_phenotype_data = False
