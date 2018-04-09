import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { getUser, getProject, getProjectFamilies } from 'redux/rootReducer'
import { FamilyRowComponent } from './FamilyRow'

import { STATE_WITH_2_FAMILIES } from '../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
    family: PropTypes.object.isRequired,
   */

  const props = {
    project: getProject(STATE_WITH_2_FAMILIES),
    family: getProjectFamilies(STATE_WITH_2_FAMILIES)[0],
    user: getUser(STATE_WITH_2_FAMILIES),
    showDetails: true,
  }

  shallow(<FamilyRowComponent {...props} />)
})
