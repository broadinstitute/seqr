import os

db_host = os.environ.get('MONGO_SERVICE_HOSTNAME', 'localhost')
db_port = 27017
db_name = 'xbrowse_annotator'

install_dir = os.environ.get("SEQR_DIR", '/seqr')
vep_perl_path = '%(install_dir)s/variant_effect_predictor/variant_effect_predictor.pl' % locals()
vep_cache_dir = '%(install_dir)s/vep_cache_dir' % locals()
vep_batch_size = 50000

reference_populations = [
    {
        'slug': '1kg_wgs_phase3',
        'name': '1000 Genomes v3',
        'file_type': 'sites_vcf',
        'file_path': '%(install_dir)s/data/reference_data/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5a.20130502.sites.decomposed.with_popmax.vcf.gz' % locals(),
        'vcf_info_key': 'AF',
    }, 
    {
       'slug': '1kg_wgs_phase3_popmax',
        'name': '1000 Genomes v3 popmax',
        'file_type': 'sites_vcf',
        'file_path': '%(install_dir)s/data/reference_data/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5a.20130502.sites.decomposed.with_popmax.vcf.gz'  % locals(), 
        'vcf_info_key': 'POPMAX_AF',
    },
    {
        'slug': 'exac_v3',
        'name': 'ExAC v0.3',
        'file_type': 'sites_vcf_with_counts',
        'file_path': '%(install_dir)s/data/reference_data/ExAC.r0.3.sites.vep.popmax.clinvar.vcf.gz' % locals(),
        'ac_info_key': 'AC_Adj',
        'an_info_key': 'AN_Adj',
    }, 
    {
        'slug': 'exac_v3_popmax',
        'name': 'ExAC v0.3 popmax',
        'file_type': 'sites_vcf_with_counts',
        'file_path': '%(install_dir)s/data/reference_data/ExAC.r0.3.sites.vep.popmax.clinvar.vcf.gz' % locals(),
        'ac_info_key': 'AC_POPMAX',
        'an_info_key': 'AN_POPMAX',
    },
]

reference_populations_to_load = []
