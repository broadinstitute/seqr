import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'

import ProjectOverview from './ProjectOverview'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const STATE = {
  ...STATE_WITH_2_FAMILIES,
  modal: {},
  mmeSubmissionsLoading: { isLoading: false },
  // Anvil renders `(workspaceName || user.isPm) && user.isAnvil && (...)`; leaving isPm/isAnvil
  // undefined (rather than false) makes the expression itself evaluate to undefined, which React
  // rejects as a component return value
  user: { ...STATE_WITH_2_FAMILIES.user, isPm: false, isAnvil: false },
}

test('renders family, matchmaker, and dataset overview sections for the current project', () => {
  const store = configureStore()(STATE)
  const wrapper = mount(
    <Provider store={store}>
      <ProjectOverview familiesLoading={false} overviewLoading={false} />
    </Provider>
  )

  expect(wrapper.text()).toContain('2 Families,6 Individuals')
  expect(wrapper.text()).toContain('2 families with 3 individuals')
  expect(wrapper.text()).toContain('Matchmaker Submissions')
  expect(wrapper.text()).toContain('No Submissions')
  expect(wrapper.text()).toContain('Genome Version')
  expect(wrapper.text()).toContain('Exome Datasets')
  expect(wrapper.text()).toContain('3/13/2018 - 1 samples')
  expect(wrapper.text()).toContain('Analysis Status')
})
