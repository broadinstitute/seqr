import React from 'react'
import { shallow } from 'enzyme'
import AwesomeBar from './AwesomeBar'


test('shallow-render without crashing', () => {
  shallow(<AwesomeBar />)
})
