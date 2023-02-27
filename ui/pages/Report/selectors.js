import { createSelector } from 'reselect'

import { CORE_ANVIL_COLUMNS, AIRTABLE_ANVIL_COLUMNS, VARIANT_ANVIL_COLUMNS, ALL_PROJECTS_PATH } from './constants'

export const getDiscoverySheetLoading = state => state.discoverySheetLoading.isLoading
export const getDiscoverySheetLoadingError = state => state.discoverySheetLoading.errorMessage
export const getDiscoverySheetRows = state => state.discoverySheetRows
export const getSampleMetadataLoading = state => state.sampleMetadataLoading.isLoading
export const getSampleMetadataLoadingError = state => state.sampleMetadataLoading.errorMessage
export const getSampleMetadataRows = state => state.sampleMetadataRows
export const getSearchHashContextLoading = state => state.searchHashContextLoading.isLoading
export const getSeqrStatsLoading = state => state.seqrStatsLoading.isLoading
export const getSeqrStatsLoadingError = state => state.seqrStatsLoading.errorMessage
export const getSeqrStats = state => state.seqrStats

export const getSampleMetadataColumns = createSelector(
  getSampleMetadataRows,
  (state, props) => props.match.params.projectGuid,
  (rawData, projectGuid) => {
    const maxSavedVariants = Math.max(1, ...rawData.map(row => row.num_saved_variants))
    return [...CORE_ANVIL_COLUMNS, ...(projectGuid === ALL_PROJECTS_PATH ? [] : AIRTABLE_ANVIL_COLUMNS)].concat(
      ...[...Array(maxSavedVariants).keys()].map(i => VARIANT_ANVIL_COLUMNS.map(col => ({ name: `${col}-${i + 1}` }))),
    ).map(({ name, ...props }) => ({ name, content: name, ...props }))
  },
)
