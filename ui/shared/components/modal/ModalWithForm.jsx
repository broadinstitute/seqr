import React from 'react'
import PropTypes from 'prop-types'

import Modal from './Modal'
import FormWrapper from '../form/FormWrapper'


/**
 * Modal dialog that contains a Form.
 * This component is useful for forms that will only be shown by themselves in a modal dialog, and never need to appear
 * inside other components such as tabbed-panes, etc.
 */
class ModalWithForm extends React.Component
{
  static propTypes = {
    title: PropTypes.string.isRequired, // modal dialog title
    cancelButtonText: PropTypes.string,
    submitButtonText: PropTypes.string,
    getFormDataJson: PropTypes.func, // required if either performValidation or formSubmitUrl is provided
    formSubmitUrl: PropTypes.string,
    performClientSideValidation: PropTypes.func,
    handleSave: PropTypes.func,
    handleClose: PropTypes.func,
    confirmCloseIfNotSaved: PropTypes.bool.isRequired,
    children: PropTypes.node,
    size: PropTypes.string,
  }

  render() {
    return (
      <Modal title={this.props.title} size={this.props.size} handleClose={this.props.handleClose}>
        <FormWrapper
          cancelButtonText={this.props.cancelButtonText}
          submitButtonText={this.props.submitButtonText}
          getFormDataJson={this.props.getFormDataJson}
          formSubmitUrl={this.props.formSubmitUrl}
          performClientSideValidation={this.props.performClientSideValidation}
          handleSave={this.props.handleSave}
          handleClose={this.props.handleClose}
          confirmCloseIfNotSaved={this.props.confirmCloseIfNotSaved}
        >
          {this.props.children}
        </FormWrapper>
      </Modal>)
  }

}


export default ModalWithForm
