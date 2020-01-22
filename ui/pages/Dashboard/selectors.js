import { createSelector } from 'reselect'

import { getProjectsByGuid } from 'redux/selectors'
import { SHOW_ALL } from './constants'


export const getProjectFilter = state => state.projectsTableState.filter

export const createProjectFilter = (projectsByGuid, projectFilter) => {
  return (projectGuid) => {
    if (projectFilter === SHOW_ALL) {
      return true
    }
    return projectsByGuid[projectGuid].projectCategoryGuids.indexOf(projectFilter) > -1
  }
}

/**
 * function that returns an array of currently-visible projectGuids based on the currently-selected
 * project filter.
 *
 * @param state {object} global Redux state
 */
export const getVisibleProjects = createSelector(
  getProjectsByGuid,
  getProjectFilter,
  (projectsByGuid, projectFilter) => {
    const filterFunc = createProjectFilter(projectsByGuid, projectFilter)
    const visibleProjectGuids = Object.keys(projectsByGuid).filter(filterFunc)
    return visibleProjectGuids.map(projectGuid => projectsByGuid[projectGuid])
  },
)
