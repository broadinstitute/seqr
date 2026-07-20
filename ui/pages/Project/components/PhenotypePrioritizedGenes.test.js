import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'

import PhenotypePrioritizedGenes from './PhenotypePrioritizedGenes'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

// Loading is triggered on mount via a thunk action creator; replace it with a no-op so mounting
// does not attempt to make a real HTTP request or require additional reducer state
jest.mock('../reducers', () => ({
  ...jest.requireActual('../reducers'),
  loadPhenotypeGeneScores: () => ({ type: 'NOOP' }),
}))

configure({ adapter: new Adapter() })

test('renders the phenotype-prioritized gene table for an individual', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <PhenotypePrioritizedGenes individualGuid="I021476_na19678_1" familyGuid="F011652_1" />
    </Provider>
  )

  expect(wrapper.find('DataTable').prop('data')).toEqual([{
    diseaseId: 'OMIM:618460',
    diseaseName: 'Khan-Khan-Katsanis syndrome',
    rank: 1,
    scores: { compositeLR: 0.066, post_test_probability: 0 },
    tool: 'lirical',
    familyGuid: 'F011652_1',
    gene: STATE_WITH_2_FAMILIES.genesById.ENSG00000228198,
    rowId: 'ENSG00000228198-lirical-OMIM:618460',
  }])
  expect(wrapper.text()).toContain('Khan-Khan-Katsanis syndrome')
  expect(wrapper.text()).toContain('lirical')
})
