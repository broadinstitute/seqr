import React from 'react'
import { shallow } from 'enzyme'
import { PhenotipsDataPanelComponent } from './PhenotipsDataPanel'

import { STATE1 } from '../fixtures'


test('shallow-render without crashing', () => {
  /*
   project: PropTypes.object.isRequired,
   individual: PropTypes.object.isRequired,
   showDetails: PropTypes.bool.isRequired,
   showPhenotipsModal: PropTypes.func.isRequired,
   */

  const props = {
    project: STATE1.project,
    individual: STATE1.individualsByGuid.I021474_na19679,
    showDetails: true,
    showPhenotipsModal: () => {},
  }

  shallow(<PhenotipsDataPanelComponent {...props} />)

  const props2 = { ...props, showDetails: false }

  shallow(<PhenotipsDataPanelComponent {...props2} />)
})
