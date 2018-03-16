import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { ProjectCategoriesInputComponent } from './ProjectCategoriesInput'
import { getProjectsByGuid, getProjectCategoriesByGuid } from '../../../../redux/rootReducer'

import { STATE1 } from '../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
    projectCategoriesByGuid: PropTypes.object.isRequired,
   */

  const props = {
    project: getProjectsByGuid(STATE1).R0237_1000_genomes_demo,
    projectCategoriesByGuid: getProjectCategoriesByGuid(STATE1),
  }

  shallow(<ProjectCategoriesInputComponent {...props} />)
})
