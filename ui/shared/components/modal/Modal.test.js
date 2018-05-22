import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { ModalComponent } from './Modal'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    title: PropTypes.string.isRequired,
    handleClose: PropTypes.func.isRequired,
    size: PropTypes.oneOf(['small', 'large', 'fullscreen']),
    children: PropTypes.node,
   */

  const props = {
    title: 'title',
    size: 'large',
    handleClose: () => {},
  }

  shallow(<ModalComponent {...props} />)
})
