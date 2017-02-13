import { combineReducers } from 'redux'
import { SHOW_ALL, SORT_BY_PROJECT_NAME } from '../constants'
import { zeroActionsReducer, createUpdateStateReducer, createUpdateObjectByKeyReducer } from '../../../shared/utils/reducerUtils'


/**
 * Action creator and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
 */


// actions
const UPDATE_MODAL_DIALOG_STATE = 'UPDATE_MODAL_DIALOG_STATE'
const UPDATE_PROJECT_TABLE_STATE = 'UPDATE_PROJECT_TABLE_STATE'
const UPDATE_PROJECTS_BY_GUID = 'UPDATE_PROJECTS_BY_GUID'
const UPDATE_PROJECT_CATEGORIES_BY_GUID = 'UPDATE_PROJECT_CATEGORIES_BY_GUID'

// action creators
export const showModal = (modalType, modalProjectGuid) => ({ type: UPDATE_MODAL_DIALOG_STATE,
  updatedState: { modalIsVisible: true, modalType, modalProjectGuid } })

export const hideModal = () => ({ type: UPDATE_MODAL_DIALOG_STATE,
  updatedState: { modalIsVisible: false, modalType: null } })


// action creators
export const updateFilter = filter => ({ type: UPDATE_PROJECT_TABLE_STATE, updatedState: { filter } })
export const updateSortColumn = sortColumn => ({ type: UPDATE_PROJECT_TABLE_STATE, updatedState: { sortColumn } })
export const updateSortDirection = sortDirection => ({ type: UPDATE_PROJECT_TABLE_STATE, updatedState: { sortDirection } })

export const updateProjectsByGuid = projectsByGuid => ({ type: UPDATE_PROJECTS_BY_GUID, updatedState: projectsByGuid })

export const updateProjectCategoriesByGuid = projectCategoriesByGuid => ({ type: UPDATE_PROJECT_CATEGORIES_BY_GUID, updatedState: projectCategoriesByGuid })


const rootReducer = combineReducers({
  modalDialogState: createUpdateStateReducer(UPDATE_MODAL_DIALOG_STATE, {
    modalIsVisible: false, modalType: null, modalProjectGuid: null }),
  projectsTableState: createUpdateStateReducer(UPDATE_PROJECT_TABLE_STATE, {
    filter: SHOW_ALL, sortColumn: SORT_BY_PROJECT_NAME, sortDirection: 1, showCategories: true }),
  projectsByGuid: createUpdateObjectByKeyReducer(UPDATE_PROJECTS_BY_GUID),
  projectCategoriesByGuid: createUpdateObjectByKeyReducer(UPDATE_PROJECT_CATEGORIES_BY_GUID),
  datasetsByGuid: zeroActionsReducer,
  user: zeroActionsReducer,
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
export const getStateToSave = state => state.projectsTableState

/**
 * Applies state to save in local storage in the browser.
 *
 * @param state The full redux state object.
 * @param restoredState Sections of state that have been restored from local storage.
 * @returns A copy of state with restoredState applied
 */
export const applyRestoredState = (state, restoredState) => {
  const result = { ...state, projectsTableState: restoredState }
  console.log('with restored state:\n  ', result)
  return result
}
