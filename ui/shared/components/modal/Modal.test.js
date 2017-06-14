import React from 'react'
import { shallow } from 'enzyme'
import Modal from './Modal'


test('shallow-render without crashing', () => {
  /*
    title: PropTypes.string.isRequired,
    onClose: PropTypes.func.isRequired,
    size: PropTypes.oneOf(['small', 'large', 'fullscreen']),
    children: PropTypes.node,
   */

  const props = {
    title: 'title',
    size: 'large',
    onClose: () => {},
  }

  shallow(<Modal {...props} />)
})
