import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'

import EditDatasetsButton from './EditDatasetsButton'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const STATE = { ...STATE_WITH_2_FAMILIES, modal: {} }

test('renders an "Edit Datasets" button for a data manager', () => {
  const store = configureStore()(STATE)
  const wrapper = mount(
    <Provider store={store}>
      <EditDatasetsButton user={{ isDataManager: true }} />
    </Provider>
  )

  expect(wrapper.text()).toEqual('Edit Datasets')
})

test('renders a "Load Additional Data" button when workspace loading is allowed for a non-manager', () => {
  const store = configureStore()(STATE)
  const wrapper = mount(
    <Provider store={store}>
      <EditDatasetsButton user={{ isDataManager: false, isPm: false }} showLoadWorkspaceData />
    </Provider>
  )

  expect(wrapper.text()).toEqual('Load Additional Data')
})

test('renders nothing for a regular user without workspace loading', () => {
  const store = configureStore()(STATE)
  const wrapper = mount(
    <Provider store={store}>
      <EditDatasetsButton user={{ isDataManager: false, isPm: false }} />
    </Provider>
  )

  expect(wrapper.text()).toEqual('')
})
