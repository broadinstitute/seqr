import { createStore, applyMiddleware, compose } from 'redux'
import { loadState, saveState } from './localStorage'
import throttle from 'lodash/throttle'
import thunk from 'redux-thunk'

export const configureStore = (rootReducer, getStateToPersist) => {
    const persistedState = loadState()

    const composeEnhancers = window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || compose;
    const store = createStore(
        rootReducer,
        persistedState,
        composeEnhancers(applyMiddleware(thunk))
    )

    store.subscribe(throttle(() => {
        saveState(getStateToPersist(store.getState()))
    }, 200))

    return store
}

