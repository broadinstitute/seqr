import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import StaffOnlyIcon from './StaffOnlyIcon'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    mouseOverText: PropTypes.string,
   */

  const props = {
    mouseOverText: 'text',
  }

  shallow(<StaffOnlyIcon {...props} />)
})
