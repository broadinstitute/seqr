/* eslint-disable no-unused-expressions */
/* eslint-disable global-require */

import 'react-hot-loader/patch'

import React from 'react'
import ReactDOM from 'react-dom'
import { AppContainer } from 'react-hot-loader'
import { injectGlobal } from 'styled-components'

import InitialSettingsProvider from 'shared/components/setup/InitialSettingsProvider'
import ReduxInit from 'shared/components/setup/ReduxInit'

import 'semantic-ui-css/semantic-custom.css'
import 'shared/global.css'

import PedigreeImageZoomModal from 'shared/components/panel/view-pedigree-image/zoom-modal/PedigreeImageZoomModal'
import PhenotipsModal from 'shared/components/panel/view-phenotips-info/phenotips-modal/PhenotipsModal'
import EditFamiliesAndIndividualsModal from 'shared/components/panel/edit-families-and-individuals/EditFamiliesAndIndividualsModal'
import EditDatasetsModal from 'shared/components/panel/edit-datasets/EditDatasetsModal'
import EditProjectModal from 'shared/components/panel/edit-project/EditProjectModal'
import EditFamilyInfoModal from 'shared/components/panel/edit-one-of-many-families/EditFamilyInfoModal'
import EditIndividualInfoModal from 'shared/components/panel/edit-one-of-many-individuals/EditIndividualInfoModal'

import ProjectPageUI from './components/ProjectPageUI'

import rootReducer, { getStateToSave, applyRestoredState } from './redux/rootReducer'

//import { patchReactToLogLifecycleMethods } from 'shared/pages/setup/debug/LifecycleMethodsLogger'

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
`

/*
if (process.env.NODE_ENV !== 'production') {
  const { whyDidYouUpdate } = require('why-did-you-update')
  whyDidYouUpdate(React)
}
*/
/**
patchReactToLogLifecycleMethods({
    excludeTypes: [
      'Connect(RichTextEditorModal)',
      'Ref',
      'Icon',
      'styled.div',
    ],
    excludeMethods: [
      'componentWillMount',
    ],
    showTimingInfo: false,
  }
)
*/

// render top-level component
ReactDOM.render(
  <AppContainer>
    <InitialSettingsProvider>
      <ReduxInit storeName="projectpage" rootReducer={rootReducer} getStateToSave={getStateToSave} applyRestoredState={applyRestoredState}>

        <ProjectPageUI />
        <EditProjectModal />
        <PedigreeImageZoomModal />
        <PhenotipsModal />
        <EditFamilyInfoModal />
        <EditIndividualInfoModal />
        <EditFamiliesAndIndividualsModal />
        <EditDatasetsModal />

        {/*
          <EditIndividualsForm />
        */}

      </ReduxInit>
    </InitialSettingsProvider>
  </AppContainer>,
  document.getElementById('reactjs-root'),
)
