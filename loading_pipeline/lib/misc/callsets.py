import hail as hl

from loading_pipeline.lib.core import DatasetType


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
