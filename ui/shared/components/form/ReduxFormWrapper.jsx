/* eslint-disable jsx-a11y/label-has-for */

import React, { createElement } from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { createSelector } from 'reselect'
import { connect } from 'react-redux'
import { Field, FieldArray, reduxForm, getFormSyncErrors, getFormSyncWarnings } from 'redux-form'
import { Form, Message, Icon, Popup } from 'semantic-ui-react'
import flatten from 'lodash/flatten'

import { closeModal, setModalConfirm } from 'redux/utils/modalReducer'
import ButtonLink from '../buttons/ButtonLink'
import ButtonPanel from './ButtonPanel'
import RequestStatus from './RequestStatus'

const StyledForm = styled(({ hasSubmitButton, inline, ...props }) => <Form {...props} />)`
  min-height: inherit;
  display: ${props => (props.inline ? 'inline-block' : 'block')};
  padding-bottom: ${props => props.hasSubmitButton && '40px'};
  
  .field.inline {
    display: inline;
  }
`

const MessagePanel = styled(Message)`
  margin: 1em 2em !important;
`

export const validators = {
  required: value => (value ? undefined : 'Required'),
  requiredBoolean: value => ((value === true || value === false) ? undefined : 'Required'),
}

const renderField = (props) => {
  const { fieldComponent = Form.Input, meta: { touched, invalid }, submitForm, input, ...additionalProps } = props
  const { onChange, ...additionalInput } = input
  const onChangeSubmit = submitForm ? (data) => {
    onChange(data)
    submitForm({ [props.input.name]: data })
  } : onChange
  return createElement(fieldComponent, { error: touched && invalid, meta: props.meta, onChange: onChangeSubmit, ...additionalInput, ...additionalProps })
}

renderField.propTypes = {
  fieldComponent: PropTypes.oneOfType([PropTypes.func, PropTypes.string]),
  meta: PropTypes.object,
  input: PropTypes.object,
  submitForm: PropTypes.func,
}

export const configuredFields = props =>
  props.fields.map(({ component, name, isArrayField, addArrayElement, key, label, labelHelp, ...fieldProps }) => {
    const baseProps = {
      key: key || name,
      name,
    }
    const singleFieldProps = {
      component: renderField,
      fieldComponent: component,
      submitForm: props.submitOnChange ? props.onSubmit : null,
      label: labelHelp ?
        <label> {label} <Popup trigger={<Icon name="question circle outline" />} content={labelHelp} size="small" position="top center" /></label>
        : label,
      ...fieldProps,
    }
    return isArrayField ?
      <FieldArray {...baseProps} component={({ fields }) =>
        <div className="field">
          <label>{label}</label>
          {fields.map((fieldPath, i) => <Field key={fieldPath} name={fieldPath} {...singleFieldProps} removeField={() => fields.remove(i)} />)}
          {addArrayElement && <ButtonLink onClick={() => fields.push(addArrayElement.newValue)}><Icon link name="plus" />{addArrayElement.label}</ButtonLink>}
        </div>}
      /> :
      <Field {...baseProps} {...singleFieldProps} />
  })

class ReduxFormWrapper extends React.Component {

  static propTypes = {
    /* A unique string identifier for the form */
    form: PropTypes.string.isRequired, //eslint-disable-line react/no-unused-prop-types

    /* A unique string identifier for the parent modal. Defaults to the "form" identifier */
    modalName: PropTypes.string, //eslint-disable-line react/no-unused-prop-types

    /* A callback when a valid form is submitted. Will be passed all the form data */
    /* Note that this is different from handleSubmit, which is a redux-form supplied handler that should never be overridden */
    onSubmit: PropTypes.func.isRequired, //eslint-disable-line react/no-unused-prop-types

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

    /* Whether form should be rendered inline instead of the default block display */
    inline: PropTypes.bool,

    /* Array of objects representing the fields to show in the form. */
    /* Each field must have a name and a component, and can have any additional props accepted by redux-form's Field */
    fields: PropTypes.arrayOf(PropTypes.object), //eslint-disable-line react/no-unused-prop-types

    /* React child component class. Mutually exclusive with fields */
    renderChildren: PropTypes.func,

    /*  These props are added by redux-form and should never be passed explicitly */
    submitting: PropTypes.bool,
    submitFailed: PropTypes.bool,
    submitSucceeded: PropTypes.bool,
    dirty: PropTypes.bool,
    errorMessages: PropTypes.array,
    warningMessages: PropTypes.array,
    handleSubmit: PropTypes.func,
    setModalConfirm: PropTypes.func,
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

    const saveErrorMessage =
      (this.props.errorMessages && this.props.errorMessages.length > 0 && this.props.errorMessages.join('; ')) ||
      (this.props.warningMessages && this.props.warningMessages.length > 0 && this.props.warningMessages.join('; ')) ||
      (this.props.submitFailed ? 'Error' : null)

    const fieldComponents = this.props.renderChildren ? React.createElement(this.props.renderChildren) : configuredFields(this.props)

    return (
      <StyledForm onSubmit={this.props.handleSubmit} size={this.props.size} loading={this.props.submitting} hasSubmitButton={!this.props.submitOnChange} inline={this.props.inline}>
        {fieldComponents}
        {this.props.showErrorPanel && ['warningMessages', 'errorMessages'].map(messagesKey => (
          this.props[messagesKey] && this.props[messagesKey].length > 0 ? <MessagePanel key={messagesKey} error visible list={this.props[messagesKey]} /> : null
        ))}
        {
          this.props.secondarySubmitButton && this.props.onSecondarySubmit &&
          React.cloneElement(this.props.secondarySubmitButton, { onClick: this.props.handleSubmit(values => this.props.onSecondarySubmit(values)) })
        }
        {
          !this.props.submitOnChange &&
            <ButtonPanel
              cancelButtonText={this.props.cancelButtonText}
              submitButtonText={this.props.submitButtonText}
              saveStatus={saveStatus}
              saveErrorMessage={saveErrorMessage}
              handleClose={this.handleUnconfirmedClose}
            />
        }
      </StyledForm>
    )
  }

  shouldComponentUpdate(nextProps, nextState) {
    const updateProps = [
      'modalName',
      'form',
      'submitSucceeded',
      'submitFailed',
      'closeOnSuccess',
      'renderChildren',
      'fields',
      'showErrorPanel',
      'size',
      'submitting',
      'secondarySubmitButton',
      'submitOnChange',
      'cancelButtonText',
      'submitButtonText',
      'dirty',
      'confirmCloseIfNotSaved',
      'initialValues',
    ]
    const listUpdateProps = [
      'errorMessages',
      'warningMessages',
    ]
    if (updateProps.some(k => nextProps[k] !== this.props[k])) {
      return true
    }
    if (listUpdateProps.some(k => (
      (nextProps[k] && this.props[k] && nextProps[k].length === this.props[k].length) ? nextProps[k].some((val, i) => val !== this.props[k][i]) : nextProps[k] !== this.props[k]
    ))) {
      return true
    }
    return nextState !== this.state
  }

  componentWillUpdate(nextProps) {
    if (nextProps.submitSucceeded && nextProps.closeOnSuccess) {
      this.props.handleClose(true)
    } else if (this.props.confirmCloseIfNotSaved) {
      if (nextProps.dirty && !this.props.dirty) {
        this.props.setModalConfirm('The form contains unsaved changes. Are you sure you want to close it?')
      } else if (!nextProps.dirty && this.props.dirty) {
        this.props.setModalConfirm(null)
      }
    }
  }
}

const getValidationErrorList = validationErrors =>
  (validationErrors ? flatten(Object.values(validationErrors)).filter(err => err) : null)
const getValidationErrors = createSelector(
  (state, props) => (props.submitFailed ? getFormSyncErrors(props.form)(state) : null),
  getValidationErrorList,
)
const getValidationWarnings = createSelector(
  (state, props) => (props.submitFailed ? getFormSyncWarnings(props.form)(state) : null),
  getValidationErrorList,
)

// redux-form does not support throwing submission warnings so this is a work around
const getSubmissionWarnings = (state, props) => props.warning || (props.error && props.error.map(error => error.warning).filter(warning => warning))
const getSubmissionErrors = (state, props) => props.error && props.error.filter(error => !error.warning)

const getErrors = (submissionErrors, validationErrors) =>
  ((submissionErrors && submissionErrors.length > 0) ? submissionErrors : validationErrors)

const getErrorMessages = createSelector(
  getSubmissionErrors,
  getValidationErrors,
  getErrors,
)
const getWarningMessages = createSelector(
  getSubmissionWarnings,
  getValidationWarnings,
  getErrors,
)


const mapStateToProps = (state, ownProps) => ({
  errorMessages: getErrorMessages(state, ownProps),
  warningMessages: getWarningMessages(state, ownProps),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    handleClose: (confirmed) => {
      dispatch(closeModal(ownProps.modalName || ownProps.form, confirmed))
    },
    setModalConfirm: (confirm) => {
      dispatch(setModalConfirm(ownProps.modalName || ownProps.form, confirm))
    },
  }
}


export default reduxForm()(connect(mapStateToProps, mapDispatchToProps)(ReduxFormWrapper))
