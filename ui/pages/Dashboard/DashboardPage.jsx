import React from 'react'
import ReactDOM from 'react-dom'
import DocumentTitle from 'react-document-title'
import { AppContainer } from 'react-hot-loader'

import rootReducer, { getStateToSave, applyRestoredState } from './reducers/rootReducer'
import InitialSettingsProvider from '../../shared/components/setup/InitialSettingsProvider'
import ReduxInit from '../../shared/components/setup/ReduxInit'
import BaseLayout from './components/BaseLayout'
import ProjectsTable from './components/ProjectsTable'
import PerfProfiler from '../../shared/components/setup/PerfProfiler'
import AddOrEditProjectModal from './components/AddOrEditProjectModal'
import EditProjectCategoriesModal from './components/EditProjectCategoriesModal'
import '../../shared/global.css'
import './dashboard.css'

ReactDOM.render(
  <InitialSettingsProvider>
    <ReduxInit storeName="dashboard" rootReducer={rootReducer} getStateToSave={getStateToSave} applyRestoredState={applyRestoredState}>
      <AppContainer>
        <PerfProfiler enableWhyDidYouUpdate={false} enableVisualizeRender={false}>
          <BaseLayout>
            <DocumentTitle title="seqr: dashboard" />
            <ProjectsTable />
            <AddOrEditProjectModal />
            <EditProjectCategoriesModal />
          </BaseLayout>
        </PerfProfiler>
      </AppContainer>
    </ReduxInit>
  </InitialSettingsProvider>,
  document.getElementById('reactjs-root'),
)
