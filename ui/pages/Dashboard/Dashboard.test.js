import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { ProjectsTableComponent } from './Dashboard'

configure({ adapter: new Adapter() })


test('shallow-render without crashing', () => {
  /*
   visibleProjects: PropTypes.array.isRequired,
   */

  const props = {
    visibleProjects: [],
    fetchProjects: () => {},
    user: {},
  }

  shallow(<ProjectsTableComponent {...props} />)
})
