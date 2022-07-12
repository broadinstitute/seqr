import { createStore, applyMiddleware, compose } from 'redux'
import thunkMiddleware from 'redux-thunk'

import { loadState, saveState } from 'shared/utils/localStorage'

const PERSISTING_STATE = [
  'projectsTableState', 'familyTableState', 'savedVariantTableState', 'variantSearchDisplay', 'searchesByHash',
  'familyTableFilterState',
]

const persistStoreMiddleware = store => next => (action) => {
  const result = next(action)
  const nextState = store.getState()
  PERSISTING_STATE.forEach((key) => { saveState(key, nextState[key]) })
  return result
}

const enhancer = compose(
  applyMiddleware(thunkMiddleware, persistStoreMiddleware),
)

/**
 * Initialize the Redux store
 * @param rootReducer
 * @param initialState
 * @returns {*}
 */
export default (
  rootReducer = state => state,
  initialState = {},
) => {
  const persistedInitialState = PERSISTING_STATE.reduce((acc, key) => ({ ...acc, [key]: loadState(key) }), initialState)

  console.log('Creating store with initial state:', persistedInitialState) // eslint-disable-line no-console

  return createStore(rootReducer, persistedInitialState, enhancer)
}
