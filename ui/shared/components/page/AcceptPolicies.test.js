import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { BaseAcceptPolicies  } from './AcceptPolicies'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<BaseAcceptPolicies user={{}} />)
  shallow(<BaseAcceptPolicies user={{ currentPolicies: true }} />)
})
