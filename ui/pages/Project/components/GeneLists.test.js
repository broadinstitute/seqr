import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'

import { GeneLists } from './GeneLists'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

// Loading is triggered on mount via a thunk action creator; replace it with a no-op so mounting
// does not attempt to make a real HTTP request or require additional reducer STATE_WITH_2_FAMILIES
jest.mock('../reducers', () => ({
  ...jest.requireActual('../reducers'),
  loadProjectLocusLists: () => ({ type: 'NOOP' }),
}))

configure({ adapter: new Adapter() })

test('renders gene lists for the current project', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <GeneLists />
    </Provider>
  )

  expect(wrapper.find('ButtonLink').at(0).text()).toEqual('Known Genes')
})

test('shows a loading indicator while gene lists are loading', () => {
  const loadingState = { ...STATE_WITH_2_FAMILIES, projectLocusListsLoading: { isLoading: true } }
  const store = configureStore()(loadingState)
  const wrapper = mount(
    <Provider store={store}>
      <GeneLists />
    </Provider>
  )

  expect(wrapper.find('Dimmer').prop('active')).toBe(true)
  expect(wrapper.text()).toContain('Loading')
})
