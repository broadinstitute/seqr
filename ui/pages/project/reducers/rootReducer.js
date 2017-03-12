import { combineReducers } from 'redux'

import modalDialogReducer from './modalDialogReducer'
import projectsTableReducer from './projectsTableReducer'
import projectsByGuidReducer from './projectsByGuidReducer'


// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

const zeroActionsReducer = (state = {}) => {
  return state
}

const rootReducer = combineReducers({
  user: zeroActionsReducer,
  modalDialog: modalDialogReducer,
  familiesTable: projectsTableReducer,
  familiesByGuid: projectsByGuidReducer,
})

export default rootReducer

// selectors
//export const getUser = (state) => state.stored.user


/**
 * Returns the sections of state to save in local storage in the browser.
 *
 * @param state The full redux state object.
 *
 * @returns A copy of state with restoredState applied
 */
export const getStateToSave = state => state.projectsTable

/**
 * Applies state to save in local storage in the browser.
 *
 * @param state The full redux state object.
 * @param restoredState Sections of state that have been restored from local storage.
 * @returns A copy of state with restoredState applied
 */
export const applyRestoredState = (state, restoredState) => {
  return { ...state, ...{ projectsTable: restoredState } }
}
