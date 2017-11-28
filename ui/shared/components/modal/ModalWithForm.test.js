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
