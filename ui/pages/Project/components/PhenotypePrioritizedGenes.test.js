import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import PhenotypePrioritizedGenes from './PhenotypePrioritizedGenes'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

// Loading is triggered on mount via a thunk action creator; mock the underlying HTTP request so
// mounting does not attempt a real network call
jest.mock('shared/utils/httpRequestHelper', () => ({
  ...jest.requireActual('shared/utils/httpRequestHelper'),
  HttpRequestHelper: jest.fn().mockImplementation(() => ({ get: jest.fn(), post: jest.fn() })),
}))

configure({ adapter: new Adapter() })

test('renders the phenotype-prioritized gene table for an individual', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
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

test('renders without error for an individual with no phenotype-prioritized genes loaded', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <PhenotypePrioritizedGenes individualGuid="I021475_na19675_2" familyGuid="F011652_1" />
    </Provider>
  )

  expect(wrapper.find('DataTable').exists()).toBe(false)
  expect(wrapper.text()).toContain('Error 404')
})
