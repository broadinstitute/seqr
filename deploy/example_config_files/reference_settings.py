import os

ensembl_rest_host = "beta.rest.ensembl.org"
ensembl_rest_port = 80
ensembl_db_host = "useastdb.ensembl.org"
ensembl_db_port = 3306
ensembl_db_user = "anonymous"
ensembl_db_password = ""

db_host = 'localhost'
db_port = 27017
db_name = 'xbrowse_reference'

install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
reference_data_dir = os.path.join(install_dir, 'data/reference_data')

gencode_gtf_file = os.path.join(reference_data_dir, 'gencode.v19.annotation.gtf.gz')

gene_tags = [
	{
		'slug': 'high_variability', 
		'name': 'High Variability Genes', 
		'storage_type': 'gene_list_file', 
		'data_type': 'bool', 
		'file_path': os.path.join(reference_data_dir, 'high_variability.genes.txt'),
	}, 
	{
		'slug': 'constraint', 
		'name': 'Constraint Score', 
		'data_type': 'test_statistic', 
		'file_path': os.path.join(reference_data_dir, 'gene_constraint_scores.csv')
	},
        {
                'slug': 'lof_constraint',
                'name': 'LoF Constraint Score',
                'data_type': 'test_statistic',
                'file_path': os.path.join(reference_data_dir, 'cleaned_exac_with_pHI_march16_pLI.csv')
         },
         {
                'slug': 'missense_constraint',
                'name': 'Missense Constraint Score',
                'data_type': 'test_statistic',
                'file_path': os.path.join(reference_data_dir, 'forweb_cleaned_exac_r03_2015_03_16_z_data_missense.csv')
         }
]

gtex_expression_file = os.path.join(reference_data_dir, 'GTEx_Analysis_v6_RNA-seq_RNA-SeQCv1.1.8_gene_rpkm.gct.gz')
gtex_samples_file = os.path.join(reference_data_dir, 'GTEx_Data_V6_Annotations_SampleAttributesDS.txt')

has_phenotype_data = False
