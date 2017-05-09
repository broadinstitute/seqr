import React from 'react'
import { shallow } from 'enzyme'
import { AwesomeBarComponent } from './AwesomeBar'


test('shallow-render without crashing', () => {
  shallow(<AwesomeBarComponent />)
})
