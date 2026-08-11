import math

import hail as hl
import hailtop.fs as hfs
import luigi
import luigi.util

from loading_pipeline.lib.annotations.fields import get_fields
from loading_pipeline.lib.annotations.misc import (
    annotate_formatting_annotation_enum_globals,
)
from loading_pipeline.lib.misc.callsets import get_callset_ht
from loading_pipeline.lib.misc.io import checkpoint, remap_pedigree_hash
from loading_pipeline.lib.misc.math import constrain
from loading_pipeline.lib.misc.vep import run_vep
from loading_pipeline.lib.paths import (
    new_variants_table_path,
    project_pedigree_path,
    valid_reference_dataset_path,
    variant_annotations_table_path,
)
from loading_pipeline.lib.reference_datasets.gencode.mapping_gene_ids import (
    load_gencode_ensembl_to_refseq_id,
    load_gencode_gene_symbol_to_gene_id,
)
from loading_pipeline.lib.reference_datasets.reference_dataset import ReferenceDataset
from loading_pipeline.lib.tasks.base.base_loading_run_params import (
    BaseLoadingRunParams,
)
from loading_pipeline.lib.tasks.base.base_write import BaseWriteTask
from loading_pipeline.lib.tasks.files import GCSorLocalTarget
from loading_pipeline.lib.tasks.write_metadata_for_run import (
    WriteMetadataForRunTask,
)

VARIANTS_PER_VEP_PARTITION = 1e3
MIN_PARTITIONS = 10
MAX_PARTITIONS = 10000
GENCODE_RELEASE = 42
GENCODE_FOR_VEP_RELEASE = 44


@luigi.util.inherits(BaseLoadingRunParams)
class WriteNewVariantsTableTask(BaseWriteTask):
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

        if self.dataset_type.has_gencode_ensembl_to_refseq_id_mapping(
            self.reference_genome,
        ):
            deps['gencode_ensembl_to_refseq_id_mapping'] = hl.literal(
                load_gencode_ensembl_to_refseq_id(GENCODE_FOR_VEP_RELEASE),
            )
        if self.dataset_type.has_gencode_gene_symbol_to_gene_id_mapping:
            deps['gencode_gene_symbol_to_gene_id_mapping'] = hl.literal(
                load_gencode_gene_symbol_to_gene_id(GENCODE_RELEASE),
            )
        return deps

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            new_variants_table_path(
                self.reference_genome,
                self.dataset_type,
                self.run_id,
            ),
        )

    def requires(self) -> list[luigi.Task]:
        return [
            self.clone(WriteMetadataForRunTask),
        ]

    def complete(self) -> bool:
        # NOTE: Special hack for ClickHouse migration tasks which
        # do not have a callset/projects to load.
        if len(self.project_guids) == 0:
            return super().complete()
        return super().complete() and hl.eval(
            hl.bind(
                lambda updates: hl.all(
                    [
                        updates.contains(
                            hl.Struct(
                                callset=self.callset_path,
                                project_guid=project_guid,
                                remap_pedigree_hash=remap_pedigree_hash(
                                    project_pedigree_path(
                                        self.reference_genome,
                                        self.dataset_type,
                                        self.sample_type,
                                        project_guid,
                                    ),
                                ),
                            ),
                        )
                        for project_guid in self.project_guids
                    ],
                ),
                hl.read_table(self.output().path).updates,
            ),
        )

    def create_table(self) -> hl.Table:
        callset_ht = get_callset_ht(
            self.reference_genome,
            self.dataset_type,
            self.callset_path,
            self.project_guids,
        )

        # 1) Identify new variants.
        if hfs.exists(
            variant_annotations_table_path(
                self.reference_genome,
                self.dataset_type,
            ),
        ):
            annotations_ht = hl.read_table(
                variant_annotations_table_path(
                    self.reference_genome,
                    self.dataset_type,
                ),
            )
            # Gracefully handle case for on-premises uses
            # where key_ field is not present and migration was not run.
            if not hasattr(annotations_ht, 'key_'):
                annotations_ht = annotations_ht.add_index(name='key_')
                annotations_ht = annotations_ht.annotate_globals(
                    max_key_=(annotations_ht.count() - 1),
                )
            curr_max_key_ = annotations_ht.index_globals().max_key_
            new_variants_ht = callset_ht.repartition(
                # Repartition this join to improve performance
                constrain(
                    callset_ht.n_partitions() * 100,
                    MIN_PARTITIONS,
                    MAX_PARTITIONS,
                ),
            ).anti_join(annotations_ht)
        else:
            curr_max_key_ = -1
            new_variants_ht = callset_ht

        # Annotate new variants with VEP.
        # Note about the repartition: our work here is cpu/memory bound and
        # proportional to the number of new variants.  Our default partitioning
        # will under-partition in that regard, so we split up our work
        # with a partitioning scheme local to this task.
        new_variants_count = new_variants_ht.count()
        new_variants_ht = new_variants_ht.repartition(
            constrain(
                math.ceil(new_variants_count / VARIANTS_PER_VEP_PARTITION),
                MIN_PARTITIONS,
                MAX_PARTITIONS,
            ),
        )
        new_variants_ht = run_vep(
            new_variants_ht,
            self.dataset_type,
            self.reference_genome,
        )
        # Adding an arbitrary checkpoint here, seems to help
        new_variants_ht, _ = checkpoint(new_variants_ht)

        # An additional call to "distinct()" as a safety measure.
        # At least one case a duplicate variants has slipped through
        # this method, with the best hypothesis being that
        # the combination of VEP/repartition is potentially unsafe.
        new_variants_ht = new_variants_ht.distinct()

        # Select down to the formatting annotations fields and
        # any reference dataset collection annotations.
        new_variants_ht = new_variants_ht.select(
            **get_fields(
                new_variants_ht,
                self.dataset_type.formatting_annotation_fns(self.reference_genome),
                **self.annotation_dependencies,
                **self.param_kwargs,
            ),
        )

        # Add serial integer index
        new_variants_ht = new_variants_ht.add_index(name='key_')
        new_variants_ht = new_variants_ht.transmute(
            key_=new_variants_ht.key_ + curr_max_key_ + 1,
        )
        new_variants_ht = annotate_formatting_annotation_enum_globals(
            new_variants_ht,
            self.reference_genome,
            self.dataset_type,
        )
        return new_variants_ht.annotate_globals(
            updates={
                hl.Struct(
                    callset=self.callset_path,
                    project_guid=project_guid,
                    remap_pedigree_hash=remap_pedigree_hash(
                        project_pedigree_path(
                            self.reference_genome,
                            self.dataset_type,
                            self.sample_type,
                            project_guid,
                        ),
                    ),
                )
                for project_guid in self.project_guids
            },
        )
