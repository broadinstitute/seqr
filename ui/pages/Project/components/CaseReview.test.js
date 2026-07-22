import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import CaseReviewTable from './CaseReview'

import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

test('renders the accepted families and the individual status summary', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <CaseReviewTable />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('HorizontalStackedBar').exists()).toBe(true)
  expect(wrapper.text()).toContain('Individual Statuses:')
  expect(wrapper.find('FamilyTableRow').length).toEqual(2)
})
