import React from 'react'
import { shallow } from 'enzyme'
import ModalWithForm from './ModalWithForm'


test('shallow-render without crashing', () => {
  /*
    title: PropTypes.string.isRequired,
    submitButtonText: PropTypes.string,
    formSubmitUrl: PropTypes.string.isRequired,
    onValidate: PropTypes.func,
    onSave: PropTypes.func,
    onClose: PropTypes.func,
    confirmCloseIfNotSaved: PropTypes.bool.isRequired,
    children: PropTypes.node,
   */

  const props = {
    title: 'title',
    submitButtonText: 'submit',
    formSubmitUrl: 'http://url/',
    onValidate: () => {},
    onSave: () => {},
    onClose: () => {},
    confirmCloseIfNotSaved: true,
  }

  shallow(<ModalWithForm {...props} />)
})
