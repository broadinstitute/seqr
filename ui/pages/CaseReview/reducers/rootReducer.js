import { combineReducers } from 'redux'
import { zeroActionsReducer, createSingleObjectReducer, createObjectsByIdReducer } from 'shared/utils/reducerUtils'
import { pedigreeImageZoomModalState } from 'shared/components/panel/pedigree-image/zoom-modal/state'
import { phenoTipsModalState } from 'shared/components/panel/phenotips-view/phenotips-modal/state'
import { richTextEditorModalState } from 'shared/components/modal/text-editor-modal/state'

import { SHOW_ALL, SORT_BY_FAMILY_NAME } from '../constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

// actions
const UPDATE_INDIVIDUALS_BY_GUID = 'UPDATE_INDIVIDUALS_BY_GUID'
const UPDATE_FAMILIES_BY_GUID = 'UPDATE_FAMILIES_BY_GUID'
const UPDATE_CASE_REVIEW_TABLE_STATE = 'UPDATE_CASE_REVIEW_TABLE_STATE'

// action creators - individuals and families
export const updateIndividualsByGuid = individualsByGuid => ({ type: UPDATE_INDIVIDUALS_BY_GUID, updatesById: individualsByGuid })
export const updateFamiliesByGuid = familiesByGuid => ({ type: UPDATE_FAMILIES_BY_GUID, updatesById: familiesByGuid })

// action creators - caseReviewTableState
export const updateFamiliesFilter = familiesFilter => ({ type: UPDATE_CASE_REVIEW_TABLE_STATE, updates: { familiesFilter } })
export const updateFamiliesSortOrder = familiesSortOrder => ({ type: UPDATE_CASE_REVIEW_TABLE_STATE, updates: { familiesSortOrder } })
export const updateFamiliesSortDirection = familiesSortDirection => ({ type: UPDATE_CASE_REVIEW_TABLE_STATE, updates: { familiesSortDirection } })
export const updateShowDetails = showDetails => ({ type: UPDATE_CASE_REVIEW_TABLE_STATE, updates: { showDetails } })


const rootReducer = combineReducers({
  familiesByGuid: createObjectsByIdReducer(UPDATE_FAMILIES_BY_GUID),
  individualsByGuid: createObjectsByIdReducer(UPDATE_INDIVIDUALS_BY_GUID),
  project: zeroActionsReducer,
  user: zeroActionsReducer,
  caseReviewTableState: createSingleObjectReducer(UPDATE_CASE_REVIEW_TABLE_STATE, {
    familiesFilter: SHOW_ALL,
    familiesSortOrder: SORT_BY_FAMILY_NAME,
    familiesSortDirection: 1,
    showDetails: true,
  }, true),

  ...pedigreeImageZoomModalState,
  ...phenoTipsModalState,
  ...richTextEditorModalState,
})

export default rootReducer

// basic selectors
export const getCaseReviewTableState = state => state.caseReviewTableState

export const getFamiliesFilter = state => state.caseReviewTableState.familiesFilter
export const getFamiliesSortOrder = state => state.caseReviewTableState.familiesSortOrder
export const getFamiliesSortDirection = state => state.caseReviewTableState.familiesSortDirection
export const getShowDetails = state => state.caseReviewTableState.showDetails

/**
 * Returns the sections of state to save in local storage in the browser.
 *
 * @param state The full redux state object.
 *
 * @returns A copy of state with restoredState applied
 */
export const getStateToSave = state => getCaseReviewTableState(state)

/**
 * Applies state to save in local storage in the browser.
 *
 * @param state The full redux state object.
 * @param restoredState Sections of state that have been restored from local storage.
 * @returns A copy of state with restoredState applied
 */
export const applyRestoredState = (state, restoredState) => {
  const result = { ...state, caseReviewTableState: restoredState }
  console.log('with restored state:\n  ', result)
  return result
}
