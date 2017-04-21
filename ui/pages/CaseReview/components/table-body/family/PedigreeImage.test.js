import React from 'react'
import { shallow } from 'enzyme'
import { PedigreeImageComponent } from './PedigreeImage'
import { getFamiliesByGuid } from '../../../reducers/rootReducer'

import { STATE1 } from '../../../fixtures'


test('shallow-render without crashing', () => {
  /*
    family: React.PropTypes.object.isRequired,
    showPedigreeZoomModal: React.PropTypes.func.isRequired,
   */

  const props = {
    family: getFamiliesByGuid(STATE1).F011652_1,
    showPedigreeZoomModal: () => {},
  }

  shallow(<PedigreeImageComponent {...props} />)
})
