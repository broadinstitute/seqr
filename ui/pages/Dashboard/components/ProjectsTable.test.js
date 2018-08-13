import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { ProjectsTableComponent } from './ProjectsTable'

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
