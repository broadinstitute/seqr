import os
import pymongo

db = pymongo.MongoClient(host=os.environ.get('MONGO_SERVICE_HOSTNAME', 'localhost'))['x_custom_annots']

install_dir = os.environ.get("SEQR_DIR", '/seqr')
reference_data_dir =  os.path.join(install_dir, 'data/reference_data')
dbnsfp_dir = os.path.join(reference_data_dir, 'dbNSFP/')
#esp_target_file = reference_data_dir + 'esp_target.interval_list'

