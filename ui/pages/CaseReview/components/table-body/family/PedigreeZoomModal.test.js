import React from 'react'
import { shallow } from 'enzyme'
import { PedigreeZoomModalComponent } from './PedigreeZoomModal'
import { getPedigreeZoomModalIsVisible, getFamiliesByGuid } from '../../../reducers/rootReducer'

import { STATE1 } from '../../../fixtures'


test('shallow-render without crashing', () => {
  /*
    isVisible: React.PropTypes.bool.isRequired,
    family: React.PropTypes.object,
    hidePedigreeZoomModal: React.PropTypes.func.isRequired,
   */

  const props = {
    isVisible: getPedigreeZoomModalIsVisible(STATE1),
    family: getFamiliesByGuid(STATE1).F011652_1,
    hidePedigreeZoomModal: () => {},
  }

  shallow(<PedigreeZoomModalComponent {...props} />)
})
