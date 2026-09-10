from collections.abc import Callable
from typing import Any

import luigi
import luigi.execution_summary

from loading_pipeline.api.model import (
    DeleteFamiliesRequest,
    LoadingPipelineRequest,
    PipelineRunnerRequest,
    RebuildGtStatsRequest,
    RefreshClickhouseReferenceDataRequest,
)
from loading_pipeline.lib.core import DatasetType
from loading_pipeline.lib.logger import get_logger
from loading_pipeline.lib.misc.clickhouse import (
    ClickhouseReferenceDataset,
    delete_family_guids,
    rebuild_gt_stats,
    refresh_clickhouse_reference_data,
)
from loading_pipeline.lib.tasks.load_clickhouse_entries import (
    LoadClickhouseEntries,
)

logger = get_logger(__name__)


def run_loading_pipeline(
    lpr: LoadingPipelineRequest,
    run_id: str,
    local_scheduler: bool,
    *_: Any,
):
    luigi_task_result = luigi.build(
        [
            LoadClickhouseEntries(
                run_id=run_id,
                **lpr.model_dump(exclude='request_type'),
            ),
        ],
        detailed_summary=True,
        local_scheduler=local_scheduler,
    )
    if luigi_task_result.status in {
        luigi.execution_summary.LuigiStatusCode.SUCCESS,
        luigi.execution_summary.LuigiStatusCode.SUCCESS_WITH_RETRY,
    }:
        return
    raise RuntimeError(luigi_task_result.status.value[1])


def run_delete_families(dpr: DeleteFamiliesRequest, run_id: str, *_: Any):
    for dataset_type in dpr.dataset_types:
        for reference_genome in dataset_type.reference_genomes:
            delete_family_guids(
                reference_genome,
                dataset_type,
                run_id,
                **dpr.model_dump(exclude={'request_type', 'dataset_types'}),
            )


def run_rebuild_gt_stats(rgsr: RebuildGtStatsRequest, run_id: str, *_: Any):
    for dataset_type in DatasetType:
        for reference_genome in dataset_type.reference_genomes:
            rebuild_gt_stats(
                reference_genome,
                dataset_type,
                run_id,
                **rgsr.model_dump(exclude='request_type'),
            )


def run_refresh_clickhouse_reference_data(
    rcrdr: RefreshClickhouseReferenceDataRequest,
    run_id: str,
    *_: Any,
):
    for dataset_type in DatasetType:
        for reference_genome in dataset_type.reference_genomes:
            reference_dataset = rcrdr.reference_dataset
            if (
                reference_dataset
                not in ClickhouseReferenceDataset.for_reference_genome_dataset_type(
                    reference_genome,
                    dataset_type,
                )
            ):
                continue
            refresh_clickhouse_reference_data(
                reference_genome,
                dataset_type,
                run_id,
                **rcrdr.model_dump(exclude='request_type'),
            )


REQUEST_HANDLER_MAP: dict[
    type[PipelineRunnerRequest],
    Callable[[PipelineRunnerRequest, str, ...], None],
] = {
    LoadingPipelineRequest: run_loading_pipeline,
    DeleteFamiliesRequest: run_delete_families,
    RebuildGtStatsRequest: run_rebuild_gt_stats,
    RefreshClickhouseReferenceDataRequest: run_refresh_clickhouse_reference_data,
}
