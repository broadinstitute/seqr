import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { ShowDetailsToggleComponent } from './ShowDetailsToggle'
import { getShowDetails } from '../../rootReducer'

import { STATE1 } from '../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    showDetails: PropTypes.bool.isRequired,
    updateState: PropTypes.func.isRequired,
   */

  const props = {
    showDetails: getShowDetails(STATE1),
    updateState: () => {},
  }

  shallow(<ShowDetailsToggleComponent {...props} />)
})
