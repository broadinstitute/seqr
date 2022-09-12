import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'

import EditDatasetsButton from './EditDatasetsButton'
import { STATE_WITH_2_FAMILIES, DATA_MANAGER_USER } from '../fixtures'

configure({ adapter: new Adapter() })

const PROJECT = STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo

test('shallow-render edit datasets', () => {
  shallow(<EditDatasetsButton project={PROJECT} user={DATA_MANAGER_USER} />)
})

test('shallow-render load workspace data', () => {
  shallow(
    <EditDatasetsButton project={PROJECT} user={STATE_WITH_2_FAMILIES.user} />,
  )
})
