import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter, Route } from 'react-router-dom'

import FamilyPage from './FamilyPage'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

const INITIAL_ENTRIES = ['/project/R0237_1000_genomes_demo/family_page/F011652_1']

test('renders the family display name and its individuals', () => {
  const store = configureStore({ ...STATE_WITH_2_FAMILIES, familyTagTypeCounts: {} })

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={INITIAL_ENTRIES}>
        <Route path="/project/:projectGuid/family_page/:familyGuid" component={FamilyPage} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('IndividualRow').length).toEqual(3)
})
