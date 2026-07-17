import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import EditIndividualsForm from './EditIndividualsForm'
import { STATE_WITH_2_FAMILIES } from '../../fixtures'

jest.mock('../../reducers', () => ({
  ...jest.requireActual('../../reducers'),
  loadIndividuals: () => ({ type: 'NOOP' }),
}))

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

// DataTable names each row's editable fields `${row[idField]}.${column}`; most of the fixture's
// individualsByGuid entries omit the individualGuid field itself (it's only used as the object
// key), so every row's fields would collide under the name "undefined.<column>" without this
const withIndividualGuids = individualsByGuid => Object.entries(individualsByGuid).reduce(
  (acc, [individualGuid, individual]) => ({ ...acc, [individualGuid]: { ...individual, individualGuid } }), {},
)

const STATE = {
  ...STATE_WITH_2_FAMILIES,
  modal: {},
  individualsLoading: { isLoading: false },
  individualsByGuid: withIndividualGuids(STATE_WITH_2_FAMILIES.individualsByGuid),
}

test('renders an editable row for each individual in the family', () => {
  const store = configureStore(STATE)
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
