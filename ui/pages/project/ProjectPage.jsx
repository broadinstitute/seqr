import React from 'react'
import ReactDOM from 'react-dom'
import rootReducer, { getStateToSave, applyRestoredState } from './reducers/rootReducer'
import InitialSettingsProvider from '../../shared/components/setup/InitialSettingsProvider'
import ReduxInit from '../../shared/components/setup/ReduxInit'
import BaseLayout from './components/BaseLayout'
import FamiliesTable from './components/FamiliesTable'
import EditFamilyInfoModal from './components/EditFamilyInfoModal'
import PerfProfiler from '../../shared/components/setup/PerfProfiler'

import '../../shared/global.css'
import './projectpage.css'

ReactDOM.render(
  <InitialSettingsProvider>
    <ReduxInit storeName="Project" rootReducer={rootReducer} getStateToSave={getStateToSave} applyRestoredState={applyRestoredState}>
      <PerfProfiler enableWhyDidYouUpdate={false} enableVisualizeRender={false}>
        <BaseLayout>
          <div>
            <FamiliesTable />
            <EditFamilyInfoModal />
          </div>
        </BaseLayout>
      </PerfProfiler>
    </ReduxInit>
  </InitialSettingsProvider>,
  document.getElementById('reactjs-root'),
)

ReactDOM.render(
  <div>
    <pre>
      Project
      - name
      - created date

      [Add Individuals button]
         - dialog:
            add individuals manually
               - family id, individual id,
          or upload

      - you accessed most recently
        [Create Project button]

      Datasets
      - Datasets that you've uploaded

      Gene Lists
      - Gene lists you've uploaded

    </pre>
  </div>,
  document.getElementById('reactjs-root'),
)

