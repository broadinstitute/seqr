import React from 'react'
import { shallow } from 'enzyme'
import { CaseReviewStatusDropdownComponent } from './CaseReviewStatusDropdown'
import { getIndividualsByGuid } from '../../../reducers/rootReducer'

import { STATE1 } from '../../../fixtures'


test('shallow-render without crashing', () => {
  /*
    individual: PropTypes.object.isRequired,
    updateIndividualsByGuid: PropTypes.func.isRequired,
   */

  const props = {
    individual: getIndividualsByGuid(STATE1).I021474_na19679,
    updateIndividualsByGuid: () => {},
  }

  shallow(<CaseReviewStatusDropdownComponent {...props} />)
})
