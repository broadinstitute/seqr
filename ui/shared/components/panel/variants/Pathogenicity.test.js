import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { getUser } from 'redux/selectors'
import { BasePathogenicity } from './Pathogenicity'
import { VARIANT, SV_VARIANT, USER } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<BasePathogenicity variant={VARIANT} user={USER} />)
  shallow(<BasePathogenicity variant={SV_VARIANT} user={USER} />)
})
