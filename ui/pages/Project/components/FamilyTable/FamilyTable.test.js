import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { FamilyTableComponent } from './FamilyTable'
import { getVisibleFamiliesInSortedOrder } from '../../selectors'

import { STATE1 } from '../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    visibleFamilies: PropTypes.array.isRequired,
    familyGuidToIndividuals: PropTypes.object.isRequired,
   */

  const props = {
    visibleFamilies: Object.values(STATE1.familiesByGuid),
    match: { params: {} },
  }

  shallow(<FamilyTableComponent {...props} />)
})
