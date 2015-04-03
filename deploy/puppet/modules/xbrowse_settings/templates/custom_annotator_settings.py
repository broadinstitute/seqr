import os
import pymongo

db = pymongo.Connection()['x_custom_annots']

reference_data_dir = '<%= raw_data_dir %>/'
dbnsfp_dir = os.path.join(reference_data_dir, 'dbNSFP/')
#esp_target_file = reference_data_dir + 'esp_target.interval_list'

