import os

import os
xbrowse_code_dir = os.path.abspath(os.path.join(__file__, "../../../../../"))
if not os.path.isdir(xbrowse_code_dir):
    raise Exception("Directory doesn't exist: %s" % xbrowse_code_dir)

vep_perl_path = os.path.join(xbrowse_code_dir, 'xbrowse-laptop-downloads/variant_effect_predictor/variant_effect_predictor.pl')
vep_cache_dir = os.path.join(xbrowse_code_dir, 'xbrowse-laptop-downloads/vep-cache-dir/')
vep_batch_size = 25000
