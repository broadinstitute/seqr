import React from 'react'
import { mount, shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import { BrowserRouter } from 'react-router-dom'

import AnalysisGroups from './AnalysisGroups'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

// Loading is triggered on mount via a thunk action creator; replace it with a no-op so mounting
// does not attempt to make a real HTTP request or require additional reducer STATE_WITH_2_FAMILIES
jest.mock('../reducers', () => ({
  ...jest.requireActual('../reducers'),
  loadCurrentProjectAnalysisGroups: () => ({ type: 'NOOP' }),
}))

configure({ adapter: new Adapter() })

test('renders the current project analysis group with its name and family count', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
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
  const store = configureStore()(STATE_WITH_2_FAMILIES)
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
