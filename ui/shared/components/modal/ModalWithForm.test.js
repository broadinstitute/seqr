import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import ModalWithForm from './ModalWithForm'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    title: PropTypes.string.isRequired,
    submitButtonText: PropTypes.string,
    formSubmitUrl: PropTypes.string.isRequired,
    performClientSideValidation: PropTypes.func,
    handleSave: PropTypes.func,
    handleClose: PropTypes.func,
    confirmCloseIfNotSaved: PropTypes.bool.isRequired,
    children: PropTypes.node,
   */

  const props = {
    title: 'title',
    submitButtonText: 'submit',
    formSubmitUrl: 'http://url/',
    performClientSideValidation: () => {},
    handleSave: () => {},
    handleClose: () => {},
    confirmCloseIfNotSaved: true,
  }

  shallow(<ModalWithForm {...props} />)
})
