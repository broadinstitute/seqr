import React, { createElement } from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Field, reduxForm, getFormSyncErrors, getFormSyncWarnings, submit } from 'redux-form'
import { Form, Message } from 'semantic-ui-react'
import flatten from 'lodash/flatten'

import { closeModal, setModalConfirm } from 'redux/utils/modalReducer'
import ButtonPanel from './ButtonPanel'
import RequestStatus from './RequestStatus'

const MessagePanel = styled(Message)`
  margin: 1em 2em !important;
`

export const validators = {
  required: value => (value ? undefined : 'Required'),
}

const renderField = (props) => {
  const { fieldComponent = Form.Input, meta: { touched, invalid }, input, ...additionalProps } = props
  return createElement(fieldComponent, { error: touched && invalid, ...input, ...additionalProps })
}

renderField.propTypes = {
  fieldComponent: PropTypes.oneOfType([PropTypes.func, PropTypes.string]),
  meta: PropTypes.object,
  input: PropTypes.object,
}

class ReduxFormWrapper extends React.Component {

  static propTypes = {
    /* A unique string identifier for the form */
    form: PropTypes.string.isRequired,

    /* A unique string identifier for the parent modal. Defaults to the "form" identifier */
    modalName: PropTypes.string,

    /* A callback when a valid form is submitted. Will be passed all the form data */
    /* Note that this is different from handleSubmit, which is a redux-form supplied handler that should never be overridden */
    onSubmit: PropTypes.func.isRequired,

    /* A callback for when the cancel button is selected */
    handleClose: PropTypes.func.isRequired,

    /* Whether or not to close the parent modal once form submission succeeds. Defaults to true */
    closeOnSuccess: PropTypes.bool,

    /* Whether or not to show a confirm message before canceling if there are unsaved changes */
    confirmCloseIfNotSaved: PropTypes.bool,

    showErrorPanel: PropTypes.bool,
    cancelButtonText: PropTypes.string,
    submitButtonText: PropTypes.string,

    /* Submit the form whenever values change rather than with a submit button */
    submitOnChange: PropTypes.bool,

    /* An optional secondary submit button with its own submit callback */
    secondarySubmitButton: PropTypes.node,
    onSecondarySubmit: PropTypes.func,

    /* form size (see https://react.semantic-ui.com/collections/form#form-example-size) */
    size: PropTypes.string,

    /* Array of objects representing the fields to show in the form. */
    /* Each field must have a name and a component, and can have any additional props accepted by redux-form's Field */
    fields: PropTypes.arrayOf(PropTypes.object),

    /* React child component class. Mutually exclusive with fields */
    renderChildren: PropTypes.func,

    /*  These props are added by redux-form and should never be passed explicitly */
    submitting: PropTypes.bool,
    submitFailed: PropTypes.bool,
    submitSucceeded: PropTypes.bool,
    invalid: PropTypes.bool,
    dirty: PropTypes.bool,
    error: PropTypes.array,
    validationErrors: PropTypes.object,
    validationWarnings: PropTypes.object,
    warning: PropTypes.string,
    handleSubmit: PropTypes.func,
    setModalConfirm: PropTypes.func,
    submit: PropTypes.func,
  }

  static defaultProps = {
    closeOnSuccess: true,
    cancelButtonText: 'Cancel',
    submitButtonText: 'Submit',
  }

  handleUnconfirmedClose = () => this.props.handleClose()

  render() {
    let saveStatus = RequestStatus.NONE
    if (this.props.submitSucceeded) {
      saveStatus = RequestStatus.SUCCEEDED
    } else if (this.props.submitFailed) {
      saveStatus = RequestStatus.ERROR
    }
    const saveErrorMessage = this.props.submitFailed ?
      (this.props.error && this.props.error.join('; ')) || (this.props.invalid ? 'Invalid input' : 'Unknown') : null

    const fieldComponents = this.props.renderChildren ? React.createElement(this.props.renderChildren) :
      this.props.fields.map(({ component, name, displayOnly, ...fieldProps }) => {
        return displayOnly ? React.createElement(component, { key: name }) : (
          <Field key={name} name={name} component={renderField} fieldComponent={component} {...fieldProps} />
        )
      })

    const warningMessages = this.props.warning || flatten(Object.values(this.props.validationWarnings))
    const errorMessages = this.props.error || flatten(Object.values(this.props.validationErrors))

    return (
      <Form onSubmit={this.props.handleSubmit} size={this.props.size} loading={this.props.submitting}>
        {fieldComponents}
        {this.props.showErrorPanel && (this.props.dirty || this.props.submitFailed) && [
          warningMessages && warningMessages.length > 0 ? <MessagePanel key="w" warning visible list={warningMessages} /> : null,
          errorMessages && errorMessages.length > 0 ? <MessagePanel key="e" error visible list={errorMessages} /> : null,
        ]}
        {
          this.props.secondarySubmitButton && this.props.onSecondarySubmit &&
          React.cloneElement(this.props.secondarySubmitButton, { onClick: this.props.handleSubmit(values => this.props.onSecondarySubmit(values)) })
        }
        {
          this.props.submitOnChange ?
            <RequestStatus status={this.props.submitting ? RequestStatus.IN_PROGRESS : saveStatus} errorMessage={saveErrorMessage} /> :
            <ButtonPanel
              cancelButtonText={this.props.cancelButtonText}
              submitButtonText={this.props.submitButtonText}
              saveStatus={saveStatus}
              saveErrorMessage={saveErrorMessage}
              handleClose={this.handleUnconfirmedClose}
            />
        }
      </Form>
    )
  }

  shouldComponentUpdate(nextProps, nextState) {
    const updateProps = [
      'modalName',
      'form',
      'submitSucceeded',
      'submitFailed',
      'closeOnSuccess',
      'error',
      'invalid',
      'renderChildren',
      'fields',
      'showErrorPanel',
      'validationErrors',
      'validationWarnings',
      'size',
      'submitting',
      'warning',
      'secondarySubmitButton',
      'submitOnChange',
      'cancelButtonText',
      'submitButtonText',
      'dirty',
      'confirmCloseIfNotSaved',
    ]
    if (updateProps.some(k => nextProps[k] !== this.props[k])) {
      return true
    }
    return nextState !== this.state
  }

  componentWillUpdate(nextProps) {
    if (nextProps.submitSucceeded && nextProps.closeOnSuccess) {
      this.props.handleClose(true)
    } else if (this.props.submitOnChange && nextProps.dirty && !this.props.dirty) {
      this.props.submit()
    } else if (this.props.confirmCloseIfNotSaved) {
      if (nextProps.dirty && !this.props.dirty) {
        this.props.setModalConfirm('The form contains unsaved changes. Are you sure you want to close it?')
      } else if (!nextProps.dirty && this.props.dirty) {
        this.props.setModalConfirm(null)
      }
    }
  }
}

const mapStateToProps = (state, ownProps) => ({
  validationErrors: getFormSyncErrors(ownProps.form)(state),
  validationWarnings: getFormSyncWarnings(ownProps.form)(state),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    handleClose: (confirmed) => {
      dispatch(closeModal(ownProps.modalName || ownProps.form, confirmed))
    },
    setModalConfirm: (confirm) => {
      dispatch(setModalConfirm(ownProps.modalName || ownProps.form, confirm))
    },
    submit: () => dispatch(submit(ownProps.form)),
  }
}


export default reduxForm()(connect(mapStateToProps, mapDispatchToProps)(ReduxFormWrapper))
