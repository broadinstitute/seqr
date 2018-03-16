/* eslint-disable no-unused-expressions */

import 'react-hot-loader/patch'
import React from 'react'
import ReactDOM from 'react-dom'
import DocumentTitle from 'react-document-title'
import { AppContainer } from 'react-hot-loader'
import { injectGlobal } from 'styled-components'

import InitialSettingsProvider from 'shared/components/setup/InitialSettingsProvider'
import ReduxInit from 'shared/components/setup/ReduxInit'
import BaseLayout from 'shared/components/page/BaseLayout'

import 'semantic-ui-css/semantic-custom.css'
import 'shared/global.css'

import rootReducer, { getStateToSave, applyRestoredState } from 'pages/Dashboard/redux/rootReducer'
import ProjectsTable from 'pages/Dashboard/components/ProjectsTable'
import AddOrEditProjectModal from 'pages/Dashboard/components/table-body/AddOrEditProjectModal'
import EditProjectCategoriesModal from 'pages/Dashboard/components/table-body/EditProjectCategoriesModal'


injectGlobal`
  .ui.table thead th {
    padding: 6px 3px;
    background-color: #F3F3F3;
    height: 10px;
  }
  
  .ui.form .field > label {
    text-align: left;
  }
  
  .ellipsis-menu {
    padding: 3px;
  }
  
  .ellipsis-menu:hover {
    padding: 3px;
    background-color: #fafafa;
    border-color: #ccc;
    border-radius: 3px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
  }
`

ReactDOM.render(
  <InitialSettingsProvider>
    <ReduxInit storeName="dashboard" rootReducer={rootReducer} getStateToSave={getStateToSave} applyRestoredState={applyRestoredState}>
      <AppContainer>
        <BaseLayout>
          <DocumentTitle title="seqr: home" />
          <div> NEW APP HOME PAGE</div>
          <ProjectsTable />
          <AddOrEditProjectModal />
          <EditProjectCategoriesModal />
        </BaseLayout>
      </AppContainer>
    </ReduxInit>
  </InitialSettingsProvider>,
  document.getElementById('reactjs-root'),
)
