import hail as hl
import luigi
import luigi.util

from loading_pipeline.lib.core.feature_flag import FeatureFlag
from loading_pipeline.lib.misc.family_loading_failures import (
    get_families_failed_imputed_sex_ploidy,
    get_families_failed_missing_samples,
    get_families_failed_relatedness_check,
    get_families_failed_sex_check,
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
from loading_pipeline.lib.misc.sv import overwrite_male_non_par_calls
from loading_pipeline.lib.misc.validation import SeqrValidationError
from loading_pipeline.lib.paths import (
    project_pedigree_path,
    relatedness_check_table_path,
    remapped_and_subsetted_callset_path,
)
from loading_pipeline.lib.tasks.base.base_loading_run_params import BaseLoadingRunParams
from loading_pipeline.lib.tasks.base.base_write import BaseWriteTask
from loading_pipeline.lib.tasks.files import GCSorLocalTarget, RawFileTask
from loading_pipeline.lib.tasks.validate_callset import ValidateCallsetTask
from loading_pipeline.lib.tasks.write_relatedness_check_tsv import (
    WriteRelatednessCheckTsvTask,
)
from loading_pipeline.lib.tasks.write_sex_check_table import WriteSexCheckTableTask
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
class WriteRemappedAndSubsettedCallsetTask(BaseWriteTask):
    project_i = luigi.IntParameter()

    def complete(self) -> luigi.Target:
        if not super().complete():
            return False
        mt = hl.read_matrix_table(self.output().path)
        return bool(
            hl.eval(mt.globals.family_samples),
        ) and hl.eval(
            mt.globals.remap_pedigree_hash
            == remap_pedigree_hash(
                project_pedigree_path(
                    self.reference_genome,
                    self.dataset_type,
                    self.sample_type,
                    self.project_guids[self.project_i],
                ),
            ),
        )

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            remapped_and_subsetted_callset_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
                self.project_guids[self.project_i],
            ),
        )

    def requires(self) -> list[luigi.Task]:
        requirements = [
            self.clone(ValidateCallsetTask),
            RawFileTask(
                project_pedigree_path(
                    self.reference_genome,
                    self.dataset_type,
                    self.sample_type,
                    self.project_guids[self.project_i],
                ),
            ),
        ]
        if (
            FeatureFlag.CHECK_SEX_AND_RELATEDNESS
            and self.dataset_type.check_sex_and_relatedness
            and not self.skip_check_sex_and_relatedness
        ):
            requirements = [
                *requirements,
                self.clone(WriteRelatednessCheckTsvTask),
                self.clone(WriteSexCheckTableTask),
            ]
        return requirements

    @with_persisted_validation_errors
    def create_table(self) -> hl.MatrixTable:
        callset_mt = hl.read_matrix_table(self.input()[0].path)
        pedigree_ht = import_pedigree(self.input()[1].path)

        # Remap, but only if the remap file is present!
        remap_lookup = hl.empty_dict(hl.tstr, hl.tstr)
        if 'remap_id' in pedigree_ht.row:
            project_remap_ht = parse_pedigree_ht_to_remap_ht(pedigree_ht)
            callset_mt = remap_sample_ids(
                callset_mt,
                project_remap_ht,
            )
            remap_lookup = hl.dict(
                {r.s: r.seqr_id for r in project_remap_ht.collect()},
            )

        families = parse_pedigree_ht_to_families(pedigree_ht)
        families_failed_missing_samples = get_families_failed_missing_samples(
            callset_mt,
            families,
        )
        families_failed_relatedness_check = {}
        families_failed_sex_check = {}
        families_failed_imputed_sex_ploidy = {}
        if (
            FeatureFlag.CHECK_SEX_AND_RELATEDNESS
            and self.dataset_type.check_sex_and_relatedness
            and not self.skip_check_sex_and_relatedness
        ):
            relatedness_check_ht = hl.read_table(
                relatedness_check_table_path(
                    self.reference_genome,
                    self.dataset_type,
                    self.callset_path,
                ),
            )
            sex_check_ht = hl.read_table(self.input()[3].path)
            families_failed_relatedness_check = get_families_failed_relatedness_check(
                families - families_failed_missing_samples.keys(),
                relatedness_check_ht,
                remap_lookup,
            )
            families_failed_imputed_sex_ploidy = get_families_failed_imputed_sex_ploidy(
                families
                - families_failed_missing_samples.keys()
                - families_failed_relatedness_check.keys(),
                callset_mt,
                sex_check_ht,
            )
            families_failed_sex_check = get_families_failed_sex_check(
                families
                - families_failed_missing_samples.keys()
                - families_failed_relatedness_check.keys()
                - families_failed_imputed_sex_ploidy.keys(),
                sex_check_ht,
                remap_lookup,
            )

        loadable_families = (
            families
            - families_failed_missing_samples.keys()
            - families_failed_relatedness_check.keys()
            - families_failed_sex_check.keys()
            - families_failed_imputed_sex_ploidy.keys()
        )
        if not len(loadable_families):
            msg = 'All families failed validation checks'
            raise SeqrValidationError(
                msg,
                {
                    'failed_family_samples': {
                        'missing_samples': format_failures(
                            families_failed_missing_samples,
                        ),
                        'relatedness_check': format_failures(
                            families_failed_relatedness_check,
                        ),
                        'sex_check': format_failures(families_failed_sex_check),
                        'ploidy_check': format_failures(
                            families_failed_imputed_sex_ploidy,
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

        if self.dataset_type.overwrite_male_non_par_calls:
            mt = overwrite_male_non_par_calls(mt, loadable_families)
        return mt.select_globals(
            remap_pedigree_hash=remap_pedigree_hash(
                project_pedigree_path(
                    self.reference_genome,
                    self.dataset_type,
                    self.sample_type,
                    self.project_guids[self.project_i],
                ),
            ),
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
                relatedness_check=(
                    format_failures(families_failed_relatedness_check)
                    or hl.empty_dict(hl.tstr, hl.tdict(hl.tstr, hl.tarray(hl.tstr)))
                ),
                sex_check=(
                    format_failures(families_failed_sex_check)
                    or hl.empty_dict(hl.tstr, hl.tdict(hl.tstr, hl.tarray(hl.tstr)))
                ),
                ploidy_check=(
                    format_failures(families_failed_imputed_sex_ploidy)
                    or hl.empty_dict(hl.tstr, hl.tdict(hl.tstr, hl.tarray(hl.tstr)))
                ),
            ),
        )
