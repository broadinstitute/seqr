from collections.abc import Callable

import hail as hl

from loading_pipeline.lib.core import ReferenceGenome


def global_idx_field(reference_genome: ReferenceGenome) -> str:
    return 'gnomad' if reference_genome == ReferenceGenome.GRCh37 else 'adj'


def faf_globals_field(reference_genome: ReferenceGenome) -> str:
    return (
        'popmax_index_dict'
        if reference_genome == ReferenceGenome.GRCh37
        else 'faf_index_dict'
    )


def hemi_field(reference_genome: ReferenceGenome) -> str:
    return 'gnomad_male' if reference_genome == ReferenceGenome.GRCh37 else 'XY_adj'


def get_ht(
    path: str,
    reference_genome: ReferenceGenome,
    af_popmax_expression: Callable,
) -> hl.Table:
    ht = hl.read_table(path)
    global_idx = hl.eval(ht.globals.freq_index_dict[global_idx_field(reference_genome)])
    ht = ht.select(
        AF=hl.float32(ht.freq[global_idx].AF),
        AN=ht.freq[global_idx].AN,
        AC=ht.freq[global_idx].AC,
        Hom=ht.freq[global_idx].homozygote_count,
        AF_POPMAX_OR_GLOBAL=hl.float32(
            hl.or_else(
                af_popmax_expression(ht, reference_genome),
                ht.freq[global_idx].AF,
            ),
        ),
        FAF_AF=hl.float32(
            ht.faf[
                ht.globals[faf_globals_field(reference_genome)][
                    global_idx_field(reference_genome)
                ]
            ].faf95,
        ),
        Hemi=hl.if_else(
            ht.locus.in_autosome_or_par(),
            0,
            ht.freq[ht.globals.freq_index_dict[hemi_field(reference_genome)]].AC,
        ),
    )
    return ht.select_globals()
