import React from 'react'
import { shallow } from 'enzyme'
import { SortDirectionToggleComponent } from './SortDirectionToggle'
import { getFamiliesSortDirection } from '../../reducers/rootReducer'

import { STATE1 } from '../../fixtures'


test('shallow-render without crashing', () => {
  /*
   sortDirection: PropTypes.number.isRequired,
   updateSortDirection: PropTypes.func.isRequired,
   */

  const props = {
    sortDirection: getFamiliesSortDirection(STATE1),
    updateSortDirection: () => {},
  }

  shallow(<SortDirectionToggleComponent {...props} />)
})
