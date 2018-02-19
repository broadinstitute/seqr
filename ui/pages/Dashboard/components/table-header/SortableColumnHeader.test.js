import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { SortableColumnHeaderComponent } from './SortableColumnHeader'
import { SORT_BY_DATE_CREATED, SORT_BY_NUM_FAMILIES } from '../../constants'

configure({ adapter: new Adapter() })

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
    columnLabel: 'test',
    sortDirection: -1,
    updateSortColumn: () => {},
    updateSortDirection: () => {},
    sortBy: SORT_BY_DATE_CREATED,
  }
  shallow(<SortableColumnHeaderComponent {...props1} />)


  const props2 = { ...props1, sortBy: SORT_BY_NUM_FAMILIES }
  shallow(<SortableColumnHeaderComponent {...props2} />)
})
