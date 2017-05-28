import React from 'react'
import { shallow } from 'enzyme'
import { PedigreeImageComponent } from './PedigreeImagePanel'
import { getPedigreeImageZoomModalFamily } from './zoom-modal/state'

import { STATE1 } from '../fixtures'


test('shallow-render without crashing', () => {
  /*
    family: PropTypes.object.isRequired,
    showPedigreeImageZoomModal: PropTypes.func.isRequired,
   */

  const props = {
    family: getPedigreeImageZoomModalFamily(STATE1),
    showPedigreeImageZoomModal: () => {},
  }

  shallow(<PedigreeImageComponent {...props} />)
})
