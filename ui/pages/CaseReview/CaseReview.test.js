import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { getProject } from 'redux/utils/commonDataActionsAndSelectors'
import { CaseReviewTableComponent } from './CaseReviewTable'

import { STATE1 } from './fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
   */

  const props = {
    project: getProject(STATE1),
  }

  shallow(<CaseReviewTableComponent {...props} />)
})
