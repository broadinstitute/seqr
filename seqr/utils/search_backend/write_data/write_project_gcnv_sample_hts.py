import argparse
import hail as hl

from seqr.utils.search_backend.write_data.write_project_samples_utils import write_project_samples_hts

def _read_table(file, **kwargs):
    return hl.read_table(f'gs://hail-backend-datasets/{file}.samples.ht')

def _get_sample_table(ht, sample_id):
    st = ht.filter(ht.samples.sample_id==sample_id)
    st = st.annotate(
        geneIds=hl.if_else(
            st.geneIds != hl.set(st.samples.geneIds),
            hl.missing(hl.tarray(hl.tstr)), st.samples.numExon),
        **{field: hl.if_else(st[field] == st.samples[field], hl.missing(hl.tint32), st.samples[field]) for field in [
            'start', 'end', 'numExon',
        ]},
        **{field: st.samples[field] for field in [
            'cn', 'qs', 'defragged', 'prevCall', 'prevOverlap', 'newCall',
        ]},
    )
    return st.drop('samples')

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('file')
    p.add_argument('project')
    args = p.parse_args()

    write_project_samples_hts(args.file, args.project, _read_table, _get_sample_table)