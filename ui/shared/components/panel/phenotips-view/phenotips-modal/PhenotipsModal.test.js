import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { PhenotipsModalComponent } from './PhenotipsModal'
import { getPhenotipsModalIsVisible } from './state'

import { STATE1 } from '../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    isVisible: PropTypes.bool.isRequired,
    project: PropTypes.object,
    individual: PropTypes.object,
    hidePhenotipsModal: PropTypes.func.isRequired,
   */

  const props = {
    isVisible: getPhenotipsModalIsVisible(STATE1),
    project: STATE1.project,
    individual: STATE1.individualsByGuid.I021474_na19679,
    hidePhenotipsModal: () => {},
    isViewOnly: false,
  }

  shallow(<PhenotipsModalComponent {...props} />)
})
