import React from 'react'
import { shallow } from 'enzyme'
import { ProjectBreadCrumbsComponent } from './ProjectBreadCrumbs'
import { getProject } from '../reducers/rootReducer'

import { STATE1 } from '../fixtures'


test('shallow-render without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
   */

  const props = {
    project: getProject(STATE1),
  }

  shallow(<ProjectBreadCrumbsComponent {...props} />)
})
