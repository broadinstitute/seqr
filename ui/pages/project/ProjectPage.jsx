import 'babel-polyfill'
import React from 'react'
import ReactDOM from 'react-dom'
import { AppContainer } from 'react-hot-loader'

import InitialSettingsProvider from 'shared/components/setup/InitialSettingsProvider'
import PerfProfiler from 'shared/components/setup/PerfProfiler'
import ReduxInit from 'shared/components/setup/ReduxInit'
import BaseLayout from 'shared/components/page/BaseLayout'
import PedigreeImageZoomModal from 'shared/components/panel/pedigree-image/zoom-modal/PedigreeImageZoomModal'
import PhenotipsModal from 'shared/components/panel/phenotips-view/phenotips-modal/PhenotipsModal'
import EditFamiliesAndIndividualsModal from 'shared/components/panel/edit-families-and-individuals/EditFamiliesAndIndividualsModal'
import EditProjectModal from 'shared/components/modal/edit-project-modal/EditProjectModal'
import 'shared/global.css'

import EditFamilyInfoModal from './components/table-body/family/EditFamilyInfoModal'
import EditIndividualInfoModal from './components/table-body/individual/EditIndividualInfoModal'

//import ProjectBreadCrumbs from './components/ProjectBreadCrumbs'
import ProjectTable from './components/ProjectTable'

import rootReducer, { getStateToSave, applyRestoredState } from './reducers/rootReducer'

import './projectpage.css'

// render top-level component
ReactDOM.render(
  <PerfProfiler enableWhyDidYouUpdate={false} enableVisualizeRender={false}>
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
          <EditFamiliesAndIndividualsModal />
        </ReduxInit>
      </InitialSettingsProvider>
    </AppContainer>
  </PerfProfiler>,
  document.getElementById('reactjs-root'),
)
