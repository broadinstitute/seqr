import { createSelector } from 'reselect'

import { getProjectsByGuid, getSampleBatchesByGuid, getProjectFilter, getProjectSortColumn, getProjectSortDirection } from '../reducers/rootReducer'
import { computeSortedProjectGuids } from './projectSort'
import { createProjectFilter } from './projectFilter'


/**
 * function that returns an array of currently-visible projectGuids based on the currently-selected
 * project filter.
 *
 * @param state {object} global Redux state
 */
export const getVisibleProjectGuids = createSelector(
  getProjectsByGuid,
  getProjectFilter,
  (projectsByGuid, projectFilter) => {
    const filterFunc = createProjectFilter(projectsByGuid, projectFilter)
    const visibleProjectGuids = Object.keys(projectsByGuid).filter(filterFunc)
    return visibleProjectGuids
  },
)

/**
 * function that returns an array of currently-visible project objects, sorted according to
 * current user-selected values of projectSortColumn and projectSortDirection.
 *
 * @param state {object} global Redux state
 */
export const getVisibleProjectsInSortedOrder = createSelector(
  getVisibleProjectGuids,
  getProjectsByGuid,
  getSampleBatchesByGuid,
  getProjectSortColumn,
  getProjectSortDirection,
  (visibleProjectGuids, projectsByGuid, sampleBatchesByGuid, projectSortColumn, projectSortDirection) => {
    const sortedProjectGuids = computeSortedProjectGuids(visibleProjectGuids, projectsByGuid, sampleBatchesByGuid, projectSortColumn, projectSortDirection)
    const sortedProjects = sortedProjectGuids.map(projectGuid => projectsByGuid[projectGuid])
    return sortedProjects
  },
)
