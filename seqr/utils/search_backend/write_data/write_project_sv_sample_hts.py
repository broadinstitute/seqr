import argparse
import hail as hl


def write_project_samples_hts(file, project, _read_table, _get_sample_table):
    subset_ht = hl.import_table(f'gs://seqr-project-subsets/{project}_ids.txt', key='s')
    sample_ids = subset_ht.aggregate(hl.agg.collect(subset_ht.s))

    mt = _read_table(file, subset_ht=subset_ht)
    print(f'Exporting {len(sample_ids)} samples')
    for sample_id in sample_ids:
        print(sample_id)
        sample_ht = _get_sample_table(mt, sample_id)
        sample_ht.write(f'gs://hail-backend-datasets/{file}__samples/{sample_id}.ht')

def _read_table(file, subset_ht=None):
    mt = hl.read_matrix_table(f'gs://hail-backend-datasets/{file}.mt')
    mt = mt.rename({'rsid': 'variantId'})
    mt = mt.select_globals().key_rows_by('variantId').select_rows()
    mt = mt.semi_join_cols(subset_ht)
    return mt.filter_rows(hl.agg.any(mt.GT.is_non_ref()))


def _get_sample_table(mt, sample_id):
    sample_ht = mt.filter_cols(mt.s == sample_id).key_cols_by().entries()
    return sample_ht.select('GT', CN=sample_ht.RD_CN, GQ_SV=sample_ht.GQ)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('file')
    p.add_argument('project')
    args = p.parse_args()

    write_project_samples_hts(args.file, args.project, _read_table, _get_sample_table)