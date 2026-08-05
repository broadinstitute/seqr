import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import EditIndividualsForm from './EditIndividualsForm'
import { STATE_WITH_2_FAMILIES } from '../../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

test('renders an editable row for each individual in the family', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      {/* Scope to a single family/analysis group: the fixture reuses individual IDs (NA19678,
          NA19675, NA19679) across both its families, so restrict to one to keep assertions unambiguous */}
      <EditIndividualsForm modalName="editIndividuals" analysisGroupGuid="AG0000183_test_group" />
    </Provider>
  )

  expect(wrapper.find('tbody tr').length).toEqual(3)
  expect(wrapper.find('input[value="NA19678"]').exists()).toBe(true)
  expect(wrapper.find('input[value="NA19675"]').exists()).toBe(true)
  expect(wrapper.find('input[value="NA19679"]').exists()).toBe(true)
})

test('shows the analyst-only fields when the user is an analyst', () => {
  const state = { ...STATE_WITH_2_FAMILIES, user: { ...STATE_WITH_2_FAMILIES.user, isAnalyst: true } }
  const store = configureStore(state)
  const wrapperWithoutAnalystFields = mount(
    <Provider store={configureStore(STATE_WITH_2_FAMILIES)}>
      <EditIndividualsForm modalName="editIndividuals" analysisGroupGuid="AG0000183_test_group" />
    </Provider>
  )
  const wrapper = mount(
    <Provider store={store}>
      <EditIndividualsForm modalName="editIndividuals" analysisGroupGuid="AG0000183_test_group" />
    </Provider>
  )

  const columnNames = wrapper.find('EditRecordsForm').prop('columns').map(({ name }) => name)
  const columnNamesWithoutAnalystFields = wrapperWithoutAnalystFields.find('EditRecordsForm').prop('columns').map(
    ({ name }) => name,
  )

  expect(columnNames).toEqual([
    'familyId', 'individualId', 'paternalId', 'maternalId', 'sex', 'affected', 'probandRelationship',
  ])
  expect(columnNamesWithoutAnalystFields).toEqual([
    'familyId', 'individualId', 'paternalId', 'maternalId', 'sex', 'affected',
  ])
})
