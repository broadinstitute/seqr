import React from 'react'
import { shallow } from 'enzyme'
import { EllipsisMenuComponent } from './EllipsisMenu'
import { getUser, getProjectsByGuid } from '../../reducers/rootReducer'

import { STATE1 } from '../../fixtures'


test('shallow-render without crashing', () => {
  /*
    user: React.PropTypes.object.isRequired,
    project: React.PropTypes.object.isRequired,
    showModal: React.PropTypes.func.isRequired,
   */

  const props = {
    user: getUser(STATE1),
    project: getProjectsByGuid(STATE1).R0237_1000_genomes_demo,
    showModal: () => {},
  }

  shallow(<EllipsisMenuComponent {...props} />)
})
