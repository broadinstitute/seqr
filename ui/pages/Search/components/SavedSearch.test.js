import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import configureStore from 'redux-mock-store'

import { SaveSearchButton, SavedSearchDropdown } from './SavedSearch'

import { STATE } from '../fixtures'

configure({ adapter: new Adapter() })

test('SaveSearchButton shallow-render without crashing', () => {
  const store = configureStore()(STATE)

  shallow(<SaveSearchButton store={store} />)
})

test('SavedSearchDropdown shallow-render without crashing', () => {
  const store = configureStore()(STATE)

  shallow(<SavedSearchDropdown store={store} />)
})
