import argparse
import hail as hl

from seqr.utils.search_backend.write_data.write_project_samples_utils import write_project_samples_hts

def _read_table(file, subset_ht=None):
    mt = hl.read_matrix_table(f'gs://hail-backend-datasets/{file}.mt').select_globals().select_rows()
    mt = mt.semi_join_cols(subset_ht)
    mt = mt.filter_rows(hl.agg.any(mt.GT.is_non_ref()))
    return mt.annotate_entries(AB=hl.if_else(mt.AD.length() > 1, hl.float(mt.AD[1] / hl.sum(mt.AD)), hl.missing(hl.tfloat)))

def _get_sample_table(mt, sample_id):
    sample_ht = mt.filter_cols(mt.s == sample_id).key_cols_by().entries()
    return sample_ht.select('AB', 'AD', 'DP', 'GQ', 'GT', 'PL')

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('file')
    p.add_argument('project')
    args = p.parse_args()

    write_project_samples_hts(args.file, args.project, _read_table, _get_sample_table)