import hail as hl

from loading_pipeline.lib.core.constants import (
    GRCH37_TO_GRCH38_LIFTOVER_REF_PATH,
    GRCH38_TO_GRCH37_LIFTOVER_REF_PATH,
)
from loading_pipeline.lib.core.definitions import ReferenceGenome


def add_rg38_liftover() -> None:
    rg37 = hl.get_reference(ReferenceGenome.GRCh37.value)
    rg38 = hl.get_reference(ReferenceGenome.GRCh38.value)
    if not rg38.has_liftover(rg37):
        rg38.add_liftover(GRCH38_TO_GRCH37_LIFTOVER_REF_PATH, rg37)


def add_rg37_liftover() -> None:
    rg37 = hl.get_reference(ReferenceGenome.GRCh37.value)
    rg38 = hl.get_reference(ReferenceGenome.GRCh38.value)
    if not rg37.has_liftover(rg38):
        rg37.add_liftover(GRCH37_TO_GRCH38_LIFTOVER_REF_PATH, rg38)


def remove_liftover():
    rg37 = hl.get_reference(ReferenceGenome.GRCh37.value)
    rg38 = hl.get_reference(ReferenceGenome.GRCh38.value)
    if rg37.has_liftover(rg38):
        rg37.remove_liftover(rg38)
    if rg38.has_liftover(rg37):
        rg38.remove_liftover(rg37)
