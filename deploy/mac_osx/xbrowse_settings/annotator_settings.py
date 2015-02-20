import os

db_host = 'localhost'
db_port = 27017
db_name = 'xbrowse_annotator'

xbrowse_install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
vep_perl_path = '%(xbrowse_install_dir)s/variant_effect_predictor/variant_effect_predictor.pl' % locals()
vep_cache_dir = '%(xbrowse_install_dir)s/vep_cache_dir' % locals()
vep_batch_size = 50000

reference_populations = [
    {
        'slug': 'g1k_all',
        'name': '1000 Genomes',
        'file_type': 'sites_vcf',
        'file_path': '%(xbrowse_install_dir)s/data/reference_data/1000genomes.sites.vcf.gz' % locals(),
        'vcf_info_key': 'AF',
    },
    {
        'slug': 'exac',
        'name': 'ExAC v0.3',
        'file_type': 'sites_vcf',
        'file_path': '%(xbrowse_install_dir)s/data/reference_data/ExAC.r0.3.sites.vep.vcf.gz' % locals(),
        'vcf_info_key': 'AF',
    },
]
