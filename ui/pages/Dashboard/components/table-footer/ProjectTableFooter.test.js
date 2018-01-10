import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { ProjectTableFooterComponent } from './ProjectTableFooter'
import { getUser } from '../../redux/rootReducer'
import { STATE1 } from '../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const props = {
    user: getUser(STATE1),
    showModal: () => {},
  }

  shallow(<ProjectTableFooterComponent {...props} />)
})
