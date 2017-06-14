import React from 'react'
import { shallow } from 'enzyme'
import { ProjectTableFooterComponent } from './ProjectTableFooter'
import { getUser } from '../../reducers/rootReducer'
import { STATE1 } from '../../fixtures'

test('shallow-render without crashing', () => {
  const props = {
    user: getUser(STATE1),
    showModal: () => {},
  }

  shallow(<ProjectTableFooterComponent {...props} />)
})
