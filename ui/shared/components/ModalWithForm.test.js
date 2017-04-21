import React from 'react'
import { shallow } from 'enzyme'
import ModalWithForm from './ModalWithForm'


test('shallow-render without crashing', () => {
  /*
    title: React.PropTypes.string.isRequired,
    submitButtonText: React.PropTypes.string,
    formSubmitUrl: React.PropTypes.string.isRequired,
    onValidate: React.PropTypes.func,
    onSave: React.PropTypes.func,
    onClose: React.PropTypes.func,
    confirmCloseIfNotSaved: React.PropTypes.bool.isRequired,
    children: React.PropTypes.node,
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
