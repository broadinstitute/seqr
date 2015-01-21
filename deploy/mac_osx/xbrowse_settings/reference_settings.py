ensembl_rest_host = "beta.rest.ensembl.org"
ensembl_rest_port = 80
ensembl_db_host = "useastdb.ensembl.org"
ensembl_db_port = 3306
ensembl_db_user = "anonymous"
ensembl_db_password = ""

db_host = 'localhost'
db_port = 27017
db_name = 'xbrowse_reference'

import os
xbrowse_code_dir = os.path.abspath(os.path.join(__file__, "../../../../../"))
if not os.path.isdir(xbrowse_code_dir):
    raise Exception("Directory doesn't exist: %s" % xbrowse_code_dir)

gencode_gtf_file = os.path.join(xbrowse_code_dir, 'xbrowse-laptop-downloads/gencode.v19.annotation.gtf.gz')

gene_tags = [
	{
		'slug': 'high_variability', 
		'name': 'High Variability Genes', 
		'storage_type': 'gene_list_file', 
		'data_type': 'bool', 
		'file_path': os.path.join(xbrowse_code_dir, 'xbrowse-laptop-downloads/high_variability.genes.txt'), 
	}, 
	{
		'slug': 'constraint', 
		'name': 'Constraint Score', 
		'data_type': 'test_statistic', 
		'file_path': os.path.join(xbrowse_code_dir, 'xbrowse-laptop-downloads/gene_constraint_scores.csv')
	}
]

gtex_expression_file = os.path.join(xbrowse_code_dir, 'xbrowse-laptop-downloads/RPKM_GeneLevel_September.gct')
gtex_samples_file = os.path.join(xbrowse_code_dir, 'xbrowse-laptop-downloads/gtex_samples.txt')

has_phenotype_data = False
