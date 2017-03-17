import React from 'react'
import { shallow } from 'enzyme'
import { TableBodyComponent } from './TableBody'
import { getFamilyGuidToIndividuals, getVisibleFamiliesInSortedOrder } from '../../utils/visibleFamiliesSelector'

import { STATE1 } from '../../fixtures'


test('shallow-render without crashing', () => {
  /*
    visibleFamilies: React.PropTypes.array.isRequired,
    familyGuidToIndividuals: React.PropTypes.object.isRequired,
   */

  const props = {
    visibleFamilies: getVisibleFamiliesInSortedOrder(STATE1),
    familyGuidToIndividuals: getFamilyGuidToIndividuals(STATE1),
  }

  shallow(<TableBodyComponent {...props} />)
})
