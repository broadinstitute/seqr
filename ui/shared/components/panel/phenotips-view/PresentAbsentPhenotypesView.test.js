import React from 'react'
import { shallow } from 'enzyme'
import PresentAbsentPhenotypesView from './PresentAbsentPhenotypesView'

import { STATE1 } from '../fixtures'


test('shallow-render without crashing', () => {
  /*
   features: PropTypes.array.isRequired,
   */

  const props = {
    features: STATE1.individualsByGuid.I021474_na19679.phenotipsData.features,
  }

  shallow(<PresentAbsentPhenotypesView {...props} />)
})
