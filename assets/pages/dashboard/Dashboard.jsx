import React from 'react';
import ReactDOM from 'react-dom';

import BaseLayout from '../../shared/components/Root'

ReactDOM.render(
    <Root>
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

