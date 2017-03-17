import React from 'react'
import { shallow } from 'enzyme'
import { SortByColumnComponent } from './SortByColumn'
import { SORT_BY_DATE_CREATED, SORT_BY_NUM_FAMILIES } from '../../constants'


test('shallow-render without crashing', () => {
  /*
   currentSortColumn: React.PropTypes.string.isRequired,
   sortDirection: React.PropTypes.number.isRequired,
   updateSortColumn: React.PropTypes.func.isRequired,
   updateSortDirection: React.PropTypes.func.isRequired,
   sortBy: React.PropTypes.string.isRequired,
   */

  const props1 = {
    currentSortColumn: SORT_BY_DATE_CREATED,
    sortDirection: -1,
    updateSortColumn: () => {},
    updateSortDirection: () => {},
    sortBy: SORT_BY_DATE_CREATED,
  }
  shallow(<SortByColumnComponent {...props1} />)


  const props2 = { ...props1, sortBy: SORT_BY_NUM_FAMILIES }
  shallow(<SortByColumnComponent {...props2} />)
})
