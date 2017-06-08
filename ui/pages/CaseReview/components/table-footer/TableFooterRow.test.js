import React from 'react'
import { shallow } from 'enzyme'
import { TableFooterRowComponent } from './TableFooterRow'


test('shallow-render without crashing', () => {
  const props = {}

  shallow(<TableFooterRowComponent {...props} />)
})
