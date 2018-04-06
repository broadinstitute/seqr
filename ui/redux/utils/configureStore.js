/* eslint-disable no-underscore-dangle */

import { createStore, applyMiddleware } from 'redux'
import thunkMiddleware from 'redux-thunk'

import { loadState, saveState } from 'shared/utils/localStorage'


const env = process.env.NODE_ENV || 'development'
console.log('ENV: ', env)

/**
 * Initialize the Redux store
 * @param rootReducer
 * @param initialState
 * @returns {*}
 */
export const configureStore = (
  rootReducer = state => state,
  initialState = {},
  persistingStates = [],
) => {

  const persistStoreMiddleware = store => next => (action) => {
    const result = next(action)
    const nextState = store.getState()
    persistingStates.forEach((key) => { saveState(key, nextState[key]) })
    return result
  }

  persistingStates.forEach((key) => { initialState[key] = loadState(key) })

  console.log('Creating store with initial state:')
  console.log(initialState)

  const store = createStore(
    rootReducer,
    initialState,
    applyMiddleware(thunkMiddleware, persistStoreMiddleware),
  )

  return store
}
