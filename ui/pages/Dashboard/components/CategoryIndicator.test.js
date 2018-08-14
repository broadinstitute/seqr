import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { getProjectsByGuid, getProjectCategoriesByGuid } from 'redux/selectors'
import { CategoryIndicatorComponent } from './CategoryIndicator'
import { STATE1 } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render with categories without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
   */

  const props = {
    project: getProjectsByGuid(STATE1).R0237_1000_genomes_demo,
    projectCategoriesByGuid: getProjectCategoriesByGuid(STATE1),
  }

  shallow(<CategoryIndicatorComponent {...props} />)
})

test('shallow-render without categories without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
   */

  const props = {
    project: getProjectsByGuid(STATE1).R0202_tutorial,
    projectCategoriesByGuid: getProjectCategoriesByGuid(STATE1),
  }

  shallow(<CategoryIndicatorComponent {...props} />)
})