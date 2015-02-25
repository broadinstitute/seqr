import os
import pymongo

db = pymongo.Connection()['x_custom_annots']

xbrowse_install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
reference_data_dir =  os.path.join(xbrowse_install_dir, 'data/reference_data')
dbsnp_vcf_file = os.path.join(reference_data_dir, '00-All.vcf')
dbnsfp_dir = os.path.join(reference_data_dir, 'dbNSFP')
#esp_target_file = reference_data_dir + 'esp_target.interval_list'

