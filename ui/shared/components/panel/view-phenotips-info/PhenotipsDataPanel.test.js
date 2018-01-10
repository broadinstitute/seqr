import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { PhenotipsDataPanelComponent } from './PhenotipsDataPanel'

import { STATE1 } from '../fixtures'

configure({ adapter: new Adapter() })

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
    showEditPhenotipsLink: true,
    showPhenotipsModal: () => {},
  }

  shallow(<PhenotipsDataPanelComponent {...props} />)

  const props2 = { ...props, showDetails: false }

  shallow(<PhenotipsDataPanelComponent {...props2} />)
})
