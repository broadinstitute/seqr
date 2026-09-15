import hashlib
import os

import hailtop.fs as hfs

from loading_pipeline.lib.core import (
    DatasetType,
    Env,
    ReferenceGenome,
    SampleType,
)
from loading_pipeline.lib.reference_datasets.reference_dataset import (
    ReferenceDataset,
)


def pipeline_prefix(
    root: str,
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
) -> str:
    return os.path.join(
        root,
        reference_genome.value,
        dataset_type.value,
    )


def _v03_reference_dataset_prefix(
    root: str,
    reference_genome: ReferenceGenome,
) -> str:
    return os.path.join(
        root,
        reference_genome.value,
    )


def _callset_path_hash(callset_path: str) -> str:
    # Include the most recent modified time of any
    # of the callset shards if they exist.
    try:
        # hfs.ls throws FileNotFoundError if a non-wildcard is passed
        # but not found, but does not throw if a wildcard is passed and
        # there are no results.
        shards = hfs.ls(callset_path)
        if not shards:
            key = callset_path
        else:
            # f.modification_time is None for directories
            key = callset_path + str(
                sum((f.size if f.size else 0) for f in shards),
            )
    except FileNotFoundError:
        key = callset_path
    return hashlib.sha256(
        key.encode('utf8'),
    ).hexdigest()


def tdr_metrics_dir(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
) -> str:
    return os.path.join(
        pipeline_prefix(
            Env.LOADING_DATASETS_DIR,
            reference_genome,
            dataset_type,
        ),
        'tdr_metrics',
    )


def tdr_metrics_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    bq_table_name: str,
) -> str:
    return os.path.join(
        tdr_metrics_dir(reference_genome, dataset_type),
        f'{bq_table_name}.tsv',
    )


def imported_callset_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    callset_path: str,
) -> str:
    return os.path.join(
        pipeline_prefix(
            Env.LOADING_DATASETS_DIR,
            reference_genome,
            dataset_type,
        ),
        'imported_callsets',
        f'{_callset_path_hash(callset_path)}.mt',
    )


def postprocessed_callset_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    callset_path: str,
) -> str:
    return os.path.join(
        pipeline_prefix(
            Env.LOADING_DATASETS_DIR,
            reference_genome,
            dataset_type,
        ),
        'postprocessed_callsets',
        f'{_callset_path_hash(callset_path)}.mt',
    )


def validation_errors_for_run_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
) -> str:
    return os.path.join(
        runs_path(
            reference_genome,
            dataset_type,
        ),
        run_id,
        'validation_errors.json',
    )


def metadata_for_run_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
) -> str:
    return os.path.join(
        runs_path(
            reference_genome,
            dataset_type,
        ),
        run_id,
        'metadata.json',
    )


def relatedness_check_table_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    callset_path: str,
) -> str:
    return os.path.join(
        pipeline_prefix(
            Env.LOADING_DATASETS_DIR,
            reference_genome,
            dataset_type,
        ),
        'relatedness_check',
        f'{_callset_path_hash(callset_path)}.ht',
    )


def relatedness_check_tsv_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    callset_path: str,
) -> str:
    return os.path.join(
        pipeline_prefix(
            Env.LOADING_DATASETS_DIR,
            reference_genome,
            dataset_type,
        ),
        'relatedness_check',
        f'{_callset_path_hash(callset_path)}.tsv',
    )


def sample_qc_json_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    callset_path: str,
) -> str:
    return os.path.join(
        pipeline_prefix(
            Env.LOADING_DATASETS_DIR,
            reference_genome,
            dataset_type,
        ),
        'sample_qc',
        f'{_callset_path_hash(callset_path)}.json',
    )


def remapped_and_subsetted_callset_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    callset_path: str,
) -> str:
    return os.path.join(
        pipeline_prefix(
            Env.LOADING_DATASETS_DIR,
            reference_genome,
            dataset_type,
        ),
        'remapped_and_subsetted_callsets',
        f'{_callset_path_hash(callset_path)}.mt',
    )


def runs_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
) -> str:
    return os.path.join(
        pipeline_prefix(
            Env.PIPELINE_DATA_DIR,
            reference_genome,
            dataset_type,
        ),
        'runs',
    )


def sex_check_table_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    callset_path: str,
) -> str:
    return os.path.join(
        pipeline_prefix(
            Env.LOADING_DATASETS_DIR,
            reference_genome,
            dataset_type,
        ),
        'sex_check',
        f'{_callset_path_hash(callset_path)}.ht',
    )


def valid_reference_dataset_path(
    reference_genome: ReferenceGenome,
    reference_dataset: ReferenceDataset,
) -> str | None:
    return os.path.join(
        _v03_reference_dataset_prefix(
            Env.REFERENCE_DATASETS_DIR,
            reference_genome,
        ),
        reference_dataset.value,
        f'{reference_dataset.version(reference_genome)}.ht',
    )


def ancestry_model_rf_path() -> str:
    return os.path.join(
        _v03_reference_dataset_prefix(
            Env.REFERENCE_DATASETS_DIR,
            ReferenceGenome.GRCh38,
        ),
        DatasetType.SNV_INDEL,
        'ancestry_imputation_model.onnx',
    )


def new_entries_parquet_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
) -> str:
    return os.path.join(
        runs_path(
            reference_genome,
            dataset_type,
        ),
        run_id,
        'new_entries.parquet',
    )


def new_variant_details_parquet_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
) -> str:
    return os.path.join(
        runs_path(
            reference_genome,
            dataset_type,
        ),
        run_id,
        'new_variant_details.parquet',
    )


def new_variants_parquet_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
) -> str:
    return os.path.join(
        runs_path(
            reference_genome,
            dataset_type,
        ),
        run_id,
        'new_variants.parquet',
    )


def existing_variants_parquet_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
) -> str:
    return os.path.join(
        runs_path(
            reference_genome,
            dataset_type,
        ),
        run_id,
        'existing_variants.parquet',
    )


def new_variants_table_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
) -> str:
    return os.path.join(
        runs_path(
            reference_genome,
            dataset_type,
        ),
        run_id,
        'new_variants.ht',
    )


def project_pedigree_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    sample_type: SampleType,
    project_guid: str,
) -> str:
    return os.path.join(
        pipeline_prefix(
            Env.LOADING_DATASETS_DIR,
            reference_genome,
            dataset_type,
        ),
        'pedigrees',
        sample_type.value,
        f'{project_guid}_pedigree.tsv',
    )


def loading_pipeline_queue_dir() -> str:
    """
    Returns the directory where loading pipeline requests are queued.
    """
    return os.path.join(
        Env.LOCAL_DISK_MOUNT_DIR,
        'loading_pipeline_queue',
    )


# https://en.wikipedia.org/wiki/Dead_letter_queue
def loading_pipeline_deadletter_queue_dir() -> str:
    return os.path.join(
        Env.LOCAL_DISK_MOUNT_DIR,
        'loading_pipeline_deadletter_queue',
    )


def loading_pipeline_queue_path(run_id: str) -> str:
    """
    Returns a new path for a loading pipeline queue request file.
    """
    return os.path.join(
        loading_pipeline_queue_dir(),
        f'request_{run_id}.json',
    )


def loading_pipeline_deadletter_queue_path(run_id: str) -> str:
    """
    Returns a new path for a loading pipeline queue request file.
    """
    return os.path.join(
        loading_pipeline_deadletter_queue_dir(),
        f'request_{run_id}.json',
    )


def pipeline_run_success_file_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
) -> str:
    return os.path.join(
        runs_path(
            reference_genome,
            dataset_type,
        ),
        run_id,
        '_SUCCESS',
    )


def clickhouse_load_success_file_path(
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    run_id: str,
) -> str:
    return os.path.join(
        runs_path(
            reference_genome,
            dataset_type,
        ),
        run_id,
        '_CLICKHOUSE_LOAD_SUCCESS',
    )


def reference_dataset_parquet(
    reference_genome: ReferenceGenome,
    reference_dataset: ReferenceDataset,
) -> str:
    return os.path.join(
        Env.REFERENCE_DATASETS_DIR,
        reference_genome.value,
        reference_dataset.value,
        f'{reference_dataset.version(reference_genome)}.parquet',
    )
