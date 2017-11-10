import { combineReducers } from 'redux'
import { zeroActionsReducer, createSingleObjectReducer, createObjectsByIdReducer } from 'shared/utils/reducerUtils'
import { pedigreeImageZoomModalState } from 'shared/components/panel/pedigree-image/zoom-modal/state'
import { phenoTipsModalState } from 'shared/components/panel/phenotips-view/phenotips-modal/state'
import { textEditorModalState } from 'shared/components/modal/text-editor-modal/state'
import { addOrEditIndividualsModalState } from 'shared/components/panel/add-or-edit-individuals/state'
import { editProjectModalState } from 'shared/components/modal/edit-project-modal/state'

import { SHOW_ALL, SORT_BY_FAMILY_NAME } from '../constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

// actions
const UPDATE_INDIVIDUALS_BY_GUID = 'UPDATE_INDIVIDUALS_BY_GUID'
const UPDATE_FAMILIES_BY_GUID = 'UPDATE_FAMILIES_BY_GUID'
const UPDATE_PROJECT_TABLE_STATE = 'UPDATE_PROJECT_TABLE_STATE'
const UPDATE_PROJECT = 'UPDATE_PROJECT'

// action creators - individuals and families
export const updateIndividualsByGuid = individualsByGuid => ({ type: UPDATE_INDIVIDUALS_BY_GUID, updatesById: individualsByGuid })
export const updateFamiliesByGuid = familiesByGuid => ({ type: UPDATE_FAMILIES_BY_GUID, updatesById: familiesByGuid })
export const updateProject = project => ({ type: UPDATE_PROJECT, updates: project })

// action creators - projectTableState
export const updateFamiliesFilter = familiesFilter => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { familiesFilter } })
export const updateFamiliesSortOrder = familiesSortOrder => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { familiesSortOrder } })
export const updateFamiliesSortDirection = familiesSortDirection => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { familiesSortDirection } })
export const updateShowDetails = showDetails => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { showDetails } })

const rootReducer = combineReducers({
  familiesByGuid: createObjectsByIdReducer(UPDATE_FAMILIES_BY_GUID),
  individualsByGuid: createObjectsByIdReducer(UPDATE_INDIVIDUALS_BY_GUID),
  samplesByGuid: zeroActionsReducer,
  datasetsByGuid: zeroActionsReducer,
  project: createSingleObjectReducer(UPDATE_PROJECT, {}, true),
  user: zeroActionsReducer,
  projectTableState: createSingleObjectReducer(UPDATE_PROJECT_TABLE_STATE, {
    familiesFilter: SHOW_ALL,
    familiesSortOrder: SORT_BY_FAMILY_NAME,
    familiesSortDirection: 1,
    showDetails: true,
  }, false),

  ...editProjectModalState,
  ...pedigreeImageZoomModalState,
  ...phenoTipsModalState,
  ...textEditorModalState,
  ...addOrEditIndividualsModalState,
})


export default rootReducer


// basic selectors
export const getFamiliesByGuid = state => state.familiesByGuid
export const getIndividualsByGuid = state => state.individualsByGuid
export const getSamplesByGuid = state => state.samplesByGuid
export const getDatasetsByGuid = state => state.datasetsByGuid
export const getProject = state => state.project
export const getUser = state => state.user
export const getProjectTableState = state => state.projectTableState

export const getFamiliesFilter = state => state.projectTableState.familiesFilter || SHOW_ALL
export const getFamiliesSortOrder = state => state.projectTableState.familiesSortOrder || SORT_BY_FAMILY_NAME
export const getFamiliesSortDirection = state => state.projectTableState.familiesSortDirection || 1
export const getShowDetails = state => (state.projectTableState.showDetails !== undefined ? state.projectTableState.showDetails : true)

/**
 * Returns the sections of state to save in local storage in the browser.
 *
 * @param state The full redux state object.
 *
 * @returns A copy of state with restoredState applied
 */
export const getStateToSave = state => getProjectTableState(state)

/**
 * Applies state to save in local storage in the browser.
 *
 * @param state The full redux state object.
 * @param restoredState Sections of state that have been restored from local storage.
 * @returns A copy of state with restoredState applied
 */
export const applyRestoredState = (state, restoredState) => {
  const result = { ...state, projectTableState: restoredState }
  //console.log('with restored state:\n  ', result)
  return result
}
