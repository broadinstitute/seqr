import { formValueSelector } from 'redux-form'
import { createSelector } from 'reselect'

import {
  CORE_ANVIL_COLUMNS, VARIANT_ANVIL_COLUMNS, VARIANT_ANVIL_COLUMN_FORMATS, STAFF_SEARCH_FORM_NAME, INCLUDE_ALL_PROJECTS,
} from './constants'

export const getAnvilLoading = state => state.anvilLoading.isLoading
export const getAnvilLoadingError = state => state.anvilLoading.errorMessage
export const getAnvilRows = state => state.anvilRows
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
export const getSeqrStatsLoading = state => state.seqrStatsLoading.isLoading
export const getSeqrStatsLoadingError = state => state.seqrStatsLoading.errorMessage
export const getSeqrStats = state => state.seqrStats
export const getQcUploadStats = state => state.qcUploadStats

export const getAnvilColumns = createSelector(
  getAnvilRows,
  (rawData) => {
    const maxSavedVariants = Math.max(1, ...rawData.map(({ numSavedVariants }) => numSavedVariants))
    return CORE_ANVIL_COLUMNS.concat(
      ...[...Array(maxSavedVariants).keys()].map(i => VARIANT_ANVIL_COLUMNS.map((col) => {
        const colName = `${col}-${i + 1}`
        return {
          name: colName,
          content: colName,
          format: VARIANT_ANVIL_COLUMN_FORMATS[col] && (row => VARIANT_ANVIL_COLUMN_FORMATS[col](row[colName])),
        }
      })))
  },
)

export const getSearchIncludeAllProjectsInput = state =>
  formValueSelector(STAFF_SEARCH_FORM_NAME)(state, INCLUDE_ALL_PROJECTS)
