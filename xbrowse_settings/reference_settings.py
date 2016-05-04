import os
import ConfigParser


resources = ConfigParser.SafeConfigParser()
resources.read(['config/resources.ini.sample','config/resources.ini','config/ensembl.ini.sample','config/ensembl.ini'])

ensembl_rest_host = resources.get('ensembl','ensembl_rest_host')
ensembl_rest_port = resources.get('ensembl','ensembl_rest_port')
ensembl_db_host = resources.get('ensembl','ensembl_db_host')
ensembl_db_port = resources.get('ensembl','ensembl_db_port')
ensembl_db_user = resources.get('ensembl','ensembl_db_user')
ensembl_db_password = resources.get('ensembl','ensembl_db_password')

xbrowse_install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
xbrowse_reference_data_dir = os.path.join(xbrowse_install_dir, 'data/reference_data')

gencode_gtf_file = resources.get('seqr_resource_bundle','gencode_gtf_file')
gtex_expression_file = resources.get('seqr_resource_bundle','gtex_expression_file')
gtex_samples_file = resources.get('seqr_resource_bundle','gtex_samples_file')

gene_tags = [
	{
		'slug': 'high_variability',
		'name': 'High Variability Genes',
		'storage_type': 'gene_list_file',
		'data_type': 'bool',
		'file_path': resources.get('seqr_resource_bundle','high_variability'),
	},
	{
		'slug': 'constraint',
		'name': 'Constraint Score',
		'data_type': 'test_statistic',
		'file_path': resources.get('seqr_resource_bundle','constraint_score')
	}
]
has_phenotype_data = False
