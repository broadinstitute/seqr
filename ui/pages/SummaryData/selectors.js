import { createSelector } from 'reselect'

import { CORE_ANVIL_COLUMNS, AIRTABLE_ANVIL_COLUMNS, VARIANT_ANVIL_COLUMNS, ALL_PROJECTS_PATH } from './constants'

export const getSuccessStoryLoading = state => state.successStoryLoading.isLoading
export const getSuccessStoryLoadingError = state => state.successStoryLoading.errorMessage
export const getSuccessStoryRows = state => state.successStoryRows
export const getMmeLoading = state => state.mmeLoading.isLoading
export const getMmeLoadingError = state => state.mmeLoading.errorMessage
export const getMmeMetrics = state => state.mmeMetrics
export const getMmeSubmissions = state => state.mmeSubmissions
export const getExternalAnalysisUploadStats = state => state.externalAnalysisUploadStats
export const getSampleMetadataLoading = state => state.sampleMetadataLoading.isLoading
export const getSampleMetadataLoadingError = state => state.sampleMetadataLoading.errorMessage
export const getSampleMetadataRows = state => state.sampleMetadataRows

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
