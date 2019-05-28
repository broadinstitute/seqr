/* eslint-disable jsx-a11y/label-has-for */

import React, { createElement } from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { createSelector } from 'reselect'
import { connect } from 'react-redux'
import { Field, FieldArray, reduxForm, getFormSyncErrors, getFormSyncWarnings } from 'redux-form'
import { Form, Message, Icon, Popup, Confirm } from 'semantic-ui-react'
import flattenDeep from 'lodash/flattenDeep'

import { closeModal, setModalConfirm } from 'redux/utils/modalReducer'
import ButtonPanel from './ButtonPanel'
import RequestStatus from './RequestStatus'

const StyledForm = styled(({ hasSubmitButton, inline, ...props }) => <Form {...props} />)`
  min-height: inherit;
  display: ${props => (props.inline ? 'inline-block' : 'block')};
  padding-bottom: ${props => props.hasSubmitButton && '50px'};
  
  .field.inline {
    display: inline-block;
    padding-right: 1em;
  }
  
  .inline.fields .field:last-child {
    padding-right: 0 !important;
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

export const helpLabel = (label, labelHelp) => (
  labelHelp ?
    <label> {label} <Popup trigger={<Icon name="question circle outline" />} content={labelHelp} size="small" position="top center" /></label>
    : label
)

export const configuredField = (field, formProps = {}) => {
  const { component, name, isArrayField, addArrayElement, addArrayElementProps, arrayFieldName, key, label, labelHelp,
    ...fieldProps } = field
  const baseProps = {
    key: key || name,
    name,
  }
  const singleFieldProps = {
    component: renderField,
    fieldComponent: component,
    submitForm: formProps.submitOnChange ? formProps.onSubmit : null,
    label: helpLabel(label, labelHelp),
    ...fieldProps,
  }
  return isArrayField ?
    <FieldArray {...baseProps} component={({ fields }) =>
      <div className="field">
        <label>{label}</label>
        {fields.map((fieldPath, i) =>
          <Field
            key={fieldPath}
            name={arrayFieldName ? `${fieldPath}.${arrayFieldName}` : fieldPath}
            removeField={(e) => { e.preventDefault(); fields.remove(i) }}
            index={i}
            {...singleFieldProps}
          />)}
        {addArrayElement && createElement(addArrayElement, { addElement: fields.push, ...addArrayElementProps })}
      </div>}
    /> :
    <Field {...baseProps} {...singleFieldProps} />
}

export const configuredFields = props => props.fields.map(field => configuredField(field, props))

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

    /* An optional confirm message to show before saving */
    confirmDialog: PropTypes.string,

    /* Whether or not the form is rendered outside a modal */
    noModal: PropTypes.bool,

    showErrorPanel: PropTypes.bool,
    cancelButtonText: PropTypes.string,
    submitButtonText: PropTypes.string,
    successMessage: PropTypes.string,

    /* Submit the form whenever values change rather than with a submit button */
    submitOnChange: PropTypes.bool,

    /* form size (see https://react.semantic-ui.com/collections/form#form-example-size) */
    size: PropTypes.string,

    /* Whether form should be rendered inline instead of the default block display */
    inline: PropTypes.bool,

    /* Whether the form should be rendered as loading */
    loading: PropTypes.bool,

    /* Array of objects representing the fields to show in the form. */
    /* Each field must have a name and a component, and can have any additional props accepted by redux-form's Field */
    fields: PropTypes.arrayOf(PropTypes.object), //eslint-disable-line react/no-unused-prop-types

    /* React child component class. Mutually exclusive with fields */
    children: PropTypes.node,

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

  constructor(props) {
    super(props)

    this.state = {
      confirming: false,
    }
  }

  handleUnconfirmedClose = () => this.props.handleClose()

  showConfirmDialog = () => this.setState({ confirming: true })

  hideConfirmDialog = () => this.setState({ confirming: false })

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

    const fieldComponents = this.props.children || configuredFields(this.props)

    return (
      <StyledForm
        onSubmit={this.props.confirmDialog ? this.showConfirmDialog : this.props.handleSubmit}
        size={this.props.size}
        loading={this.props.submitting || this.props.loading}
        hasSubmitButton={!this.props.submitOnChange}
        inline={this.props.inline}
      >
        {fieldComponents}
        {this.props.showErrorPanel && ['warning', 'error'].map(key => (
          this.props[`${key}Messages`] && this.props[`${key}Messages`].length > 0 ?
            <MessagePanel key={key} {...{ [key]: true }} visible list={this.props[`${key}Messages`]} /> : null
        ))}
        {this.props.submitSucceeded && this.props.successMessage &&
          <MessagePanel success visible content={this.props.successMessage} />
        }
        {
          !this.props.submitOnChange &&
            <ButtonPanel
              cancelButtonText={this.props.cancelButtonText}
              submitButtonText={this.props.submitButtonText}
              saveStatus={saveStatus}
              saveErrorMessage={saveErrorMessage}
              handleClose={this.props.noModal ? null : this.handleUnconfirmedClose}
            />
        }
        <Confirm
          content={this.props.confirmDialog}
          open={this.state.confirming}
          onCancel={this.hideConfirmDialog}
          onConfirm={() => {
            this.hideConfirmDialog()
            this.props.handleSubmit()
          }}
        />
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
      'fields',
      'showErrorPanel',
      'size',
      'submitting',
      'submitOnChange',
      'cancelButtonText',
      'submitButtonText',
      'dirty',
      'confirmCloseIfNotSaved',
      'confirmDialog',
      'initialValues',
      'children',
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
    if (nextProps.submitSucceeded && nextProps.closeOnSuccess && !nextProps.noModal) {
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

const nestedObjectValues = obj => (typeof obj === 'object' ? Object.values(obj).map(nestedObjectValues) : obj)

const shouldShowValidationErrors = props => props.submitFailed || (props.liveValidate && props.dirty)
const getValidationErrorList = validationErrors =>
  (validationErrors ? flattenDeep(nestedObjectValues(validationErrors)).filter(err => err) : null)
const getValidationErrors = createSelector(
  (state, props) => (shouldShowValidationErrors(props) ? getFormSyncErrors(props.form)(state) : null),
  getValidationErrorList,
)
const getValidationWarnings = createSelector(
  (state, props) => (shouldShowValidationErrors(props) ? getFormSyncWarnings(props.form)(state) : null),
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
