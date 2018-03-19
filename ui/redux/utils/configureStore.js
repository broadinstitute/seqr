/* eslint-disable no-underscore-dangle */

import { createStore, applyMiddleware } from 'redux'
import thunkMiddleware from 'redux-thunk'

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
) => {
  console.log('Creating store with initial state:')
  console.log(initialState)

  const store = createStore(
    rootReducer,
    initialState,
    applyMiddleware(thunkMiddleware),
  )

  return store
}
