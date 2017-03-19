import React from 'react'
import { shallow } from 'enzyme'
import StaffOnlyIcon from './StaffOnlyIcon'


test('shallow-render without crashing', () => {
  /*
    mouseOverText: React.PropTypes.string,
   */

  const props = {
    mouseOverText: 'text',
  }

  shallow(<StaffOnlyIcon {...props} />)
})
