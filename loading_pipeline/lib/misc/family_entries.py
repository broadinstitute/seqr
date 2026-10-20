import hail as hl

from loading_pipeline.lib.core import DatasetType, SampleType


def compute_callset_family_entries_ht(
    dataset_type: DatasetType,
    mt: hl.MatrixTable,
    entries_fields: dict[str, hl.Expression],
    sample_type: SampleType,
) -> hl.Table:
    sample_id_to_family_guid = hl.dict(
        {
            s: family_guid
            for family_guid, sample_ids in hl.eval(mt.family_samples).items()
            for s in sample_ids
        },
    )
    family_guid_to_project_guid = hl.dict(
        {
            family_guid: project_guid
            for project_guid, family_guids in hl.eval(mt.project_families).items()
            for family_guid in family_guids
        },
    )
    ht = mt.select_rows(
        filters=mt.filters.difference(dataset_type.excluded_filters),
        family_entries=(
            # NB: we're sorted by both family and sample when this runs.
            # However, the sort is not guaranteed once the entries
            # table is edited and families are spliced out and re-appended.
            hl.sorted(
                hl.agg.collect(
                    hl.Struct(
                        sampleId=mt.s,
                        **entries_fields,
                    ),
                )
                .group_by(lambda e: sample_id_to_family_guid[e.sampleId])
                .items()
                .starmap(
                    lambda family_guid, entries: hl.Struct(
                        family_guid=family_guid,
                        project_guid=family_guid_to_project_guid[family_guid],
                        calls=hl.sorted(entries, key=lambda e: e.sampleId),
                    ),
                ),
                lambda fe: fe.family_guid,
            )
        ),
    ).rows()
    ht = ht.key_by(
        **dataset_type.entries_table_key_expression(ht, sample_type),
    )
    ht = ht.annotate(
        family_entries=(
            ht.family_entries.map(
                lambda fe: hl.or_missing(
                    fe.calls.any(lambda e: e.gt > 0),
                    fe,
                ),
            )
        ),
    )
    # Only keep rows where at least one family is not missing.
    return ht.filter(ht.family_entries.any(hl.is_defined))


def deduplicate_by_most_non_ref_calls(ht: hl.Table) -> hl.Table:
    ht = ht.annotate(
        non_ref_count=hl.len(
            hl.flatten(ht.family_entries.calls).filter(lambda s: s.gt > 0),
        ),
    )
    return ht.group_by(*ht.key).aggregate(
        filters=hl.agg.take(ht.filters, 1, ordering=-ht.non_ref_count)[0],
        family_entries=hl.agg.take(ht.family_entries, 1, ordering=-ht.non_ref_count)[0],
    )
