import hail as hl
import hailtop.fs as hfs
import luigi

from loading_pipeline.lib.core.feature_flag import FeatureFlag
from loading_pipeline.lib.methods.sex_check import compute_sex_check_ht
from loading_pipeline.lib.misc.io import import_imputed_sex
from loading_pipeline.lib.paths import (
    imported_callset_path,
    sex_check_table_path,
    tdr_metrics_dir,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import BaseLoadingRunParams
from loading_pipeline.lib.tasks.base.base_write import BaseWriteTask
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.write_postprocessed_callset import (
    WritePostprocessedCallsetTask,
)
from loading_pipeline.lib.tasks.write_tdr_metrics_files import WriteTDRMetricsFilesTask


@luigi.util.inherits(BaseLoadingRunParams)
class WriteSexCheckTableTask(BaseWriteTask):
    callset_path = luigi.Parameter()

    @property
    def predicted_sex_from_tdr(self):
        # complicated enough to need a helper :/
        return (
            FeatureFlag.EXPECT_TDR_METRICS
            and not self.skip_expect_tdr_metrics
            and self.dataset_type.expect_tdr_metrics(
                self.reference_genome,
            )
        )

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            sex_check_table_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ),
        )

    def requires(self) -> list[luigi.Task]:
        requirements = []
        if self.predicted_sex_from_tdr:
            requirements = [
                *requirements,
                self.clone(WriteTDRMetricsFilesTask),
            ]
        else:
            requirements = [
                *requirements,
                self.clone(WritePostprocessedCallsetTask),
            ]
        return requirements

    def create_table(self) -> hl.Table:
        ht = None
        if self.predicted_sex_from_tdr:
            for tdr_metrics_file in hfs.ls(
                tdr_metrics_dir(self.reference_genome, self.dataset_type),
            ):
                if not ht:
                    ht = import_imputed_sex(tdr_metrics_file.path)
                    continue
                ht = ht.union(import_imputed_sex(tdr_metrics_file.path))
        else:
            mt = hl.read_matrix_table(
                imported_callset_path(
                    self.reference_genome,
                    self.dataset_type,
                    self.callset_path,
                ),
            )
            ht = compute_sex_check_ht(mt)
        return ht
