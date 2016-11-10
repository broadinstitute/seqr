import React from 'react';
import ReactDOM from 'react-dom';

import rootReducer from './reducers/rootReducer'

import Root from '../../shared/components/Root'
import PageHeader from './components/PageHeader'
import FamiliesAndIndividuals from './components/FamiliesAndIndividuals'
import { configureStore } from '../../shared/js/configureStore'

const initalState = window.initialJSON;

const store = configureStore('CaseReview', rootReducer, initalState)

ReactDOM.render(
    <Root store={store}><div>
        <PageHeader />
        <FamiliesAndIndividuals />
    </div><br/></Root>,
    document.getElementById('reactjs-root')
)
