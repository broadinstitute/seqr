import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import ProjectPageUI from './ProjectPageUI'

import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

const MATCH = { params: {} }

test('renders the project sections and the families table', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <ProjectPageUI match={MATCH} />
      </MemoryRouter>
    </Provider>,
  )

  const sectionHeaders = wrapper.find('StyledComponents__SectionHeader').map(header => header.text())
  expect(sectionHeaders).toEqual([
    'Analysis Groups', 'Gene Lists', 'Overview', 'Variant Tags', 'Notifications', 'Collaborators', 'Families',
  ])
  expect(wrapper.find('FamilyTableRow').length).toEqual(2)
})
