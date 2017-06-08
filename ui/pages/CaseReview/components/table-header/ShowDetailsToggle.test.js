import React from 'react'
import { shallow } from 'enzyme'
import { ShowDetailsToggleComponent } from './ShowDetailsToggle'
import { getShowDetails } from '../../reducers/rootReducer'

import { STATE1 } from '../../fixtures'


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
