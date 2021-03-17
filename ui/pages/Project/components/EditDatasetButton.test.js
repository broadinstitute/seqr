import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'

import EditDatasetsButton from './EditDatasetsButton'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<EditDatasetsButton user={STATE_WITH_2_FAMILIES.user} />)
})
