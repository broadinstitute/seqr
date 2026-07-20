import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import { EditFamiliesBulkForm, EditIndividualsBulkForm, EditIndividualMetadataBulkForm } from './BulkEditForm'
import { FAMILY_BULK_EDIT_EXPORT_DATA } from '../../constants'
import { INDIVIDUAL_ID_EXPORT_DATA, INDIVIDUAL_CORE_EXPORT_DATA } from 'shared/utils/constants'
import { STATE_WITH_2_FAMILIES } from '../../fixtures'

// jsdom does not implement createObjectURL; BulkUploadForm's template download links need it
global.URL.createObjectURL = jest.fn()

jest.mock('../../reducers', () => ({
  ...jest.requireActual('../../reducers'),
  loadIndividuals: () => ({ type: 'NOOP' }),
}))

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])


test('renders family bulk edit required/optional columns and the core (non-analyst) fields', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditFamiliesBulkForm modalName="bulkEditFamilies" />
    </Provider>
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
    </Provider>
  )

  const lastField = FAMILY_BULK_EDIT_EXPORT_DATA[FAMILY_BULK_EDIT_EXPORT_DATA.length - 1]
  expect(wrapper.text()).toContain(lastField.header)
})

test('renders individuals bulk form with the individual ID required columns', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditIndividualsBulkForm modalName="bulkEditIndividuals" />
    </Provider>
  )

  INDIVIDUAL_ID_EXPORT_DATA.forEach((field) => {
    expect(wrapper.text()).toContain(field.header)
  })
  INDIVIDUAL_CORE_EXPORT_DATA.forEach((field) => {
    expect(wrapper.text()).toContain(field.header)
  })
})

test('renders individual metadata bulk form', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditIndividualMetadataBulkForm modalName="bulkEditIndividualMetadata" />
    </Provider>
  )

  INDIVIDUAL_ID_EXPORT_DATA.forEach((field) => {
    expect(wrapper.text()).toContain(field.header)
  })
})
