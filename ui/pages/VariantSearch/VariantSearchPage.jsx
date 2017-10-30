import 'react-hot-loader/patch'

import React from 'react'
import ReactDOM from 'react-dom'
import { AppContainer } from 'react-hot-loader'

import InitialSettingsProvider from 'shared/components/setup/InitialSettingsProvider'
import PerfProfiler from 'shared/components/setup/PerfProfiler'
import ReduxInit from 'shared/components/setup/ReduxInit'
import BaseLayout from 'shared/components/page/BaseLayout'

import DocumentTitle from 'react-document-title'

import 'shared/global.css'

import rootReducer, { getStateToSave, applyRestoredState } from './reducers/rootReducer'
import VariantTable from './components/VariantTable'
import './variantsearch.css'

ReactDOM.render(
  <PerfProfiler enableWhyDidYouUpdate={false} enableVisualizeRender={false}>
    <AppContainer>
      <InitialSettingsProvider>
        <ReduxInit storeName="variantsearch" rootReducer={rootReducer} getStateToSave={getStateToSave} applyRestoredState={applyRestoredState}>
          <BaseLayout>
            <div>
              <DocumentTitle title="seqr: variant search" />
              <VariantTable />
            </div>
          </BaseLayout>
        </ReduxInit>
      </InitialSettingsProvider>,
    </AppContainer>
  </PerfProfiler>,
  document.getElementById('reactjs-root'),
)
