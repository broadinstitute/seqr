import React from 'react';
import ReactDOM from 'react-dom';

import BaseLayout from '../../components/base-layout'
import BreadCrumbs from '../../components/bread-crumbs';
import ProjectsTable from './components/projects-table';

ReactDOM.render(
    <BaseLayout>
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
    </BaseLayout>,
    document.getElementById('reactjs-root')
)

