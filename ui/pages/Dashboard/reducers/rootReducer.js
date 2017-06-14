import { combineReducers } from 'redux'
import { zeroActionsReducer, createSingleObjectReducer, createObjectsByIdReducer } from 'shared/utils/reducerUtils'
import { SHOW_ALL, SORT_BY_PROJECT_NAME } from '../constants'

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
  updates: { modalIsVisible: true, modalType, modalProjectGuid } })

export const hideModal = () => ({ type: UPDATE_MODAL_DIALOG_STATE,
  updates: { modalIsVisible: false, modalType: null } })

export const updateFilter = filter => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { filter } })
export const updateSortColumn = sortColumn => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { sortColumn } })
export const updateSortDirection = sortDirection => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { sortDirection } })

export const updateProjectsByGuid = projectsByGuid => ({ type: UPDATE_PROJECTS_BY_GUID, updatesById: projectsByGuid })

export const updateProjectCategoriesByGuid = projectCategoriesByGuid => ({
  type: UPDATE_PROJECT_CATEGORIES_BY_GUID, updatesById: projectCategoriesByGuid,
})


// root reducer
const rootReducer = combineReducers({
  modalDialogState: createSingleObjectReducer(UPDATE_MODAL_DIALOG_STATE, {
    modalIsVisible: false, modalType: null, modalProjectGuid: null }, true),
  projectsTableState: createSingleObjectReducer(UPDATE_PROJECT_TABLE_STATE, {
    filter: SHOW_ALL, sortColumn: SORT_BY_PROJECT_NAME, sortDirection: 1,
  }, false),
  projectsByGuid: createObjectsByIdReducer(UPDATE_PROJECTS_BY_GUID, {}, false),
  projectCategoriesByGuid: createObjectsByIdReducer(UPDATE_PROJECT_CATEGORIES_BY_GUID, {}, false),
  sampleBatchesByGuid: zeroActionsReducer,
  user: zeroActionsReducer,
})

export default rootReducer

// basic selectors
export const getModalDialogState = state => state.modalDialogState
export const getModalProjectGuid = state => state.modalDialogState.modalProjectGuid

//export const getProjectsTableState = state => state.projectsTableState
export const getProjectFilter = state => state.projectsTableState.filter
export const getProjectSortColumn = state => state.projectsTableState.sortColumn
export const getProjectSortDirection = state => state.projectsTableState.sortDirection

export const getProjectsByGuid = state => state.projectsByGuid
export const getProjectCategoriesByGuid = state => state.projectCategoriesByGuid
export const getSampleBatchesByGuid = state => state.sampleBatchesByGuid
export const getUser = state => state.user

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
