from typing import Literal

import hailtop.fs as hfs
from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    conint,
    field_validator,
    root_validator,
)

from loading_pipeline.lib.core import DatasetType, ReferenceGenome, SampleType
from loading_pipeline.lib.misc.clickhouse import ClickhouseReferenceDataset
from loading_pipeline.lib.misc.validation import ALL_VALIDATIONS, SKIPPABLE_VALIDATIONS

MAX_LOADING_PIPELINE_ATTEMPTS = 5
STRINGIFIED_SKIPPABLE_VALIDATIONS = [f.__name__ for f in SKIPPABLE_VALIDATIONS]
VALID_FILE_TYPES = ['vcf', 'vcf.gz', 'vcf.bgz', 'mt']


class PipelineRunnerRequest(BaseModel):
    request_type: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.model_fields['request_type'].default = cls.__name__


class LoadingPipelineRequest(PipelineRunnerRequest):
    attempt_id: conint(ge=0, le=MAX_LOADING_PIPELINE_ATTEMPTS - 1) = 0
    callset_path: str
    project_guids: list[str] = Field(
        min_length=1,
        frozen=True,
        validation_alias=AliasChoices('project_guids', 'projects_to_run'),
    )
    sample_type: SampleType
    reference_genome: ReferenceGenome
    dataset_type: DatasetType
    skip_check_sex_and_relatedness: bool = False
    skip_expect_tdr_metrics: bool = False
    validations_to_skip: list[Literal[*STRINGIFIED_SKIPPABLE_VALIDATIONS]] = []

    def incr_attempt(self):
        if self.attempt_id == (MAX_LOADING_PIPELINE_ATTEMPTS - 1):
            return False
        self.attempt_id += 1
        return True

    @field_validator('validations_to_skip')
    @classmethod
    def must_be_known_validation(cls, validations_to_skip):
        for v in validations_to_skip:
            if v not in set(STRINGIFIED_SKIPPABLE_VALIDATIONS):
                msg = f'{v} is not a valid validator'
                raise ValueError(msg)
        return validations_to_skip

    @root_validator(
        pre=True,
    )  # the root validator runs before Pydantic parses or coerces field values.
    @classmethod
    def override_all_validations(cls, values):
        if values.get('validations_to_skip') == [
            ALL_VALIDATIONS,
        ]:
            values['validations_to_skip'] = STRINGIFIED_SKIPPABLE_VALIDATIONS
        return values

    @field_validator('callset_path')
    @classmethod
    def check_valid_callset_path(cls, callset_path: str) -> str:
        if not any(callset_path.endswith(file_type) for file_type in VALID_FILE_TYPES):
            msg = 'callset_path must be a VCF or a Hail Matrix Table'
            raise ValueError(msg)
        if '*' in callset_path and not hfs.ls(
            callset_path,
        ):  # note that hfs.ls throws an exception if it cannot find a non-wildcard path
            msg = 'callset_path must point to a shard pattern that exists'
            raise ValueError(msg)
        if '*' not in callset_path and not hfs.exists(callset_path):
            msg = 'callset_path must point to a file that exists'
            raise ValueError(msg)
        return callset_path


class DeleteFamiliesRequest(PipelineRunnerRequest):
    project_guid: str
    family_guids: list[str] = Field(
        min_length=1,
        frozen=True,
    )
    dataset_types: list[DatasetType] = Field(default_factory=lambda: list(DatasetType))


class RebuildGtStatsRequest(PipelineRunnerRequest):
    project_guids: list[str] = Field(
        min_length=1,
        frozen=True,
    )


class RefreshClickhouseReferenceDataRequest(PipelineRunnerRequest):
    reference_dataset: ClickhouseReferenceDataset
