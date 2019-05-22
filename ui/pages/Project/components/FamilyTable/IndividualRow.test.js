import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import configureStore from 'redux-mock-store'

import IndividualRow from './IndividualRow'
import { STATE_WITH_2_FAMILIES } from '../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  shallow(
    <IndividualRow
      store={store}
      family={STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1}
      individual={STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1}
    />)
})
