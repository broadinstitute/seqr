import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'

import { mockFetchResponse, flushAll, getLastFetchUrl } from 'shared/utils/testHelpers'
import ProjectNotifications from './ProjectNotifications'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const renderNotifications = async (responseJson) => {
  mockFetchResponse(responseJson)
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <ProjectNotifications />
    </Provider>,
  )
  await flushAll()
  wrapper.update()
  return wrapper
}

test('renders unread notifications and a mark-as-read button', async () => {
  const wrapper = await renderNotifications({
    unreadNotifications: [{ id: 1, verb: 'added a note', timestamp: '2020-01-01T00:00:00Z' }],
    isSubscriber: true,
  })

  expect(wrapper.text()).toContain('added a note')
  expect(wrapper.find('ButtonLink[content="Mark all as read"]').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Subscribe"]').exists()).toBe(false)
})

test('renders a subscribe button and empty state when there are no notifications', async () => {
  const wrapper = await renderNotifications({ unreadNotifications: [], isSubscriber: false })

  expect(wrapper.text()).toContain('No new notifications')
  expect(wrapper.find('ButtonLink[content="Subscribe"]').exists()).toBe(true)
})

test('renders a show-read-notifications button when there are read notifications to show', async () => {
  const wrapper = await renderNotifications({ unreadNotifications: [], readCount: 3, isSubscriber: true })

  expect(wrapper.find('ButtonLink[content="Show 3 read notifications"]').exists()).toBe(true)
})

test('re-fetches with a new url path when a notification action button is clicked', async () => {
  const wrapper = await renderNotifications({
    unreadNotifications: [{ id: 1, verb: 'added a note', timestamp: '2020-01-01T00:00:00Z' }],
    isSubscriber: true,
  })

  wrapper.find('ButtonLink[content="Mark all as read"]').find('button').simulate('click')
  await flushAll()
  wrapper.update()

  expect(getLastFetchUrl()).toContain('/mark_read')
})
