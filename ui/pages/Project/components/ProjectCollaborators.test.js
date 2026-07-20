import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import ProjectCollaborators from './ProjectCollaborators'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

test('renders each collaborator email with an edit and add button', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <ProjectCollaborators />
    </Provider>,
  )

  expect(wrapper.find('a[href="mailto:test1@broadinstitute.org"]').exists()).toBe(true)
  expect(wrapper.find('a[href="mailto:test2@broadinstitute.org"]').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Add Collaborator"]').exists()).toBe(true)
})
