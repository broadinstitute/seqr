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

def _read_table(file, **kwargs):
    return hl.read_table(f'gs://hail-backend-datasets/{file}.samples.ht')

def _get_sample_table(ht, sample_id):
    st = ht.filter(ht.samples.sample_id==sample_id)
    st = st.annotate(
        GT=hl.if_else((st.samples.CN == 0) | (st.samples.CN > 3), hl.Call([1, 1]), hl.Call([0, 1])),
        geneIds=hl.if_else(st.geneIds == hl.set(st.samples.geneIds), hl.missing(hl.tarray(hl.tstr)), st.samples.geneIds),
        **{field: hl.if_else(st[field] == st.samples[field], hl.missing(hl.tint32), st.samples[field]) for field in [
            'start', 'end', 'numExon',
        ]},
        **{field: st.samples[field] for field in [
            'CN', 'QS', 'defragged', 'prevCall', 'prevOverlap', 'newCall',
        ]},
    )
    return st.drop('samples')

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('file')
    p.add_argument('project')
    args = p.parse_args()

    write_project_samples_hts(args.file, args.project, _read_table, _get_sample_table)