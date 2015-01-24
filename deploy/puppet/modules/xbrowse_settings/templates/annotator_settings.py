db_host = 'localhost'
db_port = 27017
db_name = 'xbrowse_annotator'

vep_perl_path = '<%= @raw_data_dir %>/variant_effect_predictor/variant_effect_predictor.pl'
vep_cache_dir = '<%= @raw_data_dir %>'
vep_batch_size = 50000

reference_populations = [
    {
        'slug': 'g1k_all',
        'name': '1000 Genomes',
        'file_type': 'sites_vcf',
        'file_path': '<%= @raw_data_dir %>/1000genomes.sites.vcf.gz',
        'vcf_info_key': 'AF',
    },
]