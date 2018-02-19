import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { TableFooterRowComponent } from './TableFooterRow'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const props = {}

  shallow(<TableFooterRowComponent {...props} />)
})
