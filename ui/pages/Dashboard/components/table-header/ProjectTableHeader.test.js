import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { ProjectTableHeaderComponent } from './ProjectTableHeader'

import { getUser } from '../../reducers/rootReducer'
import { STATE1 } from '../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    user: PropTypes.object.isRequired,
   */

  const props = {
    user: getUser(STATE1),
  }

  shallow(<ProjectTableHeaderComponent {...props} />)
})
