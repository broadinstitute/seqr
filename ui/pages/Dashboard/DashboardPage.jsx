import React from 'react'
import ReactDOM from 'react-dom'
import rootReducer from './reducers/rootReducer'
import InitialSettingsProvider from '../../shared/components/setup/InitialSettingsProvider'
import ReduxInit from '../../shared/components/setup/ReduxInit'
import BaseLayout from './containers/BaseLayout'
import ProjectsTable from './containers/ProjectsTable'


ReactDOM.render(
  <InitialSettingsProvider>
    <ReduxInit storeName="Dashboard" rootReducer={rootReducer}>
      <BaseLayout>
        <ProjectsTable />
      </BaseLayout>
    </ReduxInit>
  </InitialSettingsProvider>,
  document.getElementById('reactjs-root'),
)

