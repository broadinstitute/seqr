import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import { flushAll, getLastFetchUrl } from 'shared/utils/testHelpers'
import EditFamiliesForm from './EditFamiliesForm'
import { STATE_WITH_2_FAMILIES } from '../../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

test('renders an editable row for each family in the project', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditFamiliesForm modalName="editFamilies" />
    </Provider>,
  )

  expect(wrapper.find('input[value="1"]').exists()).toBe(true)
  expect(wrapper.find('input[value="2"]').exists()).toBe(true)
})

test('deletes selected families', async () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditFamiliesForm modalName="editFamilies" />
    </Provider>,
  )

  wrapper.find('DispatchRequestButton').prop('onSubmit')()
  await flushAll()

  expect(getLastFetchUrl()).toEqual(`/api/project/${STATE_WITH_2_FAMILIES.currentProjectGuid}/delete_families`)
})
