import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.misc.io import import_parquet
from loading_pipeline.lib.paths import (
    existing_variants_parquet_path,
    new_variants_parquet_path,
    remapped_and_subsetted_callset_path,
    valid_reference_dataset_path,
)
from loading_pipeline.lib.reference_datasets.gencode.mapping_gene_ids import (
    load_gencode_gene_symbol_to_gene_id,
)
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.base.base_write_parquet import BaseWriteParquetTask
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.write_existing_variants_parquet import (
    WriteExistingVariantsParquetTask,
)
from loading_pipeline.lib.tasks.sv.write_metadata_for_run import (
    WriteMetadataForSvRunTask,
)

GENCODE_RELEASE = 42


@luigi.util.inherits(BaseLoadingRunParams)
class WriteNewSvVariantsParquetTask(BaseWriteParquetTask):
    @property
    def annotation_dependencies(self) -> dict[str, hl.Table]:
        deps = {}
        for reference_dataset in ReferenceDataset:
            if (
                reference_dataset.formatting_annotation
                and self.dataset_type
                in reference_dataset.dataset_types(self.reference_genome)
            ):
                deps[f'{reference_dataset.value}_ht'] = hl.read_table(
                    valid_reference_dataset_path(
                        self.reference_genome,
                        reference_dataset,
                    ),
                )

        if self.dataset_type.has_gencode_gene_symbol_to_gene_id_mapping:
            deps['gencode_gene_symbol_to_gene_id_mapping'] = hl.literal(
                load_gencode_gene_symbol_to_gene_id(GENCODE_RELEASE),
            )
        return deps

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            new_variants_parquet_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def requires(self) -> list[luigi.Task]:
        return [
            self.clone(WriteMetadataForSvRunTask),
            self.clone(WriteExistingVariantsParquetTask),
        ]

    def create_table(self) -> hl.Table:
        callset_ht = hl.read_matrix_table(
            remapped_and_subsetted_callset_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ),
        ).rows()

        # 1) Identify new variants.
        annotations_ht = import_parquet(
            existing_variants_parquet_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
            self.reference_genome,
            self.dataset_type,
        )
        curr_max_key_ = annotations_ht.aggregate(hl.agg.max(annotations_ht.key_)) or -1
        new_variants_ht = callset_ht.anti_join(annotations_ht)

        # Run liftover
        new_variants_ht = new_variants_ht.annotate(
            **{
                name: fn(new_variants_ht)
                for name, fn in self.dataset_type.liftover_annotation_fns(
                    self.reference_genome,
                ).items()
            },
        )

        # Select down to the formatting annotations fields and
        # any reference dataset collection annotations.
        new_variants_ht = new_variants_ht.select(
            **{
                name: fn(
                    new_variants_ht,
                    **self.annotation_dependencies,
                    **self.param_kwargs,
                )
                for name, fn in self.dataset_type.formatting_annotation_fns(
                    self.reference_genome,
                ).items()
            },
        )

        # Add serial integer index
        new_variants_ht = new_variants_ht.add_index(name='key_')
        new_variants_ht = new_variants_ht.transmute(
            key_=new_variants_ht.key_ + curr_max_key_ + 1,
        )
        new_variants_ht = new_variants_ht.key_by()
        return new_variants_ht.select(
            'key_',
            *self.dataset_type.variants_export_field_names(self.reference_genome),
        )
