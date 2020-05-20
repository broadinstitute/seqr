import { formValueSelector } from 'redux-form'
import { createSelector } from 'reselect'

import {
  CORE_ANVIL_COLUMNS, VARIANT_ANVIL_COLUMNS, STAFF_SEARCH_FORM_NAME, INCLUDE_ALL_PROJECTS,
} from './constants'

export const getDiscoverySheetLoading = state => state.discoverySheetLoading.isLoading
export const getDiscoverySheetLoadingError = state => state.discoverySheetLoading.errorMessage
export const getDiscoverySheetRows = state => state.discoverySheetRows
export const getSuccessStoryLoading = state => state.successStoryLoading.isLoading
export const getSuccessStoryLoadingError = state => state.successStoryLoading.errorMessage
export const getSuccessStoryRows = state => state.successStoryRows
export const getElasticsearchStatusLoading = state => state.elasticsearchStatusLoading.isLoading
export const getElasticsearchStatusData = state => state.elasticsearchStatus
export const getMmeLoading = state => state.mmeLoading.isLoading
export const getMmeLoadingError = state => state.mmeLoading.errorMessage
export const getMmeMetrics = state => state.mmeMetrics
export const getMmeSubmissions = state => state.mmeSubmissions
export const getSampleMetadataLoading = state => state.sampleMetadataLoading.isLoading
export const getSampleMetadataLoadingError = state => state.sampleMetadataLoading.errorMessage
export const getSampleMetadataRows = state => state.sampleMetadataRows
export const getSearchHashContextLoading = state => state.searchHashContextLoading.isLoading
export const getSeqrStatsLoading = state => state.seqrStatsLoading.isLoading
export const getSeqrStatsLoadingError = state => state.seqrStatsLoading.errorMessage
export const getSeqrStats = state => state.seqrStats
export const getQcUploadStats = state => state.qcUploadStats

export const getSampleMetadataColumns = createSelector(
  getSampleMetadataRows,
  (rawData) => {
    const maxSavedVariants = Math.max(1, ...rawData.map(row => row.num_saved_variants))
    return CORE_ANVIL_COLUMNS.concat(
      ...[...Array(maxSavedVariants).keys()].map(i => VARIANT_ANVIL_COLUMNS.map(col => ({ name: `${col}-${i + 1}` }))),
    ).map(({ name, ...props }) => ({ name, content: name, ...props }))
  },
)

export const getSearchIncludeAllProjectsInput = state =>
  formValueSelector(STAFF_SEARCH_FORM_NAME)(state, INCLUDE_ALL_PROJECTS)
