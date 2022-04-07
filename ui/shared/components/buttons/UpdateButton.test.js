import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import UpdateButton from './UpdateButton'


configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<UpdateButton />)
})
