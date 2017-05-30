import React from 'react'
import { shallow } from 'enzyme'
import { ShowPhenotipsModalButtonComponent } from './ShowPhenotipsModalButton'
import { showPhenotipsModal } from './phenotips-modal/state'

import { STATE1 } from '../fixtures'


test('shallow-render without crashing', () => {
  /*
   project: PropTypes.object.isRequired,
   individual: PropTypes.object.isRequired,
   showPhenotipsModal: PropTypes.func.isRequired,
   */

  const props = {
    project: STATE1.project,
    individual: STATE1.individualsByGuid.I021474_na19679,
    showPhenotipsModal,
  }

  shallow(<ShowPhenotipsModalButtonComponent {...props} />)
})
