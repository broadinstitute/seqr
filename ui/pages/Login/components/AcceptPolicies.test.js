import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import AcceptPolicies from './AcceptPolicies'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()({})
  shallow(<AcceptPolicies store={store} />)
})
