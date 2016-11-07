import { createStore, applyMiddleware, compose } from 'redux'
import { loadState, saveState } from './localStorage'
import rootReducer from './reducers/rootReducer'
import throttle from 'lodash/throttle'
import thunk from 'redux-thunk'

export const configureStore = () => {
    const persistedState = loadState()

    const composeEnhancers = window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || compose;
    const store = createStore(
        rootReducer,
        persistedState,
        composeEnhancers(applyMiddleware(thunk))
    )

    store.subscribe(throttle(() => {
        saveState({ searchParams: store.getState().searchParams })
    }, 1000))

    return store
}

