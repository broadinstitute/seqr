import React from 'react'
import ReactDOM from 'react-dom'
import DocumentTitle from 'react-document-title'

import rootReducer, { getStateToSave, applyRestoredState } from './reducers/rootReducer'
import InitialSettingsProvider from '../../shared/components/setup/InitialSettingsProvider'
import ReduxInit from '../../shared/components/setup/ReduxInit'
import BaseLayout from './components/BaseLayout'
import ProjectsTable from './components/ProjectsTable'
import PerfProfiler from '../../shared/components/setup/PerfProfiler'
import EditProjectInfoModal from './components/EditProjectInfoModal'
import EditProjectCategoriesModal from './components/EditProjectCategoriesModal'
import AddProjectModal from './components/AddProjectModal'
import '../../shared/global.css'
import './dashboard.css'

ReactDOM.render(
  <InitialSettingsProvider>
    <ReduxInit storeName="Dashboard" rootReducer={rootReducer} getStateToSave={getStateToSave} applyRestoredState={applyRestoredState}>
      <BaseLayout>
        <PerfProfiler enableWhyDidYouUpdate={false} enableVisualizeRender={false}>
          <div>
            <DocumentTitle title="seqr: dashboard" />
            <ProjectsTable />

            <EditProjectInfoModal />
            <EditProjectCategoriesModal />
            <AddProjectModal />
          </div>
        </PerfProfiler>
      </BaseLayout>
    </ReduxInit>
  </InitialSettingsProvider>,
  document.getElementById('reactjs-root'),
)
