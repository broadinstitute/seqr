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
