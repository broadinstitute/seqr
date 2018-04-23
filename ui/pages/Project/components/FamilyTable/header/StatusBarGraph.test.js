import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'

import { getProjectIndividuals} from 'redux/rootReducer'
import { StatusBarGraphComponent } from './StatusBarGraph'

import { STATE1 } from '../../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    caseReviewStatusCounts: PropTypes.array.isRequired,
   */

  const props = {
    individuals: getProjectIndividuals(STATE1),
  }

  shallow(<StatusBarGraphComponent {...props} />)
})
