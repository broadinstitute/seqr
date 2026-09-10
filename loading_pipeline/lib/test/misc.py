import os
import shutil

import numpy as np

from loading_pipeline.lib.core import DatasetType, ReferenceGenome, SampleType
from loading_pipeline.lib.paths import project_pedigree_path


def convert_ndarray_to_list(obj):
    if isinstance(obj, np.ndarray):
        return [convert_ndarray_to_list(item) for item in obj.tolist()]
    if isinstance(obj, dict):
        return {k: convert_ndarray_to_list(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_ndarray_to_list(item) for item in obj]
    return obj


def copy_project_pedigree_to_mocked_dir(
    pedigree_path: str,
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    sample_type: SampleType,
    project_guid: str,
):
    os.makedirs(
        os.path.dirname(
            project_pedigree_path(
                reference_genome,
                dataset_type,
                sample_type,
                project_guid,
            ),
        ),
        exist_ok=True,
    )
    shutil.copy2(
        pedigree_path,
        project_pedigree_path(
            reference_genome,
            dataset_type,
            sample_type,
            project_guid,
        ),
    )
