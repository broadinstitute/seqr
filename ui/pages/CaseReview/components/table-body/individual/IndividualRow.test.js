import React from 'react'
import { shallow } from 'enzyme'
import { IndividualRowComponent } from './IndividualRow'
import { getProject, getIndividualsByGuid, getFamiliesByGuid } from '../../../reducers/rootReducer'

import { STATE1 } from '../../../fixtures'


test('shallow-render without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
    family: PropTypes.object.isRequired,
    individual: PropTypes.object.isRequired,
    showDetails: PropTypes.bool.isRequired,
   */

  const props = {
    project: getProject(STATE1),
    family: getFamiliesByGuid(STATE1).F011652_1,
    individual: getIndividualsByGuid(STATE1).I021474_na19679,
    showDetails: true,
  }

  shallow(<IndividualRowComponent {...props} />)

  const props2 = { ...props, showDetails: false }

  shallow(<IndividualRowComponent {...props2} />)
})
