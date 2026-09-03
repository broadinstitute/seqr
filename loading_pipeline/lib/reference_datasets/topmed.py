import hail as hl

from loading_pipeline.lib.core import ReferenceGenome
from loading_pipeline.lib.misc.nested_field import parse_nested_field
from loading_pipeline.lib.reference_datasets.misc import vcf_to_ht

SELECT = {
    'AC': 'info.AC#',
    'AF': 'info.AF#',
    'AN': 'info.AN',
    'Hom': 'info.Hom#',
    'Het': 'info.Het#',
}


def get_ht(path: str, reference_genome: ReferenceGenome) -> hl.Table:
    ht = vcf_to_ht(path, reference_genome)
    if reference_genome == ReferenceGenome.GRCh37:
        ht = ht.filter(ht.locus.position == hl.int(ht.info.OriginalStart))
    return ht.select(
        **{k: parse_nested_field(ht, v) for k, v in SELECT.items()},
    )
