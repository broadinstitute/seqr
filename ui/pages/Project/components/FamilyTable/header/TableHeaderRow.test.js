import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { TableHeaderRowComponent } from './TableHeaderRow'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<TableHeaderRowComponent />)
})
