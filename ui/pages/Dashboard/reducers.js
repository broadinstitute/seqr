import { combineReducers } from 'redux'
import { createSingleObjectReducer } from '../../redux/utils/reducerUtils'
import { SHOW_ALL, SORT_BY_PROJECT_NAME } from './constants'

/**
 * Action creator and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
 */

// actions
const UPDATE_PROJECT_TABLE_STATE = 'UPDATE_PROJECT_TABLE_STATE'

// action creators
export const updateFilter = filter => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { filter } })
export const updateSortColumn = sortColumn => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { sortColumn } })
export const updateSortDirection = sortDirection => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { sortDirection } })

// root reducer
export const reducers = {
  projectsTableState: createSingleObjectReducer(UPDATE_PROJECT_TABLE_STATE, {
    filter: SHOW_ALL, sortColumn: SORT_BY_PROJECT_NAME, sortDirection: 1,
  }, false),
}
const rootReducer = combineReducers(reducers)

export default rootReducer

// basic selectors
export const getProjectFilter = state => state.projectsTableState.filter
export const getProjectSortColumn = state => state.projectsTableState.sortColumn
export const getProjectSortDirection = state => state.projectsTableState.sortDirection
