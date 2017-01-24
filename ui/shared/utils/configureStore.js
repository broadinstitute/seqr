import { createStore, applyMiddleware } from 'redux'
import thunk from 'redux-thunk'

/**
 *
 * @param label
 * @param rootReducer
 * @param initialState
 * @returns {*}
 */
export const configureStore = (
  label = 'GlobalStore',
  rootReducer = state => state,
  initialState = {},
) => {
  //const persistedState = loadState(label)

  const store = createStore(
    rootReducer,
    initialState,
    applyMiddleware(thunk),
  )

  return store
}

