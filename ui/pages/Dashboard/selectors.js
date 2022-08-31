import { createSelector } from 'reselect'

import { getProjectsByGuid, getProjectCategoriesByGuid } from 'redux/selectors'
import { SHOW_ALL, SHOW_DEMO } from './constants'

export const getProjectFilter = state => state.projectsTableState.filter

export const createProjectFilter = (projectsByGuid, projectFilter) => (projectGuid) => {
  if (projectFilter === SHOW_ALL) {
    return true
  }
  if (projectFilter === SHOW_DEMO) {
    return projectsByGuid[projectGuid].isDemo
  }
  return projectsByGuid[projectGuid].projectCategoryGuids.indexOf(projectFilter) > -1
}

/**
 * function that returns an array of currently-visible projectGuids based on the currently-selected
 * project filter.
 *
 * @param state {object} global Redux state
 */
export const getVisibleProjects = createSelector(
  getProjectsByGuid,
  getProjectCategoriesByGuid,
  getProjectFilter,
  (projectsByGuid, projectCategoriesByGuid, projectFilter) => {
    const filterFunc = createProjectFilter(projectsByGuid, projectFilter)
    const visibleProjectGuids = Object.keys(projectsByGuid).filter(filterFunc)
    return visibleProjectGuids.map((projectGuid) => {
      const project = projectsByGuid[projectGuid]
      const projectCategories = project.projectCategoryGuids.map(
        guid => (projectCategoriesByGuid[guid] && projectCategoriesByGuid[guid].name) || guid,
      )
      return { ...project, projectCategories }
    })
  },
)

export const getEditableCategoryOptions = createSelector(
  getProjectCategoriesByGuid,
  projectCategoriesByGuid => Object.values(projectCategoriesByGuid).map(
    projectCategory => ({ value: projectCategory.guid, text: projectCategory.name, key: projectCategory.guid }),
  ),
)

export const getCategoryOptions = createSelector(
  getEditableCategoryOptions,
  options => ([
    { value: SHOW_ALL, text: 'All', key: SHOW_ALL },
    { value: SHOW_DEMO, text: 'Demo', key: SHOW_DEMO },
    ...options,
  ]),
)
