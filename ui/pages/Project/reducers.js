import { combineReducers } from 'redux'
import { createSingleObjectReducer } from 'redux/utils/reducerFactories'

import { SHOW_ALL, SORT_BY_FAMILY_NAME } from './constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

// familyTableState
const UPDATE_FAMILY_TABLE_STATE = 'UPDATE_FAMILY_TABLE_STATE'


// familyTableState - reducer, actions, and selectors
export const reducers = {
  familyTableState: createSingleObjectReducer(UPDATE_FAMILY_TABLE_STATE, {
    currentPage: 1,
    recordsPerPage: 10,
    familiesFilter: SHOW_ALL,
    familiesSortOrder: SORT_BY_FAMILY_NAME,
    familiesSortDirection: 1,
    showDetails: true,
  }, false),
}

export const setCurrentPage = currentPage => ({ type: UPDATE_FAMILY_TABLE_STATE, updates: { currentPage } })
export const setRecordsPerPage = recordsPerPage => ({ type: UPDATE_FAMILY_TABLE_STATE, updates: { recordsPerPage } })

export const updateFamiliesFilter = familiesFilter => ({ type: UPDATE_FAMILY_TABLE_STATE, updates: { familiesFilter } })
export const updateFamiliesSortOrder = familiesSortOrder => ({ type: UPDATE_FAMILY_TABLE_STATE, updates: { familiesSortOrder } })
export const updateFamiliesSortDirection = familiesSortDirection => ({ type: UPDATE_FAMILY_TABLE_STATE, updates: { familiesSortDirection } })
export const updateShowDetails = showDetails => ({ type: UPDATE_FAMILY_TABLE_STATE, updates: { showDetails } })

export const getProjectTableState = state => state.familyTableState
export const getProjectTablePage = state => state.familyTableState.currentPage || 1
export const getProjectTableRecordsPerPage = state => Math.min(state.familyTableState.recordsPerPage, 10) || 10

export const getFamiliesFilter = state => state.familyTableState.familiesFilter || SHOW_ALL
export const getFamiliesSortOrder = state => state.familyTableState.familiesSortOrder || SORT_BY_FAMILY_NAME
export const getFamiliesSortDirection = state => state.familyTableState.familiesSortDirection || 1
export const getShowDetails = state => (state.familyTableState.showDetails !== undefined ? state.familyTableState.showDetails : true)


// root reducer
const rootReducer = combineReducers(reducers)

export default rootReducer
