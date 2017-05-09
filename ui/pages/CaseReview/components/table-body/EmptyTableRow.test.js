import React from 'react'
import { shallow } from 'enzyme'
import { EmptyTableRowComponent } from './EmptyTableRow'
import { getFamiliesFilter } from '../../reducers/rootReducer'

import { STATE1 } from '../../fixtures'


test('shallow-render without crashing', () => {
  /*
    familiesFilter: PropTypes.string.isRequired,
   */

  const props = {
    familiesFilter: getFamiliesFilter(STATE1),
  }

  shallow(<EmptyTableRowComponent {...props} />)
})
