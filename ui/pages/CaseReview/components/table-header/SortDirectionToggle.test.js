import React from 'react'
import { shallow } from 'enzyme'
import { SortDirectionToggleComponent } from './SortDirectionToggle'
import { getFamiliesSortDirection } from '../../reducers/rootReducer'

import { STATE1 } from '../../fixtures'


test('shallow-render without crashing', () => {
  /*
    sortDirection: React.PropTypes.number.isRequired,
    updateSortDirection: React.PropTypes.func.isRequired,
   */

  const props = {
    sortDirection: getFamiliesSortDirection(STATE1),
    updateSortDirection: () => {},
  }

  shallow(<SortDirectionToggleComponent {...props} />)
})
