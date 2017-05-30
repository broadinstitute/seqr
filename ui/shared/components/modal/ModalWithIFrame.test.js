import React from 'react'
import { shallow } from 'enzyme'
import ModalWithIFrame from './ModalWithIFrame'


test('shallow-render without crashing', () => {
  /*
    title: PropTypes.string.isRequired,
    url: PropTypes.string.isRequired,
    onClose: PropTypes.func,
   */

  const props = {
    title: 'title',
    url: 'http://url',
    onClose: () => {},
  }

  shallow(<ModalWithIFrame {...props} />)
})
