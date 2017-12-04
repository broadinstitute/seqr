import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { CategoryIndicatorComponent } from './CategoryIndicator'
import { getProjectsByGuid } from '../../reducers/rootReducer'

import { STATE1 } from '../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
    showModal: PropTypes.func.isRequired,
   */

  const props = {
    project: getProjectsByGuid(STATE1).R0237_1000_genomes_demo,
    showModal: () => {},
  }

  shallow(<CategoryIndicatorComponent {...props} />)
})
