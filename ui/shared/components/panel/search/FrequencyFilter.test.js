import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { FrequencyFilter } from './FrequencyFilter'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<FrequencyFilter value={{ af: 0.01 }} />)
})
