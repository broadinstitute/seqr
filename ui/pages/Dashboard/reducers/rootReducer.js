import { combineReducers } from 'redux'


// action creators and reducers in one file as suggested by
// https://github.com/erikras/ducks-modular-redux

// actions
const UPDATE_PROJECT_INFO = 'UPDATE_PROJECT_INFO'

// action creators
export const updateProjectInfo = (projectGuid, projectInfo) => ({
  type: UPDATE_PROJECT_INFO,
  projectGuid,
  projectInfo,
})

// reducer
const noopReducer = (state = {}) => {
  return state
}

const userReducer = noopReducer

const projectsByGuidReducer = (projectsByGuid = {}, action) => {
  switch (action.type) {
    case UPDATE_PROJECT_INFO: {
      //update key-values for the given project with key-value pairs in the action.projectInfo obj.
      const copy = { ...projectsByGuid }
      copy[action.projectGuid] = {
        ...copy[action.projectGuid],
        ...action.projectInfo,
      }
      return copy
    }
    default:
      return projectsByGuid
  }
}

const rootReducer = combineReducers({
  user: userReducer,
  projectsByGuid: projectsByGuidReducer,
})

export default rootReducer

// selectors
//export const getUser = (state) => state.stored.user
