import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.misc.family_loading_failures import (
    get_families_failed_missing_samples,
)
from loading_pipeline.lib.misc.io import (
    import_pedigree,
    remap_pedigree_hash,
)
from loading_pipeline.lib.misc.pedigree import (
    parse_pedigree_ht_to_families,
    parse_pedigree_ht_to_remap_ht,
)
from loading_pipeline.lib.misc.sample_ids import remap_sample_ids, subset_samples
from loading_pipeline.lib.misc.validation import SeqrValidationError
from loading_pipeline.lib.paths import (
    project_pedigree_path,
    remapped_and_subsetted_callset_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import BaseLoadingRunParams
from loading_pipeline.lib.tasks.base.base_write import BaseWriteTask
from loading_pipeline.lib.tasks.files import GCSorLocalTarget, RawFileTask
from loading_pipeline.lib.tasks.sv.write_postprocessed_callset import (
    WritePostprocessedSvCallsetTask,
)
from loading_pipeline.lib.tasks.write_validation_errors_for_run import (
    with_persisted_validation_errors,
)


def format_failures(failed_families):
    return {
        f.family_guid: {
            'samples': sorted(f.samples.keys()),
            'reasons': reasons,
        }
        for f, reasons in failed_families.items()
    }


@luigi.util.inherits(BaseLoadingRunParams)
class WriteRemappedAndSubsettedSvCallsetTask(BaseWriteTask):
    def complete(self) -> luigi.Target:
        if not super().complete():
            return False
        mt = hl.read_matrix_table(self.output().path)
        return (
            bool(
                hl.eval(mt.globals.family_samples),
            )
            and len(hl.eval(mt.globals.remap_pedigree_hashes))
            == len(self.project_guids)
            and all(
                hl.eval(
                    mt.globals.remap_pedigree_hashes[i]
                    == remap_pedigree_hash(
                        project_pedigree_path(
                            self.reference_genome,
                            self.dataset_type,
                            self.sample_type,
                            project_guid,
                        ),
                    ),
                )
                for i, project_guid in enumerate(self.project_guids)
            )
        )

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            remapped_and_subsetted_callset_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
            ),
        )

    def requires(self) -> list[luigi.Task]:
        requirements = [
            self.clone(WritePostprocessedSvCallsetTask),
        ]
        requirements += [
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
        return requirements

    @with_persisted_validation_errors
    def create_table(self) -> hl.MatrixTable:
        callset_mt = hl.read_matrix_table(self.input()[0].path)

        # Remap, but only if the remap file is present!
        remap_ht = None
        project_families = {}
        for i, project_guid in enumerate(self.project_guids):
            pedigree_ht = import_pedigree(self.input()[i + 1].path)
            if 'remap_id' in pedigree_ht.row:
                project_remap_ht = parse_pedigree_ht_to_remap_ht(pedigree_ht)
                remap_ht = (
                    remap_ht.union(project_remap_ht)
                    if remap_ht is not None
                    else project_remap_ht
                )

            project_families[project_guid] = parse_pedigree_ht_to_families(pedigree_ht)

        if remap_ht is not None:
            callset_mt = remap_sample_ids(
                callset_mt,
                remap_ht,
            )

        families = {f for families in project_families.values() for f in families}
        families_failed_missing_samples = get_families_failed_missing_samples(
            callset_mt,
            families,
        )

        loadable_families = families - families_failed_missing_samples.keys()
        if not len(loadable_families):
            msg = 'All families failed validation checks'
            raise SeqrValidationError(
                msg,
                {
                    'failed_family_samples': {
                        'missing_samples': format_failures(
                            families_failed_missing_samples,
                        ),
                    },
                },
            )

        mt = subset_samples(
            callset_mt,
            hl.Table.parallelize(
                [
                    {'s': sample_id}
                    for family in loadable_families
                    for sample_id in family.samples
                ],
                hl.tstruct(s=hl.dtype('str')),
                key='s',
            ),
        )


        return mt.select_globals(
            remap_pedigree_hashes=[
                remap_pedigree_hash(
                    project_pedigree_path(
                        self.reference_genome,
                        self.dataset_type,
                        self.sample_type,
                        project_guid,
                    ),
                )
                for project_guid in self.project_guids
            ],
            family_samples=(
                {
                    f.family_guid: sorted(f.samples.keys())
                    for f in loadable_families
                    or hl.empty_dict(hl.tstr, hl.tarray(hl.tstr))
                }
            ),
            failed_family_samples=hl.Struct(
                missing_samples=(
                    format_failures(families_failed_missing_samples)
                    or hl.empty_dict(hl.tstr, hl.tdict(hl.tstr, hl.tarray(hl.tstr)))
                ),
            ),
            project_families={
                project_guid: sorted([f.family_guid for f in families])
                for project_guid, families in project_families.items()
            },
        )
