import React from 'react'
import { shallow } from 'enzyme'
import { SortOrderDropdownComponent } from './SortOrderDropdown'
import { getFamiliesSortOrder } from '../../reducers/rootReducer'

import { STATE1 } from '../../fixtures'


test('shallow-render without crashing', () => {
  /*
    sortOrder: React.PropTypes.string.isRequired,
    updateSortOrder: React.PropTypes.func.isRequired,
   */

  const props = {
    sortOrder: getFamiliesSortOrder(STATE1),
    updateSortOrder: () => {},
  }

  shallow(<SortOrderDropdownComponent {...props} />)
})
