import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.tasks.base.base_write_metadata_for_run import BaseWriteMetadataForRunTask
from loading_pipeline.lib.tasks.sv.write_remapped_and_subsetted_callset import (
    WriteRemappedAndSubsettedSvCallsetTask,
)

class WriteMetadataForSvRunTask(BaseWriteMetadataForRunTask):
    def requires(self) -> list[luigi.Task]:
        return [self.clone(WriteRemappedAndSubsettedSvCallsetTask)]

    def populate_metadata_families(self, metadata_json) -> None:
        callset_mt = hl.read_matrix_table(self.input()[0].path)
        collected_globals = callset_mt.globals.collect()[0]
        metadata_json['family_samples'] = collected_globals['family_samples']
        metadata_json['failed_family_samples']['missing_samples'] = collected_globals[
            'failed_family_samples'
        ]['missing_samples']
