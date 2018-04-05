import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { SortDirectionToggleComponent } from './SortDirectionToggle'
import { getFamiliesSortDirection } from '../../../reducers'

import { STATE1 } from '../../../fixtures'

configure({ adapter: new Adapter() })

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
