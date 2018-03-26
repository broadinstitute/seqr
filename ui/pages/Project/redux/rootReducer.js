import { combineReducers } from 'redux'
import { createSingleObjectReducer } from 'redux/utils/reducerFactories'
import {
  immutableUserState,
  projectState,
  familiesByGuidState,
  individualsByGuidState,
  immutableSamplesByGuidState,
  immutableDatasetsByGuidState,
} from 'redux/utils/commonDataActionsAndSelectors'
import { pedigreeImageZoomModalState } from 'shared/components/panel/view-pedigree-image/zoom-modal/PedigreeImageZoomModal-redux'
import { phenotipsModalState } from 'shared/components/panel/view-phenotips-info/phenotips-modal/PhenotipsModal-redux'
import { richTextEditorModalState } from 'shared/components/modal/text-editor-modal/RichTextEditorModal-redux'
import { addOrEditIndividualsModalState } from 'shared/components/panel/edit-families-and-individuals/EditFamiliesAndIndividualsModal-redux'
import { addOrEditDatasetsModalState } from 'shared/components/panel/edit-datasets/EditDatasetsModal-redux'
import { editProjectModalState } from 'shared/components/panel/edit-project/EditProjectModal-redux'

import { SHOW_ALL, SORT_BY_FAMILY_NAME } from '../constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

// projectTableState
const UPDATE_PROJECT_TABLE_STATE = 'UPDATE_PROJECT_TABLE_STATE'


// projectTableState - reducer, actions, and selectors
const projectTableState = {
  projectTableState: createSingleObjectReducer(UPDATE_PROJECT_TABLE_STATE, {
    currentPage: 1,
    recordsPerPage: 200,
    familiesFilter: SHOW_ALL,
    familiesSortOrder: SORT_BY_FAMILY_NAME,
    familiesSortDirection: 1,
    showDetails: true,
  }, false),
}

export const setCurrentPage = currentPage => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { currentPage } })
export const setRecordsPerPage = recordsPerPage => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { recordsPerPage } })

export const updateFamiliesFilter = familiesFilter => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { familiesFilter } })
export const updateFamiliesSortOrder = familiesSortOrder => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { familiesSortOrder } })
export const updateFamiliesSortDirection = familiesSortDirection => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { familiesSortDirection } })
export const updateShowDetails = showDetails => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { showDetails } })

export const getProjectTableState = state => state.projectTableState
export const getProjectTablePage = state => state.projectTableState.currentPage || 1
export const getProjectTableRecordsPerPage = state => state.projectTableState.recordsPerPage || 200

export const getFamiliesFilter = state => state.projectTableState.familiesFilter || SHOW_ALL
export const getFamiliesSortOrder = state => state.projectTableState.familiesSortOrder || SORT_BY_FAMILY_NAME
export const getFamiliesSortDirection = state => state.projectTableState.familiesSortDirection || 1
export const getShowDetails = state => (state.projectTableState.showDetails !== undefined ? state.projectTableState.showDetails : true)


// root reducer
const rootReducer = combineReducers({
  ...immutableUserState,
  ...projectState,
  ...familiesByGuidState,
  ...individualsByGuidState,
  ...immutableSamplesByGuidState,
  ...immutableDatasetsByGuidState,
  ...projectTableState,
  ...editProjectModalState,
  ...pedigreeImageZoomModalState,
  ...phenotipsModalState,
  ...richTextEditorModalState,
  ...addOrEditIndividualsModalState,
  ...addOrEditDatasetsModalState,
})

export default rootReducer


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
