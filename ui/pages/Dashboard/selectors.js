import { createSelector } from 'reselect'

import { getAnalysisGroupsByGuid, getProjectsByGuid, getProjectCategoriesByGuid } from 'redux/selectors'
import { SHOW_ALL, SHOW_DEMO } from './constants'

export const getProjectFilter = state => state.projectsTableState.filter

export const createProjectFilter = projectFilter => (project) => {
  if (projectFilter === SHOW_ALL) {
    return true
  }
  if (projectFilter === SHOW_DEMO) {
    return project.isDemo
  }
  return project.projectCategoryGuids?.indexOf(projectFilter) > -1
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
  getAnalysisGroupsByGuid,
  getProjectFilter,
  (projectsByGuid, projectCategoriesByGuid, analysisGroupsByGuid, projectFilter) => {
    const filterFunc = createProjectFilter(projectFilter)
    const visibleProjects = [
      ...Object.values(projectsByGuid).filter(({ partialAccess }) => !partialAccess),
      ...Object.values(analysisGroupsByGuid).filter(
        ({ projectGuid }) => projectGuid && (!projectsByGuid[projectGuid] || projectsByGuid[projectGuid].partialAccess),
      ),
    ].filter(filterFunc)
    return visibleProjects.map((project) => {
      const projectCategories = (project.projectCategoryGuids || []).map(
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
