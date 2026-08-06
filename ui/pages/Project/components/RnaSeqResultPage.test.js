import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import { RNASEQ_JUNCTION_PADDING } from 'shared/utils/constants'
import { mockFetchRejection, flushAll } from 'shared/utils/testHelpers'
import RnaSeqResultPage from './RnaSeqResultPage'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

// RnaSeqOutliers draws its scatterplot with d3 on mount, which the project's jest config stubs out
// (see RnaSeqOutliers.test.js); it's covered by its own test in isolation, so double it here to
// focus this test on RnaSeqResultPage's own tissue-selection/composition logic
jest.mock('./RnaSeqOutliers', () => function MockRnaSeqOutliers({ title }) {
  return <div className="mock-rna-seq-outliers">{title}</div>
})

configure({ adapter: new Adapter() })

test('renders a single tissue type as plain text and the outlier plot for it', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <RnaSeqResultPage match={{ params: { individualGuid: 'I021476_na19678_1' } }} />
    </Provider>,
  )

  expect(wrapper.find('Dropdown').exists()).toBe(false)
  expect(wrapper.text()).toContain('Tissue type: Muscle, Sequencing Product: TruSeq')
  // RnaSeqOutliers itself is React.lazy-loaded and covered by its own test; this just confirms
  // RnaSeqResultPage decided to render a plot section at all for the matching tissue/sequencing type
  expect(wrapper.find('Suspense').exists()).toBe(true)
})

test('renders a dropdown when there is more than one tissue/sequencing type', () => {
  const multiTissueState = {
    ...STATE_WITH_2_FAMILIES,
    rnaSeqDataByIndividual: {
      ...STATE_WITH_2_FAMILIES.rnaSeqDataByIndividual,
      I021476_na19678_1: {
        ...STATE_WITH_2_FAMILIES.rnaSeqDataByIndividual.I021476_na19678_1,
        outliers: {
          ...STATE_WITH_2_FAMILIES.rnaSeqDataByIndividual.I021476_na19678_1.outliers,
          ENSG00000228198: [
            ...STATE_WITH_2_FAMILIES.rnaSeqDataByIndividual.I021476_na19678_1.outliers.ENSG00000228198,
            {
              geneId: 'ENSG00000228198', isSignificant: true, pValue: 0.001, zScore: -4, tissueType: 'F', sequencingType: 'W',
            },
          ],
        },
      },
    },
  }
  const store = configureStore([thunk])(multiTissueState)
  const wrapper = mount(
    <Provider store={store}>
      <RnaSeqResultPage match={{ params: { individualGuid: 'I021476_na19678_1' } }} />
    </Provider>,
  )

  expect(wrapper.find('Dropdown').exists()).toBe(true)
  const options = wrapper.find('Dropdown').prop('options').map(o => o.value)
  expect(options).toEqual(['M-T', 'F-W'])

  wrapper.find('Dropdown').props().onChange(null, { value: 'F-W' })
  wrapper.update()
  expect(wrapper.find('Dropdown').prop('value')).toEqual('F-W')
})

test('renders no splice junction outlier table when there is no significant junction data', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <RnaSeqResultPage match={{ params: { individualGuid: 'I021474_na19679_1' } }} />
    </Provider>,
  )

  expect(wrapper.find('DataTable').exists()).toBe(false)
})

test('renders the splice junction outlier plot and table when there is significant junction data', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <RnaSeqResultPage match={{ params: { individualGuid: 'I021476_na19678_1' } }} />
    </Provider>,
  )

  expect(wrapper.find('GridColumn').length).toEqual(2)
  expect(wrapper.find('.mock-rna-seq-outliers').last().text()).toEqual('Splice Junction Outliers')
  expect(wrapper.find('DataTable').exists()).toBe(true)
})

test('does not re-request rna seq data when outliers include a non-significant entry and splice outliers are already loaded', async () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  mount(
    <Provider store={store}>
      <RnaSeqResultPage match={{ params: { individualGuid: 'I021474_na19679_1' } }} />
    </Provider>,
  )
  await flushAll()

  expect(fetch).not.toHaveBeenCalled()
})

test('requests rna seq data for an individual with none loaded yet', async () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)

  mount(
    <Provider store={store}>
      <RnaSeqResultPage match={{ params: { individualGuid: 'I021475_na19675_1' } }} />
    </Provider>,
  )
  await flushAll()

  expect(fetch.mock.calls.some(([url]) => url.startsWith('/api/individual/I021475_na19675_1/rna_seq_data'))).toBe(true)
})

test('dispatches an error action when the RNA-seq data request fails', async () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  mockFetchRejection(new Error('rna seq data request failed'))

  mount(
    <Provider store={store}>
      <RnaSeqResultPage match={{ params: { individualGuid: 'I021476_na19678_1' } }} />
    </Provider>,
  )
  await flushAll()

  expect(store.getActions()).toContainEqual(
    expect.objectContaining({ type: 'RECEIVE_DATA', error: 'rna seq data request failed' }),
  )
})

test('computes plot locations for expression and splice junction outliers', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <RnaSeqResultPage match={{ params: { individualGuid: 'I021476_na19678_1' } }} />
    </Provider>,
  )

  const [expressionConfig, spliceConfig] = wrapper.find('MockRnaSeqOutliers').map(node => node.props())

  expect(expressionConfig.getLocation({ geneId: 'ENSG00000228198' })).toEqual('ENSG00000228198')
  expect(spliceConfig.getLocation({ chrom: '1', start: 1000, end: 2000 })).toEqual(
    `1:${1000 - RNASEQ_JUNCTION_PADDING}-${2000 + RNASEQ_JUNCTION_PADDING}`,
  )
})

test('renders empty page missing per-individual data', () => {
  const store = configureStore([thunk])({ ...STATE_WITH_2_FAMILIES, rnaSeqDataByIndividual: {} } )
  const wrapper = mount(
    <Provider store={store}>
      <RnaSeqResultPage match={{ params: { individualGuid: 'I021476_na19678_1' } }} />
    </Provider>,
  )

  expect(wrapper.text()).toEqual('Error 404: Page Not Found')
})
