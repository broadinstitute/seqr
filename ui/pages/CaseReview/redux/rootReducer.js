import { combineReducers } from 'redux'
import { createSingleObjectReducer } from 'redux/utils/reducerFactories'
import {
  immutableUserState,
  immutableProjectState,
  familiesByGuidState,
  individualsByGuidState,
} from 'redux/utils/commonDataActionsAndSelectors'

import { SHOW_ALL, SORT_BY_FAMILY_NAME } from '../constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

// caseReviewTableState
const UPDATE_CASE_REVIEW_TABLE_STATE = 'UPDATE_CASE_REVIEW_TABLE_STATE'

const caseReviewTableState = {
  caseReviewTableState: createSingleObjectReducer(UPDATE_CASE_REVIEW_TABLE_STATE, {
    currentPage: 1,
    recordsPerPage: 200,
    familiesFilter: SHOW_ALL,
    familiesSortOrder: SORT_BY_FAMILY_NAME,
    familiesSortDirection: 1,
    showDetails: true,
  }, true),
}
export const setCurrentPage = currentPage => ({ type: UPDATE_CASE_REVIEW_TABLE_STATE, updates: { currentPage } })
export const setRecordsPerPage = recordsPerPage => ({ type: UPDATE_CASE_REVIEW_TABLE_STATE, updates: { recordsPerPage } })

export const updateFamiliesFilter = familiesFilter => ({ type: UPDATE_CASE_REVIEW_TABLE_STATE, updates: { familiesFilter } })
export const updateFamiliesSortOrder = familiesSortOrder => ({ type: UPDATE_CASE_REVIEW_TABLE_STATE, updates: { familiesSortOrder } })
export const updateFamiliesSortDirection = familiesSortDirection => ({ type: UPDATE_CASE_REVIEW_TABLE_STATE, updates: { familiesSortDirection } })
export const updateShowDetails = showDetails => ({ type: UPDATE_CASE_REVIEW_TABLE_STATE, updates: { showDetails } })

export const getCaseReviewTableState = state => state.caseReviewTableState
export const getCaseReviewTablePage = state => state.caseReviewTableState.currentPage || 1
export const getCaseReviewTableRecordsPerPage = state => state.caseReviewTableState.recordsPerPage || 200

export const getFamiliesFilter = state => state.caseReviewTableState.familiesFilter || SHOW_ALL
export const getFamiliesSortOrder = state => state.caseReviewTableState.familiesSortOrder || SORT_BY_FAMILY_NAME
export const getFamiliesSortDirection = state => state.caseReviewTableState.familiesSortDirection || 1
export const getShowDetails = state => state.caseReviewTableState.showDetails


// root reducer
const rootReducer = combineReducers({
  ...immutableUserState,
  ...immutableProjectState,
  ...familiesByGuidState,
  ...individualsByGuidState,
  ...caseReviewTableState,
})

export default rootReducer


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
