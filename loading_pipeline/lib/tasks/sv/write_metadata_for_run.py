import luigi
import luigi.util
import pandas as pd

from loading_pipeline.lib.paths import (
    project_pedigree_path,
)
from loading_pipeline.lib.tasks.base.base_write_metadata_for_run import (
    BaseWriteMetadataForRunTask,
)
from loading_pipeline.lib.tasks.files import RawFileTask


class WriteMetadataForSvRunTask(BaseWriteMetadataForRunTask):
    def requires(self) -> list[luigi.Task]:
        return [
            RawFileTask(
                project_pedigree_path(
                    self.reference_genome,
                    self.dataset_type,
                    self.sample_type,
                    project_guid,
                ),
            )
            for project_guid in self.project_guids
        ]

    def populate_metadata_families(self, metadata_json) -> None:
        metadata_json['remap_ids'] = {}
        metadata_json['project_families'] = {}
        metadata_json['male_sample_ids'] = []
        for i, target in enumerate(self.input()):
            df = pd.read_csv(target.path, sep='\t')
            family_samples = (
                df.groupby('Family_GUID')['Individual_ID'].apply(list).to_dict()
            )
            metadata_json['family_samples'].update(family_samples)
            metadata_json['project_families'][self.project_guids[i]] = sorted(
                family_samples.keys(),
            )
            metadata_json['male_sample_ids'] += df.loc[
                df['Sex'] == 'M',
                'Individual_ID',
            ].to_list()
            if 'VCF_ID' in df.columns:
                remap_df = df[df['VCF_ID'].notnull() & (df['VCF_ID'] != '')]
                metadata_json['remap_ids'].update(
                    remap_df.set_index('VCF_ID')['Individual_ID'].to_dict(),
                )
