
// actions
const UPDATE_PROJECTS_BY_GUID = 'UPDATE_PROJECTS_BY_GUID'

// action creators
export const updateProjectsByGuid = projectsByGuid => ({ type: UPDATE_PROJECTS_BY_GUID, projectsByGuid })

// reducer
const projectsByGuidReducer = (projectsByGuid = {}, action) => {
  switch (action.type) {
    case UPDATE_PROJECTS_BY_GUID: {
      const projectsByGuidCopy = { ...projectsByGuid }
      Object.entries(action.projectsByGuid).map(([projectGuid, updatedProject]) => (
        projectsByGuidCopy[projectGuid] = { ...projectsByGuid[projectGuid], ...updatedProject }
      ))
      return projectsByGuidCopy
    }
    default:
      return projectsByGuid
  }
}

export default projectsByGuidReducer
