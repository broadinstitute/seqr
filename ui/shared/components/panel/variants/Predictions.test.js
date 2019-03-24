import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import configureStore from 'redux-mock-store'

import { getUser } from 'redux/selectors'
import Predictions from './Predictions'
import { STATE1, VARIANT } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<Predictions store={store} variant={VARIANT} />)
})
