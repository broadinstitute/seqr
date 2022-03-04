import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import SortDirectionToggle from './SortDirectionToggle'
import { getFamiliesSortDirection } from '../../../selectors'

import { STATE1 } from '../../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const props = {
    value: getFamiliesSortDirection(STATE1),
    onChange: () => {},
  }

  shallow(<SortDirectionToggle {...props} />)
})
