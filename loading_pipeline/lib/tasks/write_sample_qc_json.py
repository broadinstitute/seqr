import json
from collections import defaultdict

import hail as hl
import hailtop.fs as hfs
import luigi
import luigi.util
import onnx

from loading_pipeline.lib.methods.sample_qc import call_sample_qc
from loading_pipeline.lib.misc.callsets import get_callset_mt
from loading_pipeline.lib.misc.io import checkpoint, import_tdr_qc_metrics
from loading_pipeline.lib.paths import (
    ancestry_model_rf_path,
    sample_qc_json_path,
    tdr_metrics_dir,
)
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset
from loading_pipeline.lib.tasks.base.base_loading_run_params import BaseLoadingRunParams
from loading_pipeline.lib.tasks.files import GCSorLocalTarget, RawFileTask
from loading_pipeline.lib.tasks.reference_data.updated_reference_dataset import (
    UpdatedReferenceDatasetTask,
)
from loading_pipeline.lib.tasks.write_remapped_and_subsetted_callset import (
    WriteRemappedAndSubsettedCallsetTask,
)
from loading_pipeline.lib.tasks.write_tdr_metrics_files import WriteTDRMetricsFilesTask


@luigi.util.inherits(BaseLoadingRunParams)
class WriteSampleQCJsonTask(luigi.Task):
    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            sample_qc_json_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ),
        )

    def requires(self):
        remapped_and_subsetted_callsets = [
            self.clone(
                WriteRemappedAndSubsettedCallsetTask,
                project_i=i,
            )
            for i in range(len(self.project_guids))
        ]
        return [
            self.clone(WriteTDRMetricsFilesTask),
            self.clone(
                UpdatedReferenceDatasetTask,
                reference_dataset=ReferenceDataset.gnomad_qc,
            ),
            RawFileTask(ancestry_model_rf_path()),
            *remapped_and_subsetted_callsets,
        ]

    def run(self):
        callset_mt = get_callset_mt(
            self.reference_genome,
            self.dataset_type,
            self.callset_path,
            self.project_guids,
        )
        callset_mt, _ = checkpoint(callset_mt)
        tdr_metrics_ht = None
        for tdr_metrics_file in hfs.ls(
            tdr_metrics_dir(self.reference_genome, self.dataset_type),
        ):
            if not tdr_metrics_ht:
                tdr_metrics_ht = import_tdr_qc_metrics(tdr_metrics_file.path)
                continue
            tdr_metrics_ht = tdr_metrics_ht.union(
                import_tdr_qc_metrics(tdr_metrics_file.path),
            )
        pop_pca_loadings_ht = hl.read_table(self.input()[1].path)
        with hfs.open(self.input()[2].path, 'rb') as f:
            ancestry_rf_model = onnx.load(f)
        callset_mt = call_sample_qc(
            callset_mt,
            tdr_metrics_ht,
            pop_pca_loadings_ht,
            ancestry_rf_model,
            self.sample_type,
        )
        ht = callset_mt.cols()
        sample_qc_dict = defaultdict(dict)
        for row in ht.flatten().collect():
            r = dict(row)
            sample_id = r.pop('s')
            for field, value in r.items():
                sample_qc_dict[sample_id][field] = value

        with self.output().open('w') as f:
            json.dump(sample_qc_dict, f)
