import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import CategoryIndicator from './CategoryIndicator'
import { getVisibleProjects } from '../selectors'
import { STATE1 } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render with categories without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
   */

  const props = {
    project: getVisibleProjects(STATE1).find(({ projectGuid }) => projectGuid === 'R0237_1000_genomes_demo'),
  }

  shallow(<CategoryIndicator {...props} />)
})

test('shallow-render without categories without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
   */

  const props = {
    project: getVisibleProjects(STATE1).find(({ projectGuid }) => projectGuid === 'R0202_tutorial'),
  }

  shallow(<CategoryIndicator {...props} />)
})