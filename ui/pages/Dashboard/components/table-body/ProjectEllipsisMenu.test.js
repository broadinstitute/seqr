import React from 'react'
import { shallow } from 'enzyme'
import { ProjectEllipsisMenuComponent } from './ProjectEllipsisMenu'
import { getUser, getProjectsByGuid } from '../../reducers/rootReducer'

import { STATE1 } from '../../fixtures'


test('shallow-render without crashing', () => {
  /*
    user: PropTypes.object.isRequired,
    project: PropTypes.object.isRequired,
    showModal: PropTypes.func.isRequired,
   */

  const props = {
    user: getUser(STATE1),
    project: getProjectsByGuid(STATE1).R0237_1000_genomes_demo,
    showModal: () => {},
  }

  shallow(<ProjectEllipsisMenuComponent {...props} />)
})
