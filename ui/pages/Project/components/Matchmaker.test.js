import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { STATE_WITH_2_FAMILIES } from '../fixtures'
import Matchmaker from './Matchmaker'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  shallow(<Matchmaker store={store} match={{ params: { familyGuid: 'F011652_1' } }} />)
})
