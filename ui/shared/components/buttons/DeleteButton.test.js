import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import DeleteButton from './DeleteButton'


configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<DeleteButton />)
})
