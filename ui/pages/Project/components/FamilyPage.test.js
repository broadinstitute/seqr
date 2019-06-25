import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import configureStore from 'redux-mock-store'

import { getUser } from 'redux/selectors'
import FamilyPage from './FamilyPage'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  shallow(<FamilyPage store={store} match={{ params: { familyGuid: 'F011652_1' } }} />)
})
