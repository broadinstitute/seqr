import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { getUser, getProject } from 'shared/utils/commonSelectors'
import { ProjectPageUIComponent } from './ProjectPageUI'


import { STATE1 } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
   */

  const props = {
    user: getUser(STATE1),
    project: getProject(STATE1),
  }

  shallow(<ProjectPageUIComponent {...props} />)
})
