import React from 'react'
import { shallow } from 'enzyme'
import Modal from './Modal'


test('shallow-render without crashing', () => {
  /*
    title: React.PropTypes.string.isRequired,
    onClose: React.PropTypes.func.isRequired,
    size: React.PropTypes.oneOf(['small', 'large', 'fullscreen']),
    children: React.PropTypes.node,
   */

  const props = {
    title: 'title',
    size: 'large',
    onClose: () => {},
  }

  shallow(<Modal {...props} />)
})
