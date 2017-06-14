import React from 'react'
import { shallow } from 'enzyme'
import { ProjectTableRowComponent } from './ProjectTableRow'
import { getUser, getSampleBatchesByGuid, getProjectsByGuid } from '../../reducers/rootReducer'

import { STATE1 } from '../../fixtures'


test('shallow-render without crashing', () => {
  /*
    user: PropTypes.object.isRequired,
    project: PropTypes.object.isRequired,
    sampleBatchesByGuid: PropTypes.object.isRequired,
   */

  const props = {
    user: getUser(STATE1),
    project: getProjectsByGuid(STATE1).R0237_1000_genomes_demo,
    sampleBatchesByGuid: getSampleBatchesByGuid(STATE1),
  }

  shallow(<ProjectTableRowComponent {...props} />)
})
