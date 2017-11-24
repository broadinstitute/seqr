import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { CaseReviewStatusDropdownComponent } from './CaseReviewStatusDropdown'
import { getIndividualsByGuid } from '../../../reducers/rootReducer'

import { STATE1 } from '../../../fixtures'

configure({ adapter: new Adapter() })

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
