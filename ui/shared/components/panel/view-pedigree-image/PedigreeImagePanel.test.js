import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import PedigreeImagePanel from './PedigreeImagePanel'

import { STATE1 } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    family: PropTypes.object.isRequired,
    showPedigreeImageZoomModal: PropTypes.func.isRequired,
   */

  const props = {
    family: STATE1.familiesByGuid.F011652_1,
  }

  shallow(<PedigreeImagePanel {...props} />)
})
