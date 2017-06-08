import React from 'react'
import { shallow } from 'enzyme'
import { StatusBarGraphComponent } from './StatusBarGraph'

import { getCaseReviewStatusCounts } from '../../utils/caseReviewStatusCountsSelector'

import { STATE1 } from '../../fixtures'


test('shallow-render without crashing', () => {
  /*
    caseReviewStatusCounts: PropTypes.array.isRequired,
   */

  const props = {
    caseReviewStatusCounts: getCaseReviewStatusCounts(STATE1),
  }

  shallow(<StatusBarGraphComponent {...props} />)
})
