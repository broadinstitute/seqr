import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'

import EditDatasetsButton from './EditDatasetsButton'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(
    <EditDatasetsButton
      project={STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo}
      user={STATE_WITH_2_FAMILIES.user}
    />,
  )
})
