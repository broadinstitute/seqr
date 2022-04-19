import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { TableHeaderRowComponent } from './TableHeaderRow'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<TableHeaderRowComponent headerStatus={{ title: 'Analysis Statuses', data: {} }} />)
})
