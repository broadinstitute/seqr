import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'

import { getUser } from 'redux/selectors'
import SavedVariants from './SavedVariants'
import { STATE1 } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)
  shallow(<SavedVariants store={store} match={{ params: {} }} />)
})
