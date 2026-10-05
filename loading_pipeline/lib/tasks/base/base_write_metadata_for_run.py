import json

import luigi
import luigi.util

from loading_pipeline.lib.paths import (
    metadata_for_run_path,
    relatedness_check_tsv_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget


@luigi.util.inherits(BaseLoadingRunParams)
class BaseWriteMetadataForRunTask(luigi.Task):
    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            metadata_for_run_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def run(self) -> None:
        metadata_json = {
            'callsets': [self.callset_path],
            'run_id': self.run_id,
            'sample_type': self.sample_type.value,
            'project_guids': self.project_guids,
            'family_samples': {},
            'failed_family_samples': {
                'missing_samples': {},
                'relatedness_check': {},
                'sex_check': {},
                'ploidy_check': {},
            },
            'relatedness_check_file_path': relatedness_check_tsv_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ),
            'sample_qc': {},
        }
        self.populate_metadata_families(metadata_json)
        if not metadata_json['family_samples']:
            msg = 'Found no loadable families in the callset.'
            raise RuntimeError(msg)
        empty_families = [
            family_guid
            for family_guid, samples in metadata_json['family_samples'].items()
            if not samples
        ]
        if empty_families:
            msg = f'Found families with no loadable samples: {sorted(empty_families)}'
            raise RuntimeError(msg)
        with self.output().open('w') as f:
            json.dump(metadata_json, f)

    def populate_metadata_families(self, metadata_json) -> None:
        raise NotImplementedError
