import React from 'react'
import { shallow } from 'enzyme'
import { CategoryIndicatorComponent } from './CategoryIndicator'
import { getProjectsByGuid } from '../../reducers/rootReducer'

import { STATE1 } from '../../fixtures'


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
