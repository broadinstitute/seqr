/* eslint-disable no-unused-expressions */

import 'react-hot-loader/patch'

import React from 'react'
import ReactDOM from 'react-dom'
import { AppContainer } from 'react-hot-loader'
import { injectGlobal } from 'styled-components'

import InitialSettingsProvider from 'shared/components/setup/InitialSettingsProvider'
import ReduxInit from 'shared/components/setup/ReduxInit'
import BaseLayout from 'shared/components/page/BaseLayout'
import PedigreeImageZoomModal from 'shared/components/panel/view-pedigree-image/zoom-modal/PedigreeImageZoomModal'
import PhenotipsModal from 'shared/components/panel/view-phenotips-info/phenotips-modal/PhenotipsModal'
import EditFamilyInfoModal from 'shared/components/panel/edit-one-of-many-families/EditFamilyInfoModal'
import EditIndividualInfoModal from 'shared/components/panel/edit-one-of-many-individuals/EditIndividualInfoModal'

import 'semantic-ui-css/semantic-custom.css'
import 'shared/global.css'

import CaseReviewBreadCrumbs from './components/CaseReviewBreadCrumbs'
import CaseReviewTable from './components/CaseReviewTable'
import rootReducer, { getStateToSave, applyRestoredState } from './redux/rootReducer'

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
        <PedigreeImageZoomModal />
        <PhenotipsModal />
        <EditFamilyInfoModal />
        <EditIndividualInfoModal />
      </ReduxInit>
    </InitialSettingsProvider>
  </AppContainer>,
  document.getElementById('reactjs-root'),
)
