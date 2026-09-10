import hail as hl

from loading_pipeline.lib.core import ReferenceGenome


def get_ht(path: str, reference_genome: ReferenceGenome) -> hl.Table:
    if reference_genome == ReferenceGenome.GRCh37:
        return hl.read_matrix_table(path).rows()
    return hl.read_table(path)
