import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import EditDatasetsButton from './EditDatasetsButton'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

let mockFailIndividualGuid = null
const mockLoadMultipleData = jest.fn(() => () => () => Promise.resolve())
jest.mock('shared/utils/httpRequestHelper', () => ({
  HttpRequestHelper: jest.fn().mockImplementation((url, onSuccess, onError) => ({
    get: jest.fn(() => Promise.resolve()),
    post: jest.fn((body) => {
      if (onError && body.individualGuid === mockFailIndividualGuid) {
        onError({ message: 'boom' })
        return Promise.resolve()
      }
      if (onSuccess) {
        onSuccess({})
      }
      return Promise.resolve()
    }),
  })),
  loadMultipleData: (...args) => mockLoadMultipleData(...args),
}))

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
  mockFailIndividualGuid = null
  HttpRequestHelper.mockClear()
  const store = configureStore(OPEN_MODAL_STATE)
  const wrapper = mount(
    <Provider store={store}>
      <EditDatasetsButton user={{ isDataManager: true }} />
    </Provider>,
  )

  expect(wrapper.find('TabPane').exists()).toBe(true)

  const igvFormWrapper = wrapper.find('FormWrapper')
  expect(igvFormWrapper.exists()).toBe(true)
  return igvFormWrapper.prop('onSubmit')({
    mappingFile: {
      updates: [
        { individualGuid: 'I021476_na19678_1', individualId: 'NA19678', filePath: '/foo.bam' },
        { individualGuid: 'I021474_na19679_1', individualId: 'NA19679', filePath: '/bar.bam' },
      ],
    },
    sampleType: 'RNA',
  }).then(() => {
    expect(HttpRequestHelper).toHaveBeenCalledWith(
      '/api/individual/I021476_na19678_1/update_igv_sample', expect.any(Function), expect.any(Function),
    )
    expect(HttpRequestHelper).toHaveBeenCalledWith(
      '/api/individual/I021474_na19679_1/update_igv_sample', expect.any(Function), expect.any(Function),
    )

    wrapper.find('.menu .item').at(1).simulate('click')
    wrapper.update()
    expect(wrapper.text()).toContain('Add RNA Data')
  })
})

test('surfaces an aggregated error when an IGV update fails', () => {
  mockFailIndividualGuid = 'I021476_na19678_1'
  const store = configureStore(OPEN_MODAL_STATE)
  const wrapper = mount(
    <Provider store={store}>
      <EditDatasetsButton user={{ isDataManager: true }} />
    </Provider>,
  )

  const igvFormWrapper = wrapper.find('FormWrapper')
  return igvFormWrapper.prop('onSubmit')({
    mappingFile: {
      updates: [
        { individualGuid: 'I021476_na19678_1', individualId: 'NA19678' },
      ],
    },
  }).then(
    () => { throw new Error('expected onSubmit to reject') },
    (e) => {
      expect(e.body.errors[0]).toContain('Error updating NA19678: boom')
    },
  )
})

test('submits the RNA form for a data manager', () => {
  mockLoadMultipleData.mockClear()
  const store = configureStore(OPEN_MODAL_STATE)
  const wrapper = mount(
    <Provider store={store}>
      <EditDatasetsButton user={{ isDataManager: true }} />
    </Provider>,
  )

  wrapper.find('.menu .item').at(1).simulate('click')
  wrapper.update()

  const rnaFormWrapper = wrapper.find('FormWrapper')
  rnaFormWrapper.prop('onSubmit')({ sampleGuids: ['S1'], fileName: 'data.tsv', dataType: 'E' })

  expect(mockLoadMultipleData).toHaveBeenCalledWith(
    `/api/project/${STATE_WITH_2_FAMILIES.currentProjectGuid}/update_rna_seq`,
    expect.any(Function),
    expect.any(String),
    expect.any(Function),
    10,
  )
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
