import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { STATE_WITH_2_FAMILIES } from '../fixtures'
import Matchmaker from './Matchmaker'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

const MATCH = { params: { familyGuid: 'F011652_1' } }

test('renders the affected individual with no matchmaker submission', () => {
  const store = configureStore({ ...STATE_WITH_2_FAMILIES, matchmakerMatchesLoading: { isLoading: false } })

  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH} />
    </Provider>,
  )

  expect(wrapper.find('Header[content="This individual has no submissions"]').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Submit to Matchmaker"]').exists()).toBe(true)
})
