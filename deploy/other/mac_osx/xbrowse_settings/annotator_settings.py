db_host = 'localhost'
db_port = 27017
db_name = 'xbrowse_annotator'

import os
xbrowse_downloads_dir = os.path.abspath(os.path.join(__file__, "../../../../../xbrowse-laptop-downloads/"))
if not os.path.isdir(xbrowse_downloads_dir):
    raise Exception("Directory doesn't exist: %s" % xbrowse_downloads_dir)

vep_perl_path = '%(xbrowse_downloads_dir)s/variant_effect_predictor/variant_effect_predictor.pl' % locals()
vep_cache_dir = '%(xbrowse_downloads_dir)s/vep_cache_dir' % locals()
vep_batch_size = 50000

reference_populations = [
    {
        'slug': 'g1k_all',
        'name': '1000 Genomes',
        'file_type': 'sites_vcf',
        'file_path': '%(xbrowse_downloads_dir)s/1000genomes.sites.vcf.gz' % locals(),
        'vcf_info_key': 'AF',
    },
]
