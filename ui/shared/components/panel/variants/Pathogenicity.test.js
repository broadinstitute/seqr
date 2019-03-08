import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { getUser } from 'redux/selectors'
import { BasePathogenicity } from './Pathogenicity'
import { VARIANT, USER } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<BasePathogenicity variant={VARIANT} user={USER} />)
})
