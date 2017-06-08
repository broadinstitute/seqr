import React from 'react'
import { shallow } from 'enzyme'
import Footer from './Footer'

test('shallow-render without crashing', () => {
  shallow(<Footer />)
})
