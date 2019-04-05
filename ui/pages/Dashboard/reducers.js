import { combineReducers } from 'redux'
import { createSingleObjectReducer } from '../../redux/utils/reducerFactories'
import { SHOW_ALL } from './constants'

/**
 * Action creator and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
 */

// actions
const UPDATE_PROJECT_TABLE_STATE = 'UPDATE_PROJECT_TABLE_STATE'

// action creators
export const updateFilter = filter => ({ type: UPDATE_PROJECT_TABLE_STATE, updates: { filter } })

// root reducer
export const reducers = {
  projectsTableState: createSingleObjectReducer(UPDATE_PROJECT_TABLE_STATE, { filter: SHOW_ALL }, false),
}
const rootReducer = combineReducers(reducers)

export default rootReducer

// basic selectors
export const getProjectFilter = state => state.projectsTableState.filter
