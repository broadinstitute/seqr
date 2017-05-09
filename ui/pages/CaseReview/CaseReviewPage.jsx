/* eslint-disable */
import React from 'react'
import ReactDOM from 'react-dom'
import { AppContainer } from 'react-hot-loader'

import InitialSettingsProvider from 'shared/components/setup/InitialSettingsProvider'
import PerfProfiler from 'shared/components/setup/PerfProfiler'
import ReduxInit from 'shared/components/setup/ReduxInit'
import BaseLayout from 'shared/components/page/BaseLayout'
import PedigreeImageZoomModal from 'shared/components/panel/pedigree-image-zoom-modal/PedigreeImageZoomModal'
import PhenotipsModal from 'shared/components/panel/phenotips-modal/PhenotipsModal'
import createRichTextEditorModal from 'shared/components/panel/rich-text-editor-modal/RichTextEditorModal'

import 'shared/global.css'

import CaseReviewBreadCrumbs from './components/CaseReviewBreadCrumbs'
import CaseReviewTable from './components/CaseReviewTable'

import rootReducer, { getStateToSave, applyRestoredState, updateFamiliesByGuid } from './reducers/rootReducer'

import './casereview.css'

//init RichTextEditorModal dialog
const onSave = (responseJson) => { updateFamiliesByGuid(responseJson) }
const RichTextEditorModal = createRichTextEditorModal() //onSave

// render top-level component
ReactDOM.render(
  <PerfProfiler enableWhyDidYouUpdate={false} enableVisualizeRender={false}>
    <AppContainer>
      <InitialSettingsProvider>
        <ReduxInit storeName="casereview" rootReducer={rootReducer} getStateToSave={getStateToSave} applyRestoredState={applyRestoredState}>
          <BaseLayout>
            <CaseReviewBreadCrumbs />
            <CaseReviewTable />
          </BaseLayout>
          <RichTextEditorModal />
          <PedigreeImageZoomModal />
          <PhenotipsModal />
        </ReduxInit>
      </InitialSettingsProvider>
    </AppContainer>
  </PerfProfiler>,
  document.getElementById('reactjs-root'),
)
