import { createStore, applyMiddleware, compose } from 'redux'
import thunkMiddleware from 'redux-thunk'

import { loadState, saveState } from 'shared/utils/localStorage'
import reduxSearchEnhancer from './reduxSearchEnhancer'


const env = process.env.NODE_ENV || 'development'
console.log('ENV: ', env)

const PERSISTING_STATE = [
  'projectsTableState', 'familyTableState', 'savedVariantTableState', 'variantSearchDisplay', 'searchesByHash',
]

const persistStoreMiddleware = store => next => (action) => {
  const result = next(action)
  const nextState = store.getState()
  PERSISTING_STATE.forEach((key) => { saveState(key, nextState[key]) })
  return result
}

const enhancer = compose(
  applyMiddleware(thunkMiddleware, persistStoreMiddleware),
  reduxSearchEnhancer,
)


/**
 * Initialize the Redux store
 * @param rootReducer
 * @param initialState
 * @returns {*}
 */
export const configureStore = (
  rootReducer = state => state,
  initialState = {},
) => {

  PERSISTING_STATE.forEach((key) => { initialState[key] = loadState(key) })

  console.log('Creating store with initial state:')
  console.log(initialState)

  return createStore(rootReducer, initialState, enhancer)
}
