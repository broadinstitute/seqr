import 'react-hot-loader/patch'

import React from 'react'
import ReactDOM from 'react-dom'
import { AppContainer } from 'react-hot-loader'

import InitialSettingsProvider from 'shared/components/setup/InitialSettingsProvider'
import ReduxInit from 'shared/components/setup/ReduxInit'
import BaseLayout from 'shared/components/page/BaseLayout'

import DocumentTitle from 'react-document-title'

import 'shared/global.css'

import VariantTable from './components/VariantTable'

import rootReducer, { getStateToSave, applyRestoredState } from './reducers/rootReducer'
import './variantsearch.css'

ReactDOM.render(
  <AppContainer>
    <InitialSettingsProvider>
      <ReduxInit storeName="variantsearch" rootReducer={rootReducer} getStateToSave={getStateToSave} applyRestoredState={applyRestoredState}>
        <BaseLayout>
          <VariantSearchUI />
        </BaseLayout>
      </ReduxInit>
    </InitialSettingsProvider>,
  </AppContainer>,

  document.getElementById('reactjs-root'),
)
