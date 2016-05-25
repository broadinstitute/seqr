import os
import ConfigParser

resources = ConfigParser.SafeConfigParser()
resources.read(['config/resources.ini.sample','config/resources.ini','config/ensembl.ini.sample','config/ensembl.ini'])

xbrowse_install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
vep_perl_path = '%(xbrowse_install_dir)s/variant_effect_predictor/variant_effect_predictor.pl' % locals()
vep_cache_dir = '%(xbrowse_install_dir)s/vep_cache_dir' % locals()
vep_batch_size = 50000

reference_populations = [
    {
        'slug': '1kg_wgs_phase3',
        'name': '1000 Genomes v3',
        'file_type': 'sites_vcf',
        'file_path': resources.get('reference_populations','1kg_wgs_phase3'),
        'vcf_info_key': 'AF',
    },
    {
       'slug': '1kg_wgs_phase3_popmax',
        'name': '1000 Genomes v3 popmax',
        'file_type': 'sites_vcf',
        'file_path': resources.get('reference_populations','1kg_wgs_phase3_popmax'),
        'vcf_info_key': 'POPMAX_AF',
    },
    {
        'slug': 'exac_v3',
        'name': 'ExAC v0.3',
        'file_type': 'sites_vcf_with_counts',
        'file_path': resources.get('reference_populations','exac_v3'),
        'ac_info_key': 'AC_Adj',
        'an_info_key': 'AN_Adj',
    },
    {
        'slug': 'exac_v3_popmax',
        'name': 'ExAC v0.3 popmax',
        'file_type': 'sites_vcf_with_counts',
        'file_path': resources.get('reference_populations','exac_v3_popmax'),
        'ac_info_key': 'AC_POPMAX',
        'an_info_key': 'AN_POPMAX',
    },
]
reference_populations_to_load = []
