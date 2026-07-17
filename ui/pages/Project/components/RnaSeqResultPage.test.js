import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'

import RnaSeqResultPage from './RnaSeqResultPage'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

// Loading is triggered on mount via a thunk action creator; replace it with a no-op so mounting
// does not attempt to make a real HTTP request or require additional reducer state
jest.mock('../reducers', () => ({
  ...jest.requireActual('../reducers'),
  loadRnaSeqData: () => ({ type: 'NOOP' }),
}))

// RnaSeqOutliers draws its scatterplot with d3 on mount, which the project's jest config stubs out
// (see RnaSeqOutliers.test.js); it's covered by its own test in isolation, so double it here to
// focus this test on RnaSeqResultPage's own tissue-selection/composition logic
jest.mock('./RnaSeqOutliers', () => function MockRnaSeqOutliers({ title }) {
  return <div className="mock-rna-seq-outliers">{title}</div>
})

configure({ adapter: new Adapter() })

// The fixture's rnaSeqDataByIndividual entries only have an "outliers" key with bare pValue/
// isSignificant records; this component also reads "spliceOutliers" and groups by tissue/
// sequencing type, so supply a fuller record for one individual to exercise that logic
const STATE = {
  ...STATE_WITH_2_FAMILIES,
  rnaSeqDataLoading: { isLoading: false },
  rnaSeqDataByIndividual: {
    I021476_na19678_1: {
      outliers: {
        ENSG00000228198: [{
          geneId: 'ENSG00000228198', isSignificant: true, pValue: 0.0004, zScore: -5, tissueType: 'muscle', sequencingType: 'RNA',
        }],
      },
      spliceOutliers: {},
    },
  },
}

test('renders a single tissue type as plain text and the outlier plot for it', () => {
  const store = configureStore()(STATE)
  const wrapper = mount(
    <Provider store={store}>
      <RnaSeqResultPage match={{ params: { individualGuid: 'I021476_na19678_1' } }} />
    </Provider>
  )

  expect(wrapper.find('Dropdown').exists()).toBe(false)
  expect(wrapper.text()).toContain('Tissue type: Unknown Tissue, Sequencing Product: Unknown Product')
  // RnaSeqOutliers itself is React.lazy-loaded and covered by its own test; this just confirms
  // RnaSeqResultPage decided to render a plot section at all for the matching tissue/sequencing type
  expect(wrapper.find('Suspense').exists()).toBe(true)
})

test('renders a dropdown when there is more than one tissue/sequencing type', () => {
  const multiTissueState = {
    ...STATE,
    rnaSeqDataByIndividual: {
      I021476_na19678_1: {
        outliers: {
          ENSG00000228198: [
            {
              geneId: 'ENSG00000228198', isSignificant: true, pValue: 0.0004, zScore: -5, tissueType: 'muscle', sequencingType: 'RNA',
            },
            {
              geneId: 'ENSG00000228198', isSignificant: true, pValue: 0.001, zScore: -4, tissueType: 'blood', sequencingType: 'RNA',
            },
          ],
        },
        spliceOutliers: {},
      },
    },
  }
  const store = configureStore()(multiTissueState)
  const wrapper = mount(
    <Provider store={store}>
      <RnaSeqResultPage match={{ params: { individualGuid: 'I021476_na19678_1' } }} />
    </Provider>
  )

  expect(wrapper.find('Dropdown').exists()).toBe(true)
  const options = wrapper.find('Dropdown').prop('options').map(o => o.value)
  expect(options).toEqual(['muscle-RNA', 'blood-RNA'])
})
