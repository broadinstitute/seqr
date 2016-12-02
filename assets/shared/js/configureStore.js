import { createStore, applyMiddleware, compose } from 'redux'
import { loadState, saveState } from './localStorage'
import throttle from 'lodash/throttle'
import thunk from 'redux-thunk'

export const configureStore = (
    label = "GlobalStore",
    rootReducer = (state, action) => state,
    initialState = {}
) => {

    if(initialState) {
        console.log(label, " initial state = ", initialState)
    }
    //const persistedState = loadState(label)

    const composeEnhancers = window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || compose;
    const store = createStore(
        rootReducer,
        initialState,
        composeEnhancers(applyMiddleware(thunk))
    )
    /*
    store.subscribe(throttle(() => {
        saveState(label, store.getState())
    }, 200)) */

    window.reduxStore = store  // global variable to allow the html page to do some further async initialization, etc.

    return store
}

