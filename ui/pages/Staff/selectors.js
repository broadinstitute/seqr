import { createSelector } from 'reselect'

import { CORE_ANVIL_COLUMNS, VARIANT_ANVIL_COLUMNS, VARIANT_ANVIL_COLUMN_FORMATS } from './constants'

export const getAnvilLoading = state => state.anvilLoading.isLoading
export const getAnvilLoadingError = state => state.anvilLoading.errorMessage
export const getAnvilRows = state => state.anvilRows
export const getDiscoverySheetLoading = state => state.discoverySheetLoading.isLoading
export const getDiscoverySheetLoadingError = state => state.discoverySheetLoading.errorMessage
export const getDiscoverySheetRows = state => state.discoverySheetRows
export const getElasticsearchStatusLoading = state => state.elasticsearchStatusLoading.isLoading
export const getElasticsearchStatusData = state => state.elasticsearchStatus
export const getMmeMetricsLoading = state => state.mmeMetricsLoading.isLoading
export const getMmeMetricsLoadingError = state => state.mmeMetricsLoading.errorMessage
export const getMmeMetrics = state => state.mmeMetrics
export const getMmeSubmissionsLoading = state => state.mmeSubmissionsLoading.isLoading
export const getMmeSubmissions = state => state.mmeSubmissions
export const getSeqrStatsLoading = state => state.seqrStatsLoading.isLoading
export const getSeqrStatsLoadingError = state => state.seqrStatsLoading.errorMessage
export const getSeqrStats = state => state.seqrStats

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
