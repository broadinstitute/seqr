import { createSelector } from 'reselect'

import { getProjectsByGuid } from 'redux/selectors'
import { CORE_ANVIL_COLUMNS, VARIANT_ANVIL_COLUMNS } from './constants'

export const getAnvilLoading = state => state.anvilLoading.isLoading
export const getAnvilRows = state => state.anvilRows

export const getAnvilColumns = createSelector(
  getAnvilRows,
  (rawData) => {
    const maxSavedVariants = Math.max(1, ...rawData.map(({ numSavedVariants }) => numSavedVariants))
    return CORE_ANVIL_COLUMNS.concat(
      ...[...Array(maxSavedVariants).keys()].map(i => VARIANT_ANVIL_COLUMNS.map((col) => {
        const colName = `${col} - ${i + 1}`
        return { name: colName, content: colName }
      })))
  },
)

export const getAnvilExportConfig = createSelector(
  getAnvilRows,
  getProjectsByGuid,
  (state, props) => props.match.params.projectGuid,
  getAnvilColumns,
  (rawData, projectsByGuid, projectGuid, anvilColumns) => {
    const project = projectsByGuid[projectGuid]
    return [
      {
        name: 'All Cases',
        data: {
          filename: `anvil_export_${project ? project.name.replace(' ', '_').toLowerCase() : 'all_projects'}`,
          rawData,
          headers: anvilColumns.map(config => config.content),
          processRow: row => anvilColumns.map(config => (config.format ? config.format(row) : row[config.name])),
        },
      },
    ]

  },
)
