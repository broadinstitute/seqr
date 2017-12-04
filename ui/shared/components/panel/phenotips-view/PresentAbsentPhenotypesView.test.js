import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import PresentAbsentPhenotypesView from './PresentAbsentPhenotypesView'

import { STATE1 } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
   features: PropTypes.array.isRequired,
   */

  const props = {
    features: STATE1.individualsByGuid.I021474_na19679.phenotipsData.features,
  }

  shallow(<PresentAbsentPhenotypesView {...props} />)
})
