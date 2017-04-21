import React from 'react'
import { shallow } from 'enzyme'
import { FamilyRowComponent } from './FamilyRow'
import { getProject, getFamiliesByGuid } from '../../../reducers/rootReducer'

import { STATE1 } from '../../../fixtures'


test('shallow-render without crashing', () => {
  /*
    project: React.PropTypes.object.isRequired,
    family: React.PropTypes.object.isRequired,
   */

  const props = {
    project: getProject(STATE1),
    family: getFamiliesByGuid(STATE1).F011652_1
  }

  shallow(<FamilyRowComponent {...props} />)
})
