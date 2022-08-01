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
