import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import configureStore from 'redux-mock-store'

import SetPassword from './SetPassword'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()({ newUser: { username: 'test'} })
  shallow(<SetPassword store={store} />)
})