import { createSelector } from 'reselect'

import { CORE_ANVIL_COLUMNS, VARIANT_ANVIL_COLUMNS, VARIANT_ANVIL_COLUMN_FORMATS } from './constants'

export const getAnvilLoading = state => state.anvilLoading.isLoading
export const getAnvilRows = state => state.anvilRows

export const getAnvilColumns = createSelector(
  getAnvilRows,
  (rawData) => {
    const maxSavedVariants = Math.max(1, ...rawData.map(({ numSavedVariants }) => numSavedVariants))
    return CORE_ANVIL_COLUMNS.concat(
      ...[...Array(maxSavedVariants).keys()].map(i => VARIANT_ANVIL_COLUMNS.map((col) => {
        const colName = `${col} - ${i + 1}`
        return {
          name: colName,
          content: colName,
          format: VARIANT_ANVIL_COLUMN_FORMATS[col] && (row => VARIANT_ANVIL_COLUMN_FORMATS[col](row[colName])),
        }
      })))
  },
)
