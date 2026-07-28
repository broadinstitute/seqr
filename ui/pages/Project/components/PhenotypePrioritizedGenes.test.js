import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import { mockFetchRejection, flushAll } from 'shared/utils/testHelpers'
import PhenotypePrioritizedGenes from './PhenotypePrioritizedGenes'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

test('renders the phenotype-prioritized gene table for an individual', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <PhenotypePrioritizedGenes individualGuid="I021476_na19678_1" familyGuid="F011652_1" />
    </Provider>,
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
    </Provider>,
  )

  expect(wrapper.find('DataTable').exists()).toBe(false)
  expect(wrapper.text()).toContain('Error 404')
})

test('does not re-request phenotype gene scores when enough are already loaded for a tool', async () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    phenotypeGeneScoresByIndividual: {
      I021476_na19678_1: {
        ENSG00000228198: {
          lirical: new Array(10).fill({
            diseaseId: 'OMIM:618460', diseaseName: 'Khan-Khan-Katsanis syndrome', rank: 1, scores: {},
          }),
        },
      },
    },
  }
  const store = configureStore([thunk])(state)
  mount(
    <Provider store={store}>
      <PhenotypePrioritizedGenes individualGuid="I021476_na19678_1" familyGuid="F011652_1" />
    </Provider>,
  )
  await flushAll()

  expect(fetch).not.toHaveBeenCalled()
})

test('dispatches an error action when the phenotype gene scores request fails', async () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  mockFetchRejection(new Error('phenotype gene scores request failed'))

  mount(
    <Provider store={store}>
      <PhenotypePrioritizedGenes individualGuid="I021475_na19675_2" familyGuid="F011652_1" />
    </Provider>,
  )
  await flushAll()

  expect(store.getActions()).toContainEqual(
    expect.objectContaining({ type: 'RECEIVE_DATA', error: 'phenotype gene scores request failed' }),
  )
})
