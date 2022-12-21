import argparse
import hail as hl


def add_interval_ref_data(file):
    # TODO on new datasets this will already be annotated in the pipeline
    hl._set_flags(use_new_shuffle='1')
    ht = hl.read_matrix_table(f'gs://hail-backend-datasets/{file}.mt').rows()
    interval_ref_data = hl.read_table('gs://hail-backend-datasets/combined_interval_reference_data.ht').index(
        ht.locus, all_matches=True
    )
    ht = ht.annotate(
        gnomad_non_coding_constraint=hl.struct(
            z_score=interval_ref_data.filter(
                lambda x: hl.is_defined(x.gnomad_non_coding_constraint["z_score"])
            ).gnomad_non_coding_constraint.z_score.first()
        ),
        screen=hl.struct(region_type=interval_ref_data.flatmap(lambda x: x.screen["region_type"])),
    )
    ht.write(f'gs://hail-backend-datasets/{file}.interval_annotations.ht')


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('file')
    args = p.parse_args()

    add_interval_ref_data(args.file)
