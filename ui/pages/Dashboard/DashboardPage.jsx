import React from 'react'
import ReactDOM from 'react-dom'
import rootReducer from './reducers/rootReducer'
import InitialSettingsProvider from '../../shared/components/setup/InitialSettingsProvider'
import ReduxInit from '../../shared/components/setup/ReduxInit'
import BaseLayout from './components/BaseLayout'
import ProjectsTable from './components/ProjectsTable'
import PerfProfiler from '../../shared/components/setup/PerfProfiler'
import EditProjectInfoModal from './components/EditProjectInfoModal'

import '../../shared/global.css'
import './dashboard.css'

ReactDOM.render(
  <InitialSettingsProvider>
    <ReduxInit storeName="Dashboard" rootReducer={rootReducer}>
      <BaseLayout>
        <PerfProfiler enableWhyDidYouUpdate={false} enableVisualizeRender={false}>
          <div>
            <ProjectsTable />
            <EditProjectInfoModal />
          </div>
        </PerfProfiler>
      </BaseLayout>
    </ReduxInit>
  </InitialSettingsProvider>,
  document.getElementById('reactjs-root'),
)

