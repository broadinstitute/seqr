import React from 'react';
import ReactDOM from 'react-dom';

import Root from '../../shared/components/Root'
import BreadCrumbs from '../../shared/components/BreadCrumbs'
import ProjectsTable from './components/ProjectsTable'

import { configureStore } from '../../shared/js/configureStore'

const store = configureStore("Dashboard")

ReactDOM.render(
    <Root store={store} >
        <div className="ui grid">
            <div className="row" style={{padding:"0px"}}>
                <div className="sixteen wide column">
                    <BreadCrumbs breadcrumbs={["Dashboard"]} />
                </div>
            </div>
            <div className="row">
                <ProjectsTable />
            </div>
        </div>
    </Root>,
    document.getElementById('reactjs-root')
)

