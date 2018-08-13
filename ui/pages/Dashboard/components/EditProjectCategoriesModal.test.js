import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { EditProjectCategoriesModalComponent } from './EditProjectCategoriesModal'
import { getProjectsByGuid, getProjectCategoriesByGuid } from 'redux/selectors'

import { STATE1, PROJECT_GUID } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {

  const props = {
    project: getProjectsByGuid(STATE1)[PROJECT_GUID],
    updateProject: () => {},
    projectCategoriesByGuid: () => getProjectCategoriesByGuid(STATE1),
  }

  shallow(<EditProjectCategoriesModalComponent {...props} />)
})
