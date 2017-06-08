import React from 'react'
import { shallow } from 'enzyme'
import { SortByColumnComponent } from './SortByColumn'
import { SORT_BY_DATE_CREATED, SORT_BY_NUM_FAMILIES } from '../../constants'


test('shallow-render without crashing', () => {
  /*
   currentSortColumn: PropTypes.string.isRequired,
   sortDirection: PropTypes.number.isRequired,
   updateSortColumn: PropTypes.func.isRequired,
   updateSortDirection: PropTypes.func.isRequired,
   sortBy: PropTypes.string.isRequired,
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
