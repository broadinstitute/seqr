import os
import pymongo

db = pymongo.MongoClient()['x_custom_annots']

xbrowse_install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
reference_data_dir =  os.path.join(xbrowse_install_dir, 'data/reference_data')
dbnsfp_dir = os.path.join(reference_data_dir, 'dbNSFP/')
#esp_target_file = reference_data_dir + 'esp_target.interval_list'

