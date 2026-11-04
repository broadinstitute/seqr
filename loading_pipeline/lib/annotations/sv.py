# ruff: noqa: N806
from typing import Any

import hail as hl


def populations(
    ht: hl.Table,
    gnomad_svs_ht: hl.Table,
    **_: Any,
) -> hl.Expression:
    gnomad_sv_id = ht['info.GNOMAD_V4.1_TRUTH_VID']
    gnomad_sv = gnomad_svs_ht[gnomad_sv_id]
    return hl.struct(
        gnomad_svs=hl.or_missing(
            hl.is_defined(gnomad_sv),
            hl.struct(
                af=gnomad_sv.AF,
                het=gnomad_sv.N_HET,
                hom=gnomad_sv.N_HOM,
                id=gnomad_sv_id,
            ),
        ),
    )
