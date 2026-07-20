import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { CASE_REVIEW_TABLE_NAME } from '../../constants'

import IndividualRow from './IndividualRow'
import { STATE_WITH_2_FAMILIES } from '../../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

test('toggles compact/full individual details via CollapsableLayout when deeply rendered', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <IndividualRow
          family={STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1}
          individual={STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1}
          tableName={CASE_REVIEW_TABLE_NAME}
        />
      </MemoryRouter>
    </Provider>,
  )

  // the pedigree/IGV edit buttons are always rendered, regardless of collapsed state
  const baseFieldCount = wrapper.find('BaseFieldView').length

  const toggle = wrapper.find('CollapsableLayout').find('Icon[name="dropdown"]')
  expect(toggle.exists()).toBe(true)

  toggle.first().simulate('click')
  wrapper.update()

  // after toggling, the full set of case review detail fields is rendered in addition
  expect(wrapper.find('BaseFieldView').length).toBeGreaterThan(baseFieldCount)
})
