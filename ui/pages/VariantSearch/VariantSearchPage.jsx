import React from 'react'
import ReactDOM from 'react-dom'
import DocumentTitle from 'react-document-title'

import ReduxInit from 'shared/components/setup/ReduxInit'
import PerfProfiler from 'shared/components/setup/PerfProfiler'
import 'shared/global.css'

import rootReducer, { getStateToSave, applyRestoredState } from './reducers/rootReducer'
import InitialSettingsProvider from '../../shared/components/setup/InitialSettingsProvider'
import BaseLayout from './components/BaseLayout'
import VariantTable from './components/VariantTable'
import './variantsearch.css'

ReactDOM.render(
  <InitialSettingsProvider>
    <ReduxInit storeName="Dashboard" rootReducer={rootReducer} getStateToSave={getStateToSave} applyRestoredState={applyRestoredState}>
      <BaseLayout>
        <PerfProfiler enableWhyDidYouUpdate={false} enableVisualizeRender={false}>
          <div>
            <DocumentTitle title="seqr: variant search" />
            <VariantTable />
          </div>
        </PerfProfiler>
      </BaseLayout>
    </ReduxInit>
  </InitialSettingsProvider>,
  document.getElementById('reactjs-root'),
)
