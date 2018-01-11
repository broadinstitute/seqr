import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { PedigreeImageComponent } from './PedigreeImagePanel'
import { getPedigreeImageZoomModalFamily } from './zoom-modal/PedigreeImageZoomModal-redux'

import { STATE1 } from '../fixtures'

configure({ adapter: new Adapter() })

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
