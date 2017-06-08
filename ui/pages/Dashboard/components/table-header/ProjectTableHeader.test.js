import React from 'react'
import { shallow } from 'enzyme'
import { ProjectTableHeaderComponent } from './ProjectTableHeader'

import { getUser } from '../../reducers/rootReducer'
import { STATE1 } from '../../fixtures'

test('shallow-render without crashing', () => {
  /*
    user: PropTypes.object.isRequired,
   */

  const props = {
    user: getUser(STATE1),
  }

  shallow(<ProjectTableHeaderComponent {...props} />)
})
