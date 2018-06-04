import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { getUser } from 'redux/selectors'
import Pathogenicity from './Pathogenicity'
import { VARIANT } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<Pathogenicity variant={VARIANT} />)
})
