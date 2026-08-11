import hail as hl

from loading_pipeline.lib.core import ReferenceGenome
from loading_pipeline.lib.reference_datasets.gnomad_utils import get_ht as _get_ht


def af_popmax_expression(
    ht: hl.Table,
    reference_genome: ReferenceGenome,
) -> hl.Expression:
    if reference_genome == ReferenceGenome.GRCh37:
        return ht.popmax[ht.globals.popmax_index_dict['gnomad']].AF
    return ht.grpmax['gnomad'].AF


def get_ht(path: str, reference_genome: ReferenceGenome) -> hl.Table:
    return _get_ht(
        path,
        reference_genome,
        af_popmax_expression,
    )
