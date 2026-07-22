import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import EditDatasetsButton from './EditDatasetsButton'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

const OPEN_MODAL_STATE = { ...STATE_WITH_2_FAMILIES, modal: { Datasets: { open: true } } }

test('renders an "Edit Datasets" button for a data manager', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditDatasetsButton user={{ isDataManager: true }} />
    </Provider>,
  )

  expect(wrapper.text()).toEqual('Edit Datasets')
})

test('renders a "Load Additional Data" button when workspace loading is allowed for a non-manager', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditDatasetsButton user={{ isDataManager: false, isPm: false }} showLoadWorkspaceData />
    </Provider>,
  )

  expect(wrapper.text()).toEqual('Load Additional Data')
})

test('renders nothing for a regular user without workspace loading', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditDatasetsButton user={{ isDataManager: false, isPm: false }} />
    </Provider>,
  )

  expect(wrapper.text()).toEqual('')
})

test('renders the IGV and RNA panes and submits the IGV form for a data manager', () => {
  const store = configureStore(OPEN_MODAL_STATE)
  const wrapper = mount(
    <Provider store={store}>
      <EditDatasetsButton user={{ isDataManager: true }} />
    </Provider>,
  )

  expect(wrapper.find('TabPane').exists()).toBe(true)

  const igvFormWrapper = wrapper.find('FormWrapper')
  expect(igvFormWrapper.exists()).toBe(true)
  igvFormWrapper.prop('onSubmit')({ mappingFile: { updates: [] } })

  wrapper.find('.menu .item').at(1).simulate('click')
  wrapper.update()
  expect(wrapper.text()).toContain('Add RNA Data')
})

test('renders RNA upload info and warning messages when present', () => {
  const store = configureStore({
    ...OPEN_MODAL_STATE,
    rnaSeqUploadStats: { info: ['1 sample loaded'], warnings: ['1 sample skipped'] },
  })
  const wrapper = mount(
    <Provider store={store}>
      <EditDatasetsButton user={{ isDataManager: true }} />
    </Provider>,
  )

  wrapper.find('.menu .item').at(1).simulate('click')
  wrapper.update()

  expect(wrapper.find('Message[info=true]').exists()).toBe(true)
  expect(wrapper.find('Message[warning=true]').exists()).toBe(true)
  expect(wrapper.text()).toContain('1 sample loaded')
  expect(wrapper.text()).toContain('1 sample skipped')
})

test('renders the VCF pane for workspace loading', () => {
  const store = configureStore(OPEN_MODAL_STATE)
  const wrapper = mount(
    <Provider store={store}>
      <EditDatasetsButton user={{ isDataManager: false, isPm: false }} showLoadWorkspaceData />
    </Provider>,
  )

  expect(wrapper.find('TabPane').exists()).toBe(true)
})
