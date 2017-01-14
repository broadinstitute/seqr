import { combineReducers } from 'redux'

import projectsTableReducer from './projectsTableReducer'
import projectsByGuidReducer from './projectsByGuidReducer'


// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

const zeroActionsReducer = (state = {}) => {
  return state
}

const rootReducer = combineReducers({
  user: zeroActionsReducer,
  projectsTable: projectsTableReducer,
  projectsByGuid: projectsByGuidReducer,
})

export default rootReducer

// selectors
//export const getUser = (state) => state.stored.user
