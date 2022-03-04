import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'

import ForgotPassword from './ForgotPassword'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()()
  shallow(<ForgotPassword store={store} />)
})