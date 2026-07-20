import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'

import ProjectOverview from './ProjectOverview'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

test('divides content correctly by section for the current project', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <ProjectOverview familiesLoading={false} overviewLoading={false} />
    </Provider>
  )

  // Each DetailSection renders a <b> title alongside a styled DetailContent with its content.
  // Pair them up by DOM position so we verify each title is associated with its own content,
  // rather than just asserting all expected text appears somewhere on the page.
  const sections = wrapper.find('ProjectOverview__DetailContent').map(content => ({
    title: content.parents().find('b').first().text(),
    content: content.text(),
  }))

  expect(sections).toEqual(expect.arrayContaining([
    {
      title: '2 Families,6 Individuals',
      content: '2 families with 3 individuals',
    },
    {
      title: '1 Families With Data,1 Individuals With Data',
      content: '1 family with 1 individual',
    },
    {
      title: 'Matchmaker Submissions',
      content: 'No Submissions',
    },
    {
      title: 'Genome Version',
      content: 'GRCh38',
    },
    {
      title: 'Exome Datasets',
      content: '3/13/2018 - 1 samples',
    },
    {
      title: 'Analysis Status',
      content: 'No Data',
    },
  ]))
})
