import React from 'react';
import ReactDOM from 'react-dom';
import { Router, Route, hashHistory } from 'react-router'

import ViewSubmissions from './components/view-submissions';
import ViewSubmission from './components/view-submission';
import NewSubmission from './components/new-submission';
import BaseLayout from '../../components/base-layout'

ReactDOM.render(
    <BaseLayout>
        <Router history={hashHistory}>
            <Route path="/" component={ViewSubmissions} />
            <Route path="/new" component={NewSubmission} />
            <Route path="/view-submission/:submissionId" component={ViewSubmission} />
        </Router>
    </BaseLayout>,

    document.getElementById('reactjs-root')
)
