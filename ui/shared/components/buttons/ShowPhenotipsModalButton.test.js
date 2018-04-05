import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import ShowPhenotipsModalButton from './ShowPhenotipsModalButton'

import { STATE1 } from '../panel/fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
   project: PropTypes.object.isRequired,
   individual: PropTypes.object.isRequired,
   showPhenotipsModal: PropTypes.func.isRequired,
   */

  const props = {
    project: STATE1.project,
    individual: STATE1.individualsByGuid.I021474_na19679,
    isViewOnly: false,
  }

  shallow(<ShowPhenotipsModalButton {...props} />)
})
