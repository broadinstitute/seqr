import React from 'react'
import { shallow } from 'enzyme'
import { ProjectCategoriesInputComponent } from './ProjectCategoriesInput'
import { getProjectsByGuid, getProjectCategoriesByGuid } from '../../reducers/rootReducer'

import { STATE1 } from '../../fixtures'


test('shallow-render without crashing', () => {
  /*
    project: React.PropTypes.object.isRequired,
    projectCategoriesByGuid: React.PropTypes.object.isRequired,
   */

  const props = {
    project: getProjectsByGuid(STATE1).R0237_1000_genomes_demo,
    projectCategoriesByGuid: getProjectCategoriesByGuid(STATE1),
  }

  shallow(<ProjectCategoriesInputComponent {...props} />)
})
