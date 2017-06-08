import React from 'react'
import { shallow } from 'enzyme'
import { PhenotipsModalComponent } from './PhenotipsModal'
import { getPhenotipsModalIsVisible } from './state'

import { STATE1 } from '../../fixtures'


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
  }

  shallow(<PhenotipsModalComponent {...props} />)
})
