import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { FilterDropdownComponent } from './FilterDropdown'
import { getFamiliesFilter } from '../../../selectors'
import { STATE1 } from '../../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    familiesFilter: PropTypes.string.isRequired,
    filteredCount: PropTypes.number.isRequired,
    totalCount: PropTypes.number.isRequired,
    updateFilter: PropTypes.func.isRequired,
   */

  const props = {
    familiesFilter: getFamiliesFilter(STATE1),
    updateFilter: () => {},
  }

  shallow(<FilterDropdownComponent {...props} />)
})
