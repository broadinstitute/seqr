import json

import hail as hl
import hailtop.fs as hfs
import luigi
import luigi.util

from loading_pipeline.lib.core import FeatureFlag
from loading_pipeline.lib.paths import (
    sample_qc_json_path,
)
from loading_pipeline.lib.tasks.base.base_write_metadata_for_run import (
    BaseWriteMetadataForRunTask,
)
from loading_pipeline.lib.tasks.write_remapped_and_subsetted_callset import (
    WriteRemappedAndSubsettedCallsetTask,
)
from loading_pipeline.lib.tasks.write_sample_qc_json import WriteSampleQCJsonTask


class WriteMetadataForRunTask(BaseWriteMetadataForRunTask):
    priority = 2

    def requires(self) -> list[luigi.Task]:
        requirements = [self.clone(WriteRemappedAndSubsettedCallsetTask)]
        if (
            FeatureFlag.EXPECT_TDR_METRICS
            and not self.skip_expect_tdr_metrics
            and self.dataset_type.expect_tdr_metrics(
                self.reference_genome,
            )
        ):
            requirements = [
                *requirements,
                self.clone(WriteSampleQCJsonTask),
            ]
        return requirements

    def populate_metadata_families(self, metadata_json) -> None:
        callset_mt = hl.read_matrix_table(self.input()[0].path)
        collected_globals = callset_mt.globals.collect()[0]
        metadata_json['family_samples'] = collected_globals['family_samples']
        sample_qc_loadable_samples = {
            sample
            for family_samples in collected_globals['family_samples'].values()
            for sample in family_samples
        }
        for key in [
            'missing_samples',
            'relatedness_check',
            'sex_check',
            'ploidy_check',
        ]:
            metadata_json['failed_family_samples'][key] = collected_globals[
                'failed_family_samples'
            ][key]
            sample_qc_loadable_samples = {
                *{
                    sample
                    for meta in collected_globals['failed_family_samples'][key].values()
                    for sample in meta['samples']
                },
                *sample_qc_loadable_samples,
            }
        if (
            FeatureFlag.EXPECT_TDR_METRICS
            and not self.skip_expect_tdr_metrics
            and self.dataset_type.expect_tdr_metrics(
                self.reference_genome,
            )
        ):
            with hfs.open(
                sample_qc_json_path(
                    self.reference_genome,
                    self.dataset_type,
                    self.callset_path,
                ),
            ) as f:
                metadata_json['sample_qc'] = {
                    k: v
                    for k, v in json.load(f).items()
                    if k in sample_qc_loadable_samples
                }
