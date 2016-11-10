import { createStore, applyMiddleware, compose } from 'redux'
import { loadState, saveState } from './localStorage'
import throttle from 'lodash/throttle'
import thunk from 'redux-thunk'

export const configureStore = (
    label = "GlobalStore",
    rootReducer = (state, action) => state,
    initialState = {}) => {

    if(initialState) {
        console.log("Initializing to ", initialState)
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

    window.reduxStore = store //save it globally

    return store
}

