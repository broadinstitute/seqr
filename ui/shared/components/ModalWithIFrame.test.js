import React from 'react'
import { shallow } from 'enzyme'
import ModalWithIFrame from './ModalWithIFrame'


test('shallow-render without crashing', () => {
  /*
    title: React.PropTypes.string.isRequired,
    url: React.PropTypes.string.isRequired,
    onClose: React.PropTypes.func,
   */

  const props = {
    title: 'title',
    url: 'http://url',
    onClose: () => {},
  }

  shallow(<ModalWithIFrame {...props} />)
})
