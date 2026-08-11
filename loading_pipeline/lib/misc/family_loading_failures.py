from collections import defaultdict

import hail as hl

from loading_pipeline.lib.core import Sex
from loading_pipeline.lib.logger import get_logger
from loading_pipeline.lib.misc.pedigree import Family, Relation, Sample

logger = get_logger(__name__)


def passes_relatedness_check(
    relatedness_check_lookup: dict[tuple[str, str], list],
    sample_id: str,
    other_id: str,
    expected_relation: Relation,
    additional_allowed_relation: Relation | None,
) -> tuple[bool, str | None]:
    # No relationship to check, return true
    if other_id is None:
        return True, None
    coefficients = relatedness_check_lookup.get(
        (min(sample_id, other_id), max(sample_id, other_id)),
    )
    if not coefficients or not any(
        relation.coefficients_equal(coefficients)
        for relation in (
            [expected_relation, additional_allowed_relation]
            if additional_allowed_relation
            else [expected_relation]
        )
    ):
        return (
            False,
            f'Sample {sample_id} has expected relation "{expected_relation.value}" to {other_id} but has coefficients {coefficients or []}',
        )
    return True, None


def all_relatedness_checks(
    relatedness_check_lookup: dict[tuple[str, str], list],
    family: Family,
    sample: Sample,
) -> list[str]:
    failure_reasons = []
    for relationship_set, relation, additional_allowed_relation in [
        ([sample.mother, sample.father], Relation.PARENT_CHILD, None),
        (
            [
                sample.maternal_grandmother,
                sample.maternal_grandfather,
                sample.paternal_grandmother,
                sample.paternal_grandfather,
            ],
            Relation.GRANDPARENT_GRANDCHILD,
            None,
        ),
        (sample.siblings, Relation.SIBLING, None),
        (sample.half_siblings, Relation.HALF_SIBLING, Relation.SIBLING),
        (sample.aunt_nephews, Relation.AUNT_NEPHEW, None),
    ]:
        for other_id in relationship_set:
            # Handle case where relation is identified in the
            # pedigree as a "dummy" but is not included in
            # the list of samples to load.
            if other_id not in family.samples:
                continue
            success, reason = passes_relatedness_check(
                relatedness_check_lookup,
                sample.sample_id,
                other_id,
                relation,
                additional_allowed_relation,
            )
            if not success:
                failure_reasons.append(reason)
    return failure_reasons


def build_relatedness_check_lookup(
    relatedness_check_ht: hl.Table,
    remap_lookup: hl.dict,
) -> dict[tuple[str, str], list]:
    relatedness_check_ht = relatedness_check_ht.key_by(
        i=remap_lookup.get(relatedness_check_ht.i, relatedness_check_ht.i),
        j=remap_lookup.get(relatedness_check_ht.j, relatedness_check_ht.j),
    )
    return {
        # NB: samples are sorted in the original ibd but not necessarily
        # sorted after remapping
        (min(r.i, r.j), max(r.i, r.j)): list(r.drop('i', 'j').values())
        for r in relatedness_check_ht.collect()
    }


def build_sex_check_lookup(
    sex_check_ht: hl.Table,
    remap_lookup: hl.dict,
) -> dict[str, Sex]:
    sex_check_ht = sex_check_ht.key_by(
        s=remap_lookup.get(sex_check_ht.s, sex_check_ht.s),
    )
    sex_check_ht = sex_check_ht.select('predicted_sex')
    return {r.s: Sex(r.predicted_sex) for r in sex_check_ht.collect()}


def get_families_failed_missing_samples(
    mt: hl.MatrixTable,
    families: set[Family],
) -> dict[Family, list[str]]:
    callset_samples = set(mt.cols().s.collect())
    failed_families = {}
    for family in families:
        missing_samples = family.samples.keys() - callset_samples
        if len(missing_samples) > 0:
            # NB: This is an array of a single element for consistency with
            # the other checks.
            failed_families[family] = [f'Missing samples: {missing_samples}']
    return failed_families


def get_families_failed_relatedness_check(
    families: set[Family],
    relatedness_check_ht: hl.Table,
    remap_lookup: hl.dict,
) -> dict[Family, list[str]]:
    relatedness_check_lookup = build_relatedness_check_lookup(
        relatedness_check_ht,
        remap_lookup,
    )
    failed_families = defaultdict(list)
    for family in families:
        for sample in family.samples.values():
            failure_reasons = all_relatedness_checks(
                relatedness_check_lookup,
                family,
                sample,
            )
            if failure_reasons:
                failed_families[family].extend(failure_reasons)
    return dict(failed_families)


def get_families_failed_sex_check(
    families: set[Family],
    sex_check_ht: hl.Table,
    remap_lookup: hl.dict,
) -> dict[Family, list[str]]:
    sex_check_lookup = build_sex_check_lookup(sex_check_ht, remap_lookup)
    failed_families = defaultdict(list)
    for family in families:
        for sample_id in family.samples:
            if sample_id not in sex_check_lookup:
                failed_families[family].append(
                    f'Sample {sample_id} has pedigree sex {family.samples[sample_id].sex.value} but is missing from the sex check source',
                )
                continue
            # NB: Both Unknown samples in pedigree and Unknown
            # samples in the predicted_sex are precluded from
            # failing the sex check.
            if (
                sex_check_lookup[sample_id] == Sex.UNKNOWN
                or family.samples[sample_id].sex == Sex.UNKNOWN
            ):
                logger.info(
                    f'Encountered sample with Unknown sex excluded from sex check: {sample_id}',
                )
                continue

            if family.samples[sample_id].sex != sex_check_lookup[sample_id]:
                failed_families[family].append(
                    f'Sample {sample_id} has pedigree sex {family.samples[sample_id].sex.value} but imputed sex {sex_check_lookup[sample_id].value}',
                )
    return dict(failed_families)


def get_families_failed_imputed_sex_ploidy(
    families: set[Family],
    mt: hl.MatrixTable,
    sex_check_ht: hl.Table,
) -> dict[Family, str]:
    mt = mt.select_cols(
        discrepant=(
            (
                # All calls are diploid or missing but the sex is Male
                hl.agg.all(mt.GT.is_diploid() | hl.is_missing(mt.GT))
                & (sex_check_ht[mt.s].predicted_sex == Sex.MALE.value)
            )
            | (
                # At least one call is haploid but the sex is Female, X0, XXY, XYY, or XXX
                hl.agg.any(~mt.GT.is_diploid())
                & hl.literal(
                    {
                        Sex.FEMALE.value,
                        Sex.X0.value,
                        Sex.XYY.value,
                        Sex.XXY.value,
                        Sex.XXX.value,
                    },
                ).contains(sex_check_ht[mt.s].predicted_sex)
            )
        ),
    )
    discrepant_samples = mt.aggregate_cols(
        hl.agg.filter(mt.discrepant, hl.agg.collect_as_set(mt.s)),
    )
    failed_families = defaultdict(list)
    for family in families:
        discrepant_loadable_samples = set(family.samples.keys()) & discrepant_samples
        if discrepant_loadable_samples:
            sorted_discrepant_samples = sorted(discrepant_loadable_samples)
            failed_families[family].append(
                f'Found samples with misaligned ploidy with their provided imputed sex: {sorted_discrepant_samples}',
            )
    return failed_families
