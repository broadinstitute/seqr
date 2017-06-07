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
import 'shared/global.css'

import EditFamilyInfoModal from './components/table-body/family/EditFamilyInfoModal'
import EditIndividualInfoModal from './components/table-body/individual/EditIndividualInfoModal'
import CaseReviewBreadCrumbs from './components/CaseReviewBreadCrumbs'
import CaseReviewTable from './components/CaseReviewTable'

import rootReducer, { getStateToSave, applyRestoredState } from './reducers/rootReducer'

import './casereview.css'

//render top-level component
ReactDOM.render(
  <PerfProfiler enableWhyDidYouUpdate={false} enableVisualizeRender={false}>
    <AppContainer>
      <InitialSettingsProvider>
        <ReduxInit storeName="casereview" rootReducer={rootReducer} getStateToSave={getStateToSave} applyRestoredState={applyRestoredState}>
          <BaseLayout>
            <CaseReviewBreadCrumbs />
            <CaseReviewTable />
          </BaseLayout>

          <EditFamilyInfoModal />
          <EditIndividualInfoModal />
          <PedigreeImageZoomModal />
          <PhenotipsModal />
        </ReduxInit>
      </InitialSettingsProvider>
    </AppContainer>
  </PerfProfiler>,
  document.getElementById('reactjs-root'),
)
