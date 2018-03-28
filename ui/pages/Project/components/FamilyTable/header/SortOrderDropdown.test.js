import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { SortOrderDropdownComponent } from './SortOrderDropdown'
import { getFamiliesSortOrder } from '../../rootReducer'

import { STATE1 } from '../../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    sortOrder: PropTypes.string.isRequired,
    updateSortOrder: PropTypes.func.isRequired,
   */

  const props = {
    sortOrder: getFamiliesSortOrder(STATE1),
    updateSortOrder: () => {},
  }

  shallow(<SortOrderDropdownComponent {...props} />)
})
