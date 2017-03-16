import React from 'react'
import { shallow } from 'enzyme'
import { CaseReviewTableComponent } from './CaseReviewTable'
import { getProject } from '../reducers/rootReducer'

import { STATE1 } from '../fixtures'


test('shallow-render without crashing', () => {
  /*
    project: React.PropTypes.object.isRequired,
   */

  const props = {
    project: getProject(STATE1),
  }

  shallow(<CaseReviewTableComponent {...props} />)
})
