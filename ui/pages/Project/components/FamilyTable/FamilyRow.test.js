import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { getUser, getProject, getFamiliesByGuid } from 'redux/utils/commonDataActionsAndSelectors'
import { FamilyRowComponent } from './FamilyRow'

import { STATE1 } from '../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
    family: PropTypes.object.isRequired,
   */

  const props = {
    project: getProject(STATE1),
    family: getFamiliesByGuid(STATE1).F011652_1,
    user: getUser(STATE1),
    showDetails: true,
  }

  shallow(<FamilyRowComponent {...props} />)
})
