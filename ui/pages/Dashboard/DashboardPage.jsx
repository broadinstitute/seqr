import 'babel-polyfill'
import React from 'react'
import ReactDOM from 'react-dom'
import DocumentTitle from 'react-document-title'
import { AppContainer } from 'react-hot-loader'

import InitialSettingsProvider from 'shared/components/setup/InitialSettingsProvider'
import PerfProfiler from 'shared/components/setup/PerfProfiler'
import ReduxInit from 'shared/components/setup/ReduxInit'
import BaseLayout from 'shared/components/page/BaseLayout'
import 'shared/global.css'

import rootReducer, { getStateToSave, applyRestoredState } from './reducers/rootReducer'
import ProjectsTable from './components/ProjectsTable'
import AddOrEditProjectModal from './components/table-body/AddOrEditProjectModal'
import EditProjectCategoriesModal from './components/table-body/EditProjectCategoriesModal'
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
