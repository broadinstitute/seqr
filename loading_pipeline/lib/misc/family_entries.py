import hail as hl

from loading_pipeline.lib.core import DatasetType


def compute_callset_family_entries_ht(
    dataset_type: DatasetType,
    mt: hl.MatrixTable,
    entries_fields: dict[str, hl.Expression],
) -> hl.Table:
    sample_id_to_family_guid = hl.dict(
        {
            s: family_guid
            for family_guid, sample_ids in hl.eval(mt.family_samples).items()
            for s in sample_ids
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
                        s=mt.s,
                        family_guid=sample_id_to_family_guid[mt.s],
                        **entries_fields,
                    ),
                )
                .group_by(lambda e: e.family_guid)
                .values()
                .map(
                    lambda fe: hl.sorted(fe, key=lambda e: e.s),
                ),
                lambda fe: fe[0].family_guid,
            )
        ),
    ).rows()
    # NB: globalize before we set families to missing
    ht = globalize_ids(ht)
    ht = ht.annotate(
        family_entries=(
            ht.family_entries.map(
                lambda fe: hl.or_missing(
                    fe.any(dataset_type.family_entries_filter_fn),
                    fe,
                ),
            )
        ),
    )
    # Only keep rows where at least one family is not missing.
    return ht.filter(ht.family_entries.any(hl.is_defined))


def globalize_ids(ht: hl.Table) -> hl.Table:
    row = ht.take(1)[0] if ht.count() > 0 else None
    has_family_entries = row and len(row.family_entries) > 0
    ht = ht.annotate_globals(
        family_guids=(
            [fe[0].family_guid for fe in row.family_entries]
            if has_family_entries
            else hl.empty_array(hl.tstr)
        ),
        family_samples=(
            {fe[0].family_guid: [e.s for e in fe] for fe in row.family_entries}
            if has_family_entries
            else hl.empty_dict(hl.tstr, hl.tarray(hl.tstr))
        ),
    )
    return ht.annotate(
        family_entries=ht.family_entries.map(
            lambda fe: fe.map(lambda se: se.drop('s', 'family_guid')),
        ),
    )


def deglobalize_ids(ht: hl.Table) -> hl.Table:
    ht = ht.annotate(
        family_entries=(
            hl.enumerate(ht.family_entries).starmap(
                lambda i, fe: hl.enumerate(fe).starmap(
                    lambda j, e: hl.Struct(
                        **e,
                        s=ht.family_samples[ht.family_guids[i]][j],
                        family_guid=ht.family_guids[i],
                    ),
                ),
            )
        ),
    )
    return ht.drop('family_guids', 'family_samples')


def deduplicate_by_most_non_ref_calls(ht: hl.Table) -> hl.Table:
    ht = ht.annotate(
        non_ref_count=hl.len(
            hl.flatten(ht.family_entries).filter(lambda s: s.GT.is_non_ref()),
        ),
    )
    return ht.group_by(*ht.key).aggregate(
        filters=hl.agg.take(ht.filters, 1, ordering=-ht.non_ref_count)[0],
        family_entries=hl.agg.take(ht.family_entries, 1, ordering=-ht.non_ref_count)[0],
    )
