import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { ShowPhenotipsModalButtonComponent } from './ShowPhenotipsModalButton'
import { showPhenotipsModal } from './phenotips-modal/PhenotipsModal-redux'

import { STATE1 } from '../fixtures'

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
    showPhenotipsModal,
  }

  shallow(<ShowPhenotipsModalButtonComponent {...props} />)
})
