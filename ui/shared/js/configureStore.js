import { createStore, applyMiddleware } from 'redux'
import thunk from 'redux-thunk'

//import { loadState, saveState } from './localStorage'
//import throttle from 'lodash/throttle'

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

  /*
  store.subscribe(throttle(() => {
      saveState(label, store.getState())
  }, 200))
  */

  return store
}

