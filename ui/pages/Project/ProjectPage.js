/* eslint-disable no-unused-expressions */

import 'react-hot-loader/patch'

import React from 'react'
import ReactDOM from 'react-dom'
import { AppContainer } from 'react-hot-loader'

import InitialSettingsProvider from 'shared/components/setup/InitialSettingsProvider'
import ReduxInit from 'shared/components/setup/ReduxInit'
import BaseLayout from 'shared/components/page/BaseLayout'

import PedigreeImageZoomModal from 'shared/components/panel/pedigree-image/zoom-modal/PedigreeImageZoomModal'
import PhenotipsModal from 'shared/components/panel/phenotips-view/phenotips-modal/PhenotipsModal'
import AddOrEditIndividualsModal from 'shared/components/panel/add-or-edit-individuals/AddOrEditIndividualsModal'
import EditProjectModal from 'shared/components/modal/edit-project-modal/EditProjectModal'
import { injectGlobal } from 'styled-components'

import 'shared/global.css'

import EditFamilyInfoModal from './components/table-body/family/EditFamilyInfoModal'
import EditIndividualInfoModal from './components/table-body/individual/EditIndividualInfoModal'
import ProjectTable from './components/ProjectPageUI'

import rootReducer, { getStateToSave, applyRestoredState } from './reducers/rootReducer'


injectGlobal`
  .ui.form .field {
    margin: 0;
  }
  
  .ui.form select {
    padding: 0;
  }
  
  .field {
    display: inline;
  }
  
  .mce-widget.mce-tooltip {
    display: none !important;
  }

`

// render top-level component
ReactDOM.render(
  <AppContainer>
    <InitialSettingsProvider>
      <ReduxInit storeName="projectpage" rootReducer={rootReducer} getStateToSave={getStateToSave} applyRestoredState={applyRestoredState}>
        <BaseLayout>
          {/* <ProjectBreadCrumbs /> */}
          <ProjectTable />
        </BaseLayout>

        <EditProjectModal />
        <PedigreeImageZoomModal />
        <PhenotipsModal />
        <EditFamilyInfoModal />
        <EditIndividualInfoModal />
        <AddOrEditIndividualsModal />
      </ReduxInit>
    </InitialSettingsProvider>
  </AppContainer>,
  document.getElementById('reactjs-root'),
)
