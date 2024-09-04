import hail as hl

from hail_search.constants import COMPOUND_HET, DE_NOVO


class BothSampleTypesMixin:

    def filter_entries_table_both_sample_types(
        self, entries_hts_map: dict[str, list[tuple[hl.Table, dict]]], inheritance_filter=None, quality_filter=None, **kwargs
    ):
        filtered_project_hts = []
        filtered_comp_het_project_hts = []
        wes_entries, wgs_entries = entries_hts_map['WES'], entries_hts_map['WGS']  # entries_hts_map: {<sample_type>: [(ht, project_samples), ...]}

        for (wes_ht, wes_project_samples), (wgs_ht, wgs_project_samples) in zip(wes_entries, wgs_entries):
            wes_ht, sorted_wes_family_sample_data = self._add_entry_sample_families(
                wes_ht, wes_project_samples, 'WES'
            )
            wgs_ht, sorted_wgs_family_sample_data = self._add_entry_sample_families(
                wgs_ht, wgs_project_samples, 'WGS'
            )
            wes_ht = wes_ht.rename({'family_entries': 'wes_family_entries', 'filters': 'wes_filters'})
            wgs_ht = wgs_ht.rename({'family_entries': 'wgs_family_entries', 'filters': 'wgs_filters'})
            ht = wes_ht.join(wgs_ht, how='outer')

            ht = self._filter_quality_both_sample_types(ht, quality_filter)
            ht, ch_ht = self._filter_inheritance_both_sample_types(
                ht, inheritance_filter, sorted_wes_family_sample_data, sorted_wgs_family_sample_data
            )
            if ht:
                filtered_project_hts.append(self._merge_both_sample_types_project_ht(ht))
            if ch_ht:
                filtered_comp_het_project_hts.append(self._merge_both_sample_types_project_ht(ch_ht))

        return filtered_project_hts, filtered_comp_het_project_hts

    def _filter_quality_both_sample_types(self, ht: hl.Table, quality_filter: dict):
        """
        Filter by quality, keeping variants that pass quality filter in at least one sample type.
        """
        wes_passes_quality_filter = self._get_family_passes_quality_filter(quality_filter, ht, 'wes_filters')
        if wes_passes_quality_filter is not None:
            ht = ht.annotate(
                wes_passes=ht.wes_family_entries.map(
                    lambda entries: hl.or_missing(wes_passes_quality_filter(entries), entries)
                ))
        else:
            ht = ht.annotate(wes_passes=ht.wes_family_entries)
        wgs_passes_quality_filter = self._get_family_passes_quality_filter(quality_filter, ht, 'wgs_filters')
        if wgs_passes_quality_filter is not None:
            ht = ht.annotate(
                wgs_passes=ht.wgs_family_entries.map(
                    lambda entries: hl.or_missing(wgs_passes_quality_filter(entries), entries)
                ))
        else:
            ht = ht.annotate(wgs_passes=ht.wgs_family_entries)
        ht = ht.filter(ht.wes_passes.any(hl.is_defined) | ht.wgs_passes.any(hl.is_defined))
        return ht

    @staticmethod
    def _merge_both_sample_types_project_ht(ht: hl.Table):
        ht = ht.drop('wes_passes', 'wgs_passes')
        ht = ht.transmute(
            family_entries=hl.coalesce(ht.wes_family_entries, hl.empty_array(ht.wes_family_entries[0].dtype)).extend(
                hl.coalesce(ht.wgs_family_entries, hl.empty_array(ht.wgs_family_entries[0].dtype))
            ),
            filters=hl.coalesce(ht.wes_filters, hl.empty_set(hl.tstr)).union(
                hl.coalesce(ht.wgs_filters, hl.empty_set(hl.tstr))
            )
        )
        return ht.transmute_globals(family_guids=ht.family_guids.extend(ht.family_guids_1))


    def _filter_inheritance_both_sample_types(
        self, ht, inheritance_filter, sorted_wes_family_sample_data, sorted_wgs_family_sample_data
    ):
        # At least one family member must have non-ref gt
        any_valid_entry, is_any_affected = self._get_any_family_member_gt_has_alt_filter()
        ht = ht.annotate(
            wes_passes=ht.wes_family_entries.map(
                lambda entries: hl.or_missing(entries.any(any_valid_entry), entries)
            ),
            wgs_passes=ht.wgs_family_entries.map(
                lambda entries: hl.or_missing(entries.any(any_valid_entry), entries)
            )
        )

        comp_het_ht = None
        if self._has_comp_het_search:
            comp_het_ht = self._annotate_families_inheritance(
                ht, COMPOUND_HET, inheritance_filter, sorted_wes_family_sample_data,
                sample_type='WES',
            )
            comp_het_ht = self._annotate_families_inheritance(
                comp_het_ht, COMPOUND_HET, inheritance_filter, sorted_wgs_family_sample_data,
                sample_type='WGS',
            )
            comp_het_ht = self._post_process_inheritance_both_sample_types(comp_het_ht)
            comp_het_ht = comp_het_ht.filter(
                comp_het_ht.wes_passes.any(hl.is_defined) | comp_het_ht.wgs_passes.any(hl.is_defined)
            ).select_globals('family_guids', 'family_guids_1')

        if is_any_affected or not (inheritance_filter or self._inheritance_mode):
            # No sample-specific inheritance filtering needed
            sorted_wes_family_sample_data = sorted_wgs_family_sample_data = []

        if self._inheritance_mode == COMPOUND_HET:
            ht = None
        else:
            ht = self._annotate_families_inheritance(
                ht, self._inheritance_mode, inheritance_filter, sorted_wes_family_sample_data,
                sample_type='WES',
            )
            ht = self._annotate_families_inheritance(
                ht, self._inheritance_mode, inheritance_filter, sorted_wgs_family_sample_data,
                sample_type='WGS',
            )
            ht = self._post_process_inheritance_both_sample_types(ht)
            ht = ht.filter(
                ht.wes_passes.any(hl.is_defined) | ht.wgs_passes.any(hl.is_defined)
            ).select_globals('family_guids', 'family_guids_1')

        return ht, comp_het_ht

    def _post_process_inheritance_both_sample_types(self, ht: hl.Table):
        if self._inheritance_mode == DE_NOVO:
            def _validate_de_novo(sample_type_1_passes, sample_type_2_passes):
                # Remove a variant if it was filtered out due to inheritance in one sample type
                # and is de novo in the other sample type but there is only one affected sample.
                return hl.enumerate(sample_type_1_passes).map(
                    lambda family_entries: hl.if_else(  # family_entries: (idx, [<family_1_sample_1>, <family_1_sample_2>, ...]) or (idx, NA)
                        hl.is_missing(sample_type_2_passes[family_entries[0]]) & hl.is_defined(family_entries[1]),
                        hl.or_missing(~(hl.len(family_entries[1]) == 1), family_entries[1]),
                        family_entries[1]
                    )
                )
            ht = ht.annotate(
                wes_passes=_validate_de_novo(ht.wes_passes, ht.wgs_passes),
                wgs_passes=_validate_de_novo(ht.wgs_passes, ht.wes_passes)
            )
        return ht
