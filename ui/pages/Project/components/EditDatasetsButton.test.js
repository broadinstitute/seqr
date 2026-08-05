import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import { mockFetchResponse, mockFetchRejection, flushAll } from 'shared/utils/testHelpers'
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
  return igvFormWrapper.prop('onSubmit')({
    mappingFile: {
      updates: [
        { individualGuid: 'I021476_na19678_1', individualId: 'NA19678', filePath: '/foo.bam' },
        { individualGuid: 'I021474_na19679_1', individualId: 'NA19679', filePath: '/bar.bam' },
      ],
    },
    sampleType: 'RNA',
  }).then(() => {
    const fetchedUrls = fetch.mock.calls.map(([url]) => url)
    expect(fetchedUrls).toContain('/api/individual/I021476_na19678_1/update_igv_sample')
    expect(fetchedUrls).toContain('/api/individual/I021474_na19679_1/update_igv_sample')

    wrapper.find('.menu .item').at(1).simulate('click')
    wrapper.update()
    expect(wrapper.text()).toContain('Add RNA Data')
  })
})

test('surfaces an aggregated error when an IGV update fails', () => {
  mockFetchResponse({ error: 'boom' }, { ok: false, status: 400 })
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

test('falls back to the exception message when an IGV update fails without a response body', () => {
  mockFetchRejection(new Error('network down'))
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
      expect(e.body.errors[0]).toContain('Error updating NA19678: network down')
    },
  )
})

test('submits the RNA form for a data manager', async () => {
  const store = configureStore(OPEN_MODAL_STATE)
  const wrapper = mount(
    <Provider store={store}>
      <EditDatasetsButton user={{ isDataManager: true }} />
    </Provider>,
  )

  wrapper.find('.menu .item').at(1).simulate('click')
  wrapper.update()

  mockFetchResponse({ info: [], warnings: [], sampleGuids: ['S1'], fileName: 'data.tsv' })
  const rnaFormWrapper = wrapper.find('FormWrapper')
  await rnaFormWrapper.prop('onSubmit')({ sampleGuids: ['S1'], fileName: 'data.tsv', dataType: 'E' })
  await flushAll()

  expect(fetch.mock.calls[0][0]).toEqual(`/api/project/${STATE_WITH_2_FAMILIES.currentProjectGuid}/update_rna_seq`)
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ sampleGuids: ['S1'], fileName: 'data.tsv', dataType: 'E' })
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
