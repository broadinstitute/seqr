import React from 'react';
import ReactDOM from 'react-dom';

import rootReducer, {getSearchParams} from './reducers/rootReducer'

import Root from '../../shared/components/Root'

import { configureStore } from '../../shared/js/configureStore'

const store = configureStore(rootReducer,
    (state) => ({searchParams: getSearchParams(state)})
)

ReactDOM.render(
    <Root store={store} />,
    document.getElementById('reactjs-root')
)
