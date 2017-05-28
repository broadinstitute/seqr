import React from 'react'
import { shallow } from 'enzyme'
import { PedigreeImageZoomModalComponent } from './PedigreeImageZoomModal'
import { getPedigreeImageZoomModalIsVisible, getPedigreeImageZoomModalFamily } from './state'

import { STATE1 } from '../../fixtures'

test('shallow-render without crashing', () => {
  /*
    isVisible: PropTypes.bool.isRequired,
    family: PropTypes.object,
    hidePedigreeZoomModal: PropTypes.func.isRequired,
   */

  const props = {
    isVisible: getPedigreeImageZoomModalIsVisible(STATE1),
    family: getPedigreeImageZoomModalFamily(STATE1),
    hidePedigreeImageZoomModal: () => {},
  }

  shallow(<PedigreeImageZoomModalComponent {...props} />)
})
