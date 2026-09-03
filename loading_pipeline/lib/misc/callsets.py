import functools

import hail as hl

from loading_pipeline.lib.core import DatasetType, ReferenceGenome
from loading_pipeline.lib.paths import remapped_and_subsetted_callset_path


def get_callset_ht(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    callset_path: str,
    project_guids: list[str],
):
    callset_hts = [
        hl.read_matrix_table(
            remapped_and_subsetted_callset_path(
                reference_genome,
                dataset_type,
                callset_path,
                project_guid,
            ),
        ).rows()
        for project_guid in project_guids
    ]
    callset_ht = functools.reduce(
        (lambda ht1, ht2: ht1.union(ht2)),
        callset_hts,
    )
    return callset_ht.distinct()


def union_callset_mts(callset_mts):
    """Merge multiple callset matrix tables into a single matrix table.

    Combines callset matrix tables from multiple projects by unioning the column
    dimension (samples/individuals). Uses an outer join on rows (variants) to
    preserve all unique variants across all callsets, with missing genotypes
    filled in as appropriate. Row fields are deduplicated by keeping only the
    left table's row metadata.

    Args:
        callset_mts: A sequence of Hail matrix tables to merge.

    Returns:
        A single matrix table containing all samples and variants from the input
        callsets, with row and entry fields merged.
    """
    return functools.reduce(
        (
            lambda mt1, mt2: mt1.union_cols(
                mt2,
                row_join_type='outer',
                drop_right_row_fields=True,
            )
        ),
        callset_mts,
    )


def get_callset_mt(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    callset_path: str,
    project_guids: list[str],
):
    callset_mts = [
        hl.read_matrix_table(
            remapped_and_subsetted_callset_path(
                reference_genome,
                dataset_type,
                callset_path,
                project_guid,
            ),
        )
        for project_guid in project_guids
    ]
    callset_mt = union_callset_mts(callset_mts)
    return callset_mt.distinct_by_row()


def get_additional_row_fields(
    mt: hl.MatrixTable,
    dataset_type: DatasetType,
    skip_check_sex_and_relatedness: bool,
):
    return {
        **(
            {'info.AF': hl.tarray(hl.tfloat64)}
            if not skip_check_sex_and_relatedness
            and dataset_type.check_sex_and_relatedness
            else {}
        ),
        # this field is never required, the pipeline
        # will run smoothly even in its absence, but
        # will trigger special handling if it is present.
        **(
            {'info.CALIBRATION_SENSITIVITY': hl.tarray(hl.tstr)}
            if hasattr(mt, 'info') and hasattr(mt.info, 'CALIBRATION_SENSITIVITY')
            else {}
        ),
        **(
            {'info.SEQR_INTERNAL_TRUTH_VID': hl.tstr}
            if dataset_type.re_key_by_seqr_internal_truth_vid
            else {}
        ),
    }
