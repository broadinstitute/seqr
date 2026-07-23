import React from 'react'
import { mount, shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { BrowserRouter } from 'react-router-dom'

import AnalysisGroups from './AnalysisGroups'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

// Loading is triggered on mount via a thunk action creator; mock the underlying HTTP request so
// mounting does not attempt a real network call
jest.mock('shared/utils/httpRequestHelper', () => ({
  HttpRequestHelper: jest.fn().mockImplementation(() => ({ get: jest.fn(), post: jest.fn() })),
}))

configure({ adapter: new Adapter() })

test('renders the current project analysis group with its name and family count', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <BrowserRouter>
        <AnalysisGroups />
      </BrowserRouter>
    </Provider>
  )

  expect(wrapper.find('a[href="/project/R0237_1000_genomes_demo/analysis_group/AG0000183_test_group"]').text()).toEqual('Test Group')

  // Popup content is a portal only rendered on hover, so render its `content` prop directly
  const popupContent = wrapper.find('Popup').prop('content')
  expect(shallow(popupContent).text()).toContain('1 Families')
})

test('renders only the requested analysis group when analysisGroupGuid is specified', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <BrowserRouter>
        <AnalysisGroups analysisGroupGuid="AG0000183_test_group" />
      </BrowserRouter>
    </Provider>
  )

  expect(wrapper.find('a').length).toEqual(1)
  expect(wrapper.find('a').text()).toEqual('Test Group')
})

test('renders a sync icon and criteria fields for a dynamic analysis group', () => {
  const criteriaState = {
    ...STATE_WITH_2_FAMILIES,
    analysisGroupsByGuid: {
      ...STATE_WITH_2_FAMILIES.analysisGroupsByGuid,
      AG0000183_test_group: {
        ...STATE_WITH_2_FAMILIES.analysisGroupsByGuid.AG0000183_test_group,
        criteria: { analysisStatus: ['Q'] },
      },
    },
  }
  const store = configureStore([thunk])(criteriaState)
  const wrapper = mount(
    <Provider store={store}>
      <BrowserRouter>
        <AnalysisGroups />
      </BrowserRouter>
    </Provider>
  )

  expect(wrapper.find('Icon[name="sync"]').exists()).toBe(true)

  const popupContent = wrapper.find('Popup').prop('content')
  expect(shallow(popupContent[0]).prop('field')).toEqual('analysisStatus')
})
