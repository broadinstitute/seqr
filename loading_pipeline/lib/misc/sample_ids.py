from collections import Counter

import hail as hl

from loading_pipeline.lib.logger import get_logger
from loading_pipeline.lib.misc.validation import SeqrValidationError

logger = get_logger(__name__)


def remap_sample_ids(
    mt: hl.MatrixTable,
    project_remap_ht: hl.Table,
) -> hl.MatrixTable:
    collected_remap = project_remap_ht.collect()
    s_dups = [k for k, v in Counter([r.s for r in collected_remap]).items() if v > 1]
    seqr_dups = [
        k for k, v in Counter([r.seqr_id for r in collected_remap]).items() if v > 1
    ]

    if len(s_dups) > 0 or len(seqr_dups) > 0:
        msg = f'Duplicate s or seqr_id entries in remap file were found. Duplicate s:{s_dups}. Duplicate seqr_id:{seqr_dups}.'
        raise SeqrValidationError(msg)

    missing_samples = project_remap_ht.anti_join(mt.cols()).collect()
    remap_count = len(collected_remap)

    if len(missing_samples) != 0:
        message = (
            f'Only {project_remap_ht.semi_join(mt.cols()).count()} out of {remap_count} '
            'remap IDs matched IDs in the variant callset.\n'
            f"IDs that aren't in the callset: {missing_samples}\n"
        )
        raise SeqrValidationError(message)

    mt = mt.annotate_cols(**project_remap_ht[mt.s])
    remap_expr = hl.if_else(hl.is_missing(mt.seqr_id), mt.s, mt.seqr_id)
    mt = mt.annotate_cols(seqr_id=remap_expr, vcf_id=mt.s)
    mt = mt.key_cols_by(s=mt.seqr_id)
    logger.info(f'Remapped {remap_count} sample ids...')
    return mt


def subset_samples(
    mt: hl.MatrixTable,
    sample_subset_ht: hl.Table,
) -> hl.MatrixTable:
    subset_count = sample_subset_ht.count()
    anti_join_ht = sample_subset_ht.anti_join(mt.cols())
    anti_join_ht_count = anti_join_ht.count()
    if subset_count == 0:
        message = '0 sample ids found the subset HT, something is probably wrong.'
        raise SeqrValidationError(message)

    if anti_join_ht_count != 0:
        missing_samples = anti_join_ht.s.collect()
        message = (
            f'Only {subset_count - anti_join_ht_count} out of {subset_count} '
            f'subsetting-table IDs matched IDs in the variant callset.\n'
            f"IDs that aren't in the callset: {missing_samples}\n"
            f'All callset sample IDs:{mt.s.collect()}'
        )
        raise SeqrValidationError(message)
    logger.info(f'Subsetted to {subset_count} sample ids')
    mt = mt.semi_join_cols(sample_subset_ht)
    return mt.filter_rows(hl.agg.any(hl.is_defined(mt.GT)))
