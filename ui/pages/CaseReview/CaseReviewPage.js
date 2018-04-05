/* eslint-disable no-unused-expressions */

import 'react-hot-loader/patch'

import React from 'react'
import ReactDOM from 'react-dom'
import { AppContainer } from 'react-hot-loader'
import { injectGlobal } from 'styled-components'

import InitialSettingsProvider from 'shared/components/setup/InitialSettingsProvider'
import ReduxInit from 'shared/components/setup/ReduxInit'
import BaseLayout from 'shared/components/page/BaseLayout'

import 'semantic-ui-css/semantic-custom.css'
import 'shared/global.css'

import CaseReviewBreadCrumbs from './components/CaseReviewBreadCrumbs'
import CaseReviewTable from './CaseReviewTable'
import rootReducer, { getStateToSave, applyRestoredState } from './rootReducer'

injectGlobal`
  .table-header-column {
    width: auto !important
  }
  
  .ui.form .field {
    margin: 0;
  }
  
  .ui.form select {
    padding: 0;
  }
  
  .ui.form .checkbox-container {
    padding: 5px 0px 10px 0px;
  }
  
  .ui.form .ui.checkbox {
    padding: 3px 10px 5px 5px;
  }
  
  .field {
    display: inline;
  }
`

//render top-level component
ReactDOM.render(
  <AppContainer>
    <InitialSettingsProvider>
      <ReduxInit storeName="casereview" rootReducer={rootReducer} getStateToSave={getStateToSave} applyRestoredState={applyRestoredState}>
        <BaseLayout>
          <CaseReviewBreadCrumbs />
          <CaseReviewTable />
        </BaseLayout>
      </ReduxInit>
    </InitialSettingsProvider>
  </AppContainer>,
  document.getElementById('reactjs-root'),
)
