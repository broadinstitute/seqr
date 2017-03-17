import React from 'react'
import { shallow } from 'enzyme'
import { CaseReviewBreadCrumbsComponent } from './CaseReviewBreadCrumbs'
import { getProject } from '../reducers/rootReducer'

import { STATE1 } from '../fixtures'


test('shallow-render without crashing', () => {
  /*
    project: React.PropTypes.object.isRequired,
   */

  const props = {
    project: getProject(STATE1),
  }

  shallow(<CaseReviewBreadCrumbsComponent {...props} />)
})
