import React from 'react'
import { shallow } from 'enzyme'
import { ViewPhenotipsModalComponent } from './ViewPhenotipsModal'
import { getViewPhenotipsModalIsVisible, getProject, getIndividualsByGuid } from '../../../reducers/rootReducer'

import { STATE1 } from '../../../fixtures'


test('shallow-render without crashing', () => {
  /*
    isVisible: React.PropTypes.bool.isRequired,
    project: React.PropTypes.object,
    individual: React.PropTypes.object,
    hideViewPhenotipsModal: React.PropTypes.func.isRequired,
   */

  const props = {
    isVisible: getViewPhenotipsModalIsVisible(STATE1),
    project: getProject(STATE1),
    individual: getIndividualsByGuid(STATE1).I021474_na19679,
    hideViewPhenotipsModal: () => {},
  }

  shallow(<ViewPhenotipsModalComponent {...props} />)
})
