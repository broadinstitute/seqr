import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { EmptyTableRowComponent } from './EmptyTableRow'
import { getFamiliesFilter } from '../../selectors'

import { STATE1 } from '../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    familiesFilter: PropTypes.string.isRequired,
   */

  const props = {
    familiesFilter: getFamiliesFilter(STATE1),
  }

  shallow(<EmptyTableRowComponent {...props} />)
})
