import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'

import ProjectNotifications from './ProjectNotifications'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

let onSuccessCallback
jest.mock('shared/utils/httpRequestHelper', () => ({
  HttpRequestHelper: jest.fn().mockImplementation((url, onSuccess) => {
    onSuccessCallback = onSuccess
    return { get: jest.fn() }
  }),
}))

configure({ adapter: new Adapter() })

test('renders unread notifications and a mark-as-read button', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <ProjectNotifications />
    </Provider>,
  )

  onSuccessCallback({
    unreadNotifications: [{ id: 1, verb: 'added a note', timestamp: '2020-01-01T00:00:00Z' }],
    isSubscriber: true,
  })
  wrapper.update()

  expect(wrapper.text()).toContain('added a note')
  expect(wrapper.find('ButtonLink[content="Mark all as read"]').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Subscribe"]').exists()).toBe(false)
})

test('renders a subscribe button and empty state when there are no notifications', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <ProjectNotifications />
    </Provider>,
  )

  onSuccessCallback({ unreadNotifications: [], isSubscriber: false })
  wrapper.update()

  expect(wrapper.text()).toContain('No new notifications')
  expect(wrapper.find('ButtonLink[content="Subscribe"]').exists()).toBe(true)
})

test('renders a show-read-notifications button when there are read notifications to show', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <ProjectNotifications />
    </Provider>,
  )

  onSuccessCallback({ unreadNotifications: [], readCount: 3, isSubscriber: true })
  wrapper.update()

  expect(wrapper.find('ButtonLink[content="Show 3 read notifications"]').exists()).toBe(true)
})
