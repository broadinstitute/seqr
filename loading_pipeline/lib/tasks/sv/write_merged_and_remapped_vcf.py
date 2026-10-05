import luigi
import luigi.util
import pandas as pd

from loading_pipeline.lib.paths import (
    imported_callset_path,
    project_pedigree_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.files import GCSorLocalTarget, RawFileTask


@luigi.util.inherits(BaseLoadingRunParams)
class WriteMergedAndRemappedSvVcf(luigi.Task):
    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            imported_callset_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ).replace('.mt', '.merged.vcf.gz'),
        )

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

    def run(self) -> None:
        family_samples = {}
        remap_ids = {}
        for target in self.input():
            df = pd.read_csv(target.path, sep='\t')
            family_samples.update(df.groupby('Family_GUID')['Individual_ID'].apply(list).to_dict())
            if 'VCF_ID' in df.columns:
                remap_df = df[df['VCF_ID'].notnull() & (df['VCF_ID'] != '')]
                remap_ids.update(remap_df.set_index('VCF_ID')['Individual_ID'].to_dict())

        sample_file_tasks = [
            RawFileTask(self.callset_path.replace('*', sample_id))
            for samples in family_samples.values() for sample_id in samples
        ]
        yield sample_file_tasks

        vcf_paths = [task.output().path for task in sample_file_tasks]
        out_file = self.output().path
