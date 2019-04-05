import { createSelector } from 'reselect'

import { getProjectsByGuid } from '../../../redux/selectors'
import { getProjectFilter } from '../reducers'
import { createProjectFilter } from './projectFilter'


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
