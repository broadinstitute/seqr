import React from 'react'
import { shallow } from 'enzyme'
import { TableHeaderRowComponent } from './TableHeaderRow'

test('shallow-render without crashing', () => {
  shallow(<TableHeaderRowComponent />)
})
