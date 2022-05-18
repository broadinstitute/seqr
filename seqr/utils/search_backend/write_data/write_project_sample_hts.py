import argparse
import hail as hl

def write_project_sample_hts(file, project):
    subset_ht = hl.import_table(f'gs://seqr-project-subsets/{project}_ids.txt', key='s')
    sample_ids = subset_ht.aggregate(hl.agg.collect(subset_ht.s))

    mt =  hl.read_matrix_table( f'gs://hail-backend-datasets/{file}.mt').select_globals().select_rows()
    mt = mt.semi_join_cols(subset_ht)
    mt = mt.filter_rows(hl.agg.any(mt.GT.is_non_ref()))

    mt = mt.annotate_entries(AB=hl.if_else(mt.AD.length() > 1, hl.float(mt.AD[1] / hl.sum(mt.AD)), hl.missing(hl.tfloat)))
    print(f'Exporting {len(sample_ids)} samples')
    for sample_id in sample_ids:
        print(sample_id)
        sample_ht = mt.filter_cols(mt.s==sample_id).key_cols_by().entries()
        sample_ht = sample_ht.select('AB', 'AD', 'DP', 'GQ', 'GT', 'PL')
        sample_ht.write(f'gs://hail-backend-datasets/{file}__samples/{sample_id}.ht')

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('file')
    p.add_argument('project')
    args = p.parse_args()

    write_project_sample_hts(args.file, args.project)