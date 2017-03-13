import { SHOW_ALL } from '../constants'

export const createProjectFilter = (projectsByGuid, projectFilter) => {
  return (projectGuid) => {
    if (projectFilter === SHOW_ALL) {
      return true
    }
    return projectsByGuid[projectGuid].projectCategoryGuids.indexOf(projectFilter) > -1
  }
}
