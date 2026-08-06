import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'

import EditDatasetsButton from './EditDatasetsButton'
import { STATE_WITH_2_FAMILIES, DATA_MANAGER_USER } from '../fixtures'

configure({ adapter: new Adapter() })

const PROJECT = STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo

const renderButton = props => mount(
  <Provider store={configureStore()(STATE_WITH_2_FAMILIES)}>
    <EditDatasetsButton project={PROJECT} {...props} />
  </Provider>,
)

test('renders an Edit Datasets button for a data manager', () => {
  const wrapper = renderButton({ user: DATA_MANAGER_USER })

  expect(wrapper.find('ButtonLink').text()).toEqual('Edit Datasets')
})

test('renders a Load Additional Data button when workspace loading is enabled for a regular user', () => {
  const wrapper = renderButton({ user: STATE_WITH_2_FAMILIES.user, showLoadWorkspaceData: true })

  expect(wrapper.find('ButtonLink').text()).toEqual('Load Additional Data')
})

test('renders nothing for a regular user without workspace loading enabled', () => {
  const wrapper = renderButton({ user: STATE_WITH_2_FAMILIES.user })

  expect(wrapper.find('ButtonLink').exists()).toBe(false)
})
