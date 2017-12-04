import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import ModalWithIFrame from './ModalWithIFrame'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    title: PropTypes.string.isRequired,
    url: PropTypes.string.isRequired,
    handleClose: PropTypes.func,
   */

  const props = {
    title: 'title',
    url: 'http://url',
    handleClose: () => {},
  }

  shallow(<ModalWithIFrame {...props} />)
})
