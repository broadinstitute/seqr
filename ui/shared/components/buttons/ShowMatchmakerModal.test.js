import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { STATE1 } from '../panel/fixtures'
import { ShowMatchmakerModalComponent } from './ShowMatchmakerModal'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<ShowMatchmakerModalComponent project={STATE1.project} family={Object.values(STATE1.familiesByGuid)[0]} />)
})
