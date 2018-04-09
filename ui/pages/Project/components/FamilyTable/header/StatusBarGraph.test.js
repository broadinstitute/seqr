import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { StatusBarGraphComponent } from './StatusBarGraph'

import { getCaseReviewStatusCounts } from '../../../../CaseReview/utils/caseReviewStatusCountsSelector'

import { STATE1 } from '../../../../CaseReview/fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    caseReviewStatusCounts: PropTypes.array.isRequired,
   */

  const props = {
    caseReviewStatusCounts: getCaseReviewStatusCounts(STATE1),
  }

  shallow(<StatusBarGraphComponent {...props} />)
})
