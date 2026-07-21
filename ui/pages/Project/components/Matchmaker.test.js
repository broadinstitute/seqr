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
const MATCH_WITH_SUBMISSION = { params: { familyGuid: 'F011652_2' } }

test('renders the affected individual with no matchmaker submission', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH} />
    </Provider>,
  )

  expect(wrapper.find('Header[content="This individual has no submissions"]').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Submit to Matchmaker"]').exists()).toBe(true)
})

test('renders the affected individual with a matchmaker submission', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_WITH_SUBMISSION} />
    </Provider>,
  )

  expect(wrapper.find('Header[content="This individual has no submissions"]').exists()).toBe(false)
  expect(wrapper.find('ButtonLink[content="Search for New Matches"]').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Update Submission"]').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Delete Submission"]').exists()).toBe(true)

  expect(wrapper.find('Header[content="Previous Matches"]').exists()).toBe(true)

  const wrapperText = wrapper.text()
  expect(wrapperText).toContain('Childhood Psychiatric Disorder Candidate Genes')
  expect(wrapperText).toContain('James Crowley')
  expect(wrapperText).toContain('2016-174')
  expect(wrapperText).toContain('Janneke Weiss')
})
