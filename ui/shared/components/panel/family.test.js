import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { getUser } from 'redux/selectors'
import { FamilyComponent } from './family'

import { STATE1 } from './fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
    family: PropTypes.object.isRequired,
   */

  const props = {
    project: STATE1.project,
    family: Object.values(STATE1.familiesByGuid)[0],
    user: getUser(STATE1),
  }

  shallow(<FamilyComponent {...props} />)
})
