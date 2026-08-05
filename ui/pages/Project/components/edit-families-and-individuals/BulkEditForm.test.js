import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import { INDIVIDUAL_ID_EXPORT_DATA, INDIVIDUAL_CORE_EXPORT_DATA, FILE_FIELD_NAME } from 'shared/utils/constants'
import { flushAll, getLastFetchUrl, getLastFetchBody } from 'shared/utils/testHelpers'
import { EditFamiliesBulkForm, EditIndividualsBulkForm, EditIndividualMetadataBulkForm } from './BulkEditForm'
import { FAMILY_BULK_EDIT_EXPORT_DATA } from '../../constants'
import { STATE_WITH_2_FAMILIES } from '../../fixtures'

// jsdom does not implement createObjectURL; BulkUploadForm's template download links need it
global.URL.createObjectURL = jest.fn()

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

test('renders family bulk edit required/optional columns and the core (non-analyst) fields', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditFamiliesBulkForm modalName="bulkEditFamilies" />
    </Provider>,
  )

  const [idField, ...optionalFields] = FAMILY_BULK_EDIT_EXPORT_DATA
  expect(wrapper.text()).toContain(idField.header)
  // non-analyst users only get the "core" subset (first 4 of the optional fields)
  optionalFields.slice(0, 4).forEach((field) => {
    expect(wrapper.text()).toContain(field.header)
  })
})

test('renders analyst-only optional fields for an analyst user', () => {
  // The analyst-only "external data" column's export formatter is called eagerly for the "download
  // current data" template link, and unconditionally calls .map on it, so it must be an array here
  const analystState = {
    ...STATE_WITH_2_FAMILIES,
    user: { ...STATE_WITH_2_FAMILIES.user, isAnalyst: true },
  }
  const analystStore = configureStore(analystState)
  const wrapper = mount(
    <Provider store={analystStore}>
      <EditFamiliesBulkForm modalName="bulkEditFamilies" />
    </Provider>,
  )

  const lastField = FAMILY_BULK_EDIT_EXPORT_DATA[FAMILY_BULK_EDIT_EXPORT_DATA.length - 1]
  expect(wrapper.text()).toContain(lastField.header)
})

test('submits the uploaded file value on form submission', async () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditFamiliesBulkForm modalName="bulkEditFamilies" />
    </Provider>,
  )

  const uploadedFileId = 'file123'
  await wrapper.find('FormWrapper').prop('onSubmit')({ [FILE_FIELD_NAME]: uploadedFileId })
  await flushAll()

  expect(getLastFetchUrl()).toEqual(`/api/project/${STATE_WITH_2_FAMILIES.currentProjectGuid}/edit_families`)
  expect(getLastFetchBody()).toEqual(uploadedFileId)
})

test('renders individuals bulk form with the individual ID required columns', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditIndividualsBulkForm modalName="bulkEditIndividuals" />
    </Provider>,
  )

  INDIVIDUAL_ID_EXPORT_DATA.forEach((field) => {
    expect(wrapper.text()).toContain(field.header)
  })
  INDIVIDUAL_CORE_EXPORT_DATA.forEach((field) => {
    expect(wrapper.text()).toContain(field.header)
  })
})

test('renders analyst-only optional fields for individuals bulk form for an analyst user', () => {
  const analystState = {
    ...STATE_WITH_2_FAMILIES,
    user: { ...STATE_WITH_2_FAMILIES.user, isAnalyst: true },
  }
  const analystStore = configureStore(analystState)
  const wrapper = mount(
    <Provider store={analystStore}>
      <EditIndividualsBulkForm modalName="bulkEditIndividuals" />
    </Provider>,
  )

  INDIVIDUAL_ID_EXPORT_DATA.forEach((field) => {
    expect(wrapper.text()).toContain(field.header)
  })
})

test('submits the uploaded file id on individuals bulk form submission', async () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditIndividualsBulkForm modalName="bulkEditIndividuals" />
    </Provider>,
  )

  const uploadedFileId = 'file789'
  await wrapper.find('FormWrapper').prop('onSubmit')({ [FILE_FIELD_NAME]: { uploadedFileId } })
  await flushAll()

  expect(getLastFetchUrl()).toEqual(
    `/api/project/${STATE_WITH_2_FAMILIES.currentProjectGuid}/save_individuals_table/${uploadedFileId}`,
  )
})

test('renders individual metadata bulk form', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditIndividualMetadataBulkForm modalName="bulkEditIndividualMetadata" />
    </Provider>,
  )

  INDIVIDUAL_ID_EXPORT_DATA.forEach((field) => {
    expect(wrapper.text()).toContain(field.header)
  })
})

test('renders without crashing with complex data for export', () => {
  const stateWithCandidateGenes = {
    ...STATE_WITH_2_FAMILIES,
    user: { ...STATE_WITH_2_FAMILIES.user, isAnalyst: true },
    familiesByGuid: {
      ...STATE_WITH_2_FAMILIES.familiesByGuid,
      F011652_1: {
        ...STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1,
        externalData: ['M', 'unknownDataType'],
      },
      F011652_2: {
        ...STATE_WITH_2_FAMILIES.familiesByGuid.F011652_2,
        externalData: ['P'],
      },
    },
    individualsByGuid: {
      ...STATE_WITH_2_FAMILIES.individualsByGuid,
      I021475_na19675_1: {
        ...STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1,
        candidateGenes: [
          { gene: 'FOXP2' },
          { gene: 'CACNA1A', comments: 'a candidate gene comment' },
        ],
      },
    },
  }
  const store = configureStore(stateWithCandidateGenes)
  const wrapper = mount(
    <Provider store={store}>
      <EditIndividualMetadataBulkForm modalName="bulkEditIndividualMetadata" />
    </Provider>,
  )

  expect(wrapper.find('FormWrapper').exists()).toBe(true)

  const familyFormWrapper = mount(
    <Provider store={store}>
      <EditFamiliesBulkForm modalName="bulkEditFamilies" />
    </Provider>,
  )
  expect(familyFormWrapper.find('FormWrapper').exists()).toBe(true)
})

test('submits the uploaded file id on individual metadata form submission', async () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditIndividualMetadataBulkForm modalName="bulkEditIndividualMetadata" />
    </Provider>,
  )

  const uploadedFileId = 'file456'
  await wrapper.find('FormWrapper').prop('onSubmit')({ [FILE_FIELD_NAME]: { uploadedFileId } })
  await flushAll()

  expect(getLastFetchUrl()).toEqual(
    `/api/project/${STATE_WITH_2_FAMILIES.currentProjectGuid}/save_individuals_metadata_table/${uploadedFileId}`,
  )
})
