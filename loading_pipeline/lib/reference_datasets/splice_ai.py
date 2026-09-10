import hail as hl

from loading_pipeline.lib.core import ReferenceGenome
from loading_pipeline.lib.misc.io import (
    checkpoint,
    compute_hail_n_partitions,
    file_size_bytes,
)
from loading_pipeline.lib.reference_datasets.misc import vcf_to_ht


def remove_duplicate_scores(ht: hl.Table):
    #
    # SpliceAI has many duplicate rows of the ilk:
    #
    #  1:861264      | ["C","A"]  | NA   | -1.00e+01 | NA       | ["A|AL645608.1|0.00|0.00|0.00|0.00|2|27|12|1"] |
    #  1:861264      | ["C","A"]  | NA   | -1.00e+01 | NA       | ["A|SAMD11|0.02|0.01|0.00|0.00|14|38|14|38"]
    #
    count_ht = ht.group_by(*ht.key).aggregate(n=hl.agg.count())
    duplicate_variants_ht = count_ht.filter(count_ht.n > 1)
    duplicates_ht = ht.semi_join(duplicate_variants_ht)
    non_duplicates_ht = ht.anti_join(duplicates_ht)
    return non_duplicates_ht.union(
        # Remove rows that 1) are part of duplicate variant groupings
        # and 2) contain dots.  Then, remove arbitrarily with .distinct()
        duplicates_ht.filter(
            ~duplicates_ht.info.SpliceAI[0].split(delim='\\|')[1].contains('.'),
        ).distinct(),
    )


def get_ht(
    paths: list[str],
    reference_genome: ReferenceGenome,
) -> hl.Table:
    # NB: We ran into weird issues...running out
    # of file descriptors on dataproc :/
    hl._set_flags(use_new_shuffle=None, no_whole_stage_codegen='1')  # noqa: SLF001
    ht = vcf_to_ht(paths, reference_genome)
    ht, checkpoint_path = checkpoint(ht)
    # The default partitions are too big, leading to OOMs.
    ht = ht.repartition(
        int(compute_hail_n_partitions(file_size_bytes(checkpoint_path)) * 2),
        # Note that shuffle=True here, since this is one of the few
        # cases in the pipeline where we want to increase the number
        # of partititons.
    )
    ht, _ = checkpoint(ht)
    ht = remove_duplicate_scores(ht)

    # SpliceAI INFO field description from the VCF header: SpliceAIv1.3 variant annotation. These include
    # delta scores (DS) and delta positions (DP) for acceptor gain (AG), acceptor loss (AL), donor gain (DG), and
    # donor loss (DL). Format: ALLELE|SYMBOL|DS_AG|DS_AL|DS_DG|DS_DL|DP_AG|DP_AL|DP_DG|DP_DL
    ds_start_index = 2
    ds_end_index = 6
    num_delta_scores = ds_end_index - ds_start_index
    ht = ht.select(
        delta_scores=ht.info.SpliceAI[0]
        .split(delim='\\|')[ds_start_index:ds_end_index]
        .map(hl.float32),
    )
    ht = ht.annotate(delta_score=hl.max(ht.delta_scores))
    return ht.annotate(
        splice_consequence_id=hl.if_else(
            ht.delta_score > 0,
            # Splice Consequence enum ID is the index of the max score
            ht.delta_scores.index(ht.delta_score),
            # If no score, use the last index for "No Consequence"
            num_delta_scores,
        ),
    ).drop('delta_scores')
