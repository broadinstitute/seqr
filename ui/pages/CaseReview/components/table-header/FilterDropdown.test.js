import React from 'react'
import { shallow } from 'enzyme'
import { FilterDropdownComponent } from './FilterDropdown'
import { getFamiliesFilter, getFamiliesByGuid } from '../../reducers/rootReducer'
import { getVisibleFamilyGuids } from '../../utils/visibleFamiliesSelector'
import { STATE1 } from '../../fixtures'


test('shallow-render without crashing', () => {
  /*
    familiesFilter: React.PropTypes.string.isRequired,
    filteredCount: React.PropTypes.number.isRequired,
    totalCount: React.PropTypes.number.isRequired,
    updateFilter: React.PropTypes.func.isRequired,
   */

  const props = {
    familiesFilter: getFamiliesFilter(STATE1),
    filteredCount: getVisibleFamilyGuids(STATE1).length,
    totalCount: Object.keys(getFamiliesByGuid(STATE1)).length,
    updateFilter: () => {},
  }

  shallow(<FilterDropdownComponent {...props} />)
})
