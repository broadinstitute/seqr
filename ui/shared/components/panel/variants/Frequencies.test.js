import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { getUser } from 'redux/selectors'
import Frequencies from './Frequencies'
import { VARIANT, SV_VARIANT } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<Frequencies variant={VARIANT} />)
  shallow(<Frequencies variant={SV_VARIANT} />)
})
