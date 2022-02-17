import React, { createElement } from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import {
  Field,
  // FieldArray, TODO
  Form as FinalForm,
} from 'react-final-form'
import { Form, Message, Icon, Popup, Confirm } from 'semantic-ui-react'
import flattenDeep from 'lodash/flattenDeep'

import { closeModal, setModalConfirm } from 'redux/utils/modalReducer'
import ButtonPanel from './ButtonPanel'
import { NONE, SUCCEEDED, ERROR } from '../panel/RequestStatus'

export const StyledForm = styled(({ hasSubmitButton, inline, ...props }) => <Form {...props} />)`
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
  requiredEmail: value => (
    /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$/i.test(value) ? undefined : 'Invalid email address'
  ),
}

const nestedObjectValues = obj => (typeof obj === 'object' ? Object.values(obj).map(nestedObjectValues) : obj)

const renderField = (props) => {
  const { fieldComponent = Form.Input, meta: { touched, invalid }, submitForm, input, ...additionalProps } = props
  const { onChange, ...additionalInput } = input
  const onChangeSubmit = submitForm ? (data) => {
    onChange(data)
    submitForm({ [props.input.name]: data })
  } : onChange
  return createElement(fieldComponent, {
    error: touched && invalid, meta: props.meta, onChange: onChangeSubmit, ...additionalInput, ...additionalProps,
  })
}

renderField.propTypes = {
  fieldComponent: PropTypes.elementType,
  meta: PropTypes.object,
  input: PropTypes.object,
  submitForm: PropTypes.func,
}

export const helpLabel = (label, labelHelp) => (
  labelHelp ? (
    <label>
      {label}
      &nbsp;
      <Popup trigger={<Icon name="question circle outline" />} content={labelHelp} size="small" position="top center" />
    </label>
  ) : label
)

const removeField = (fields, i) => (e) => {
  e.preventDefault()
  fields.remove(i)
}

const ArrayFieldItem = ({ addArrayElement, addArrayElementProps, arrayFieldName, singleFieldProps, label, fields }) => (
  <div className="field">
    <label>{label}</label>
    {fields.map((fieldPath, i) => (
      <Field
        key={fieldPath}
        name={arrayFieldName ? `${fieldPath}.${arrayFieldName}` : fieldPath}
        removeField={removeField(fields, i)}
        index={i}
        {...singleFieldProps}
      />
    ))}
    {addArrayElement && createElement(addArrayElement, { addElement: fields.push, ...addArrayElementProps })}
  </div>
)

ArrayFieldItem.propTypes = {
  addArrayElement: PropTypes.object,
  addArrayElementProps: PropTypes.object,
  arrayFieldName: PropTypes.string,
  singleFieldProps: PropTypes.object,
  label: PropTypes.string,
  fields: PropTypes.object,
}

const arrayFieldItem = fieldProps => arrayProps => <ArrayFieldItem {...fieldProps} {...arrayProps} />

export const configuredField = (field, formProps = {}) => {
  const {
    component, name, isArrayField, addArrayElement, addArrayElementProps, arrayFieldName, key, label, labelHelp,
    ...fieldProps
  } = field
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
  return isArrayField ? (
    // <FieldArray TODO
    <Field
      {...baseProps}
      component={arrayFieldItem({ addArrayElement, addArrayElementProps, arrayFieldName, singleFieldProps, label })}
    />
  ) : <Field {...baseProps} {...singleFieldProps} />
}

// TODO take needed props only instead of whole props dict
export const configuredFields = props => props.fields.map(field => configuredField(field, props))

// specify which fields to check for re-rendering entire form
const SUBSCRIPTION = [
  'submitSucceeded',
  'submitFailed',
  'submitting',
  'dirty',
  'dirtySinceLastSubmit',
  'hasSubmitErrors',
  'hasValidationErrors',
  'errors',
  'submitErrors',
].reduce((acc, k) => ({ ...acc, [k]: true }), {})

class ReduxFormWrapper extends React.PureComponent {

  static propTypes = {
    /* A unique string identifier for the form */
    // TODO was required for keeping all the forms in the redux state, now isn't, probably should clean up behavior with modalName
    form: PropTypes.string.isRequired, // eslint-disable-line react/no-unused-prop-types

    /* A unique string identifier for the parent modal. Defaults to the "form" identifier */
    modalName: PropTypes.string, // eslint-disable-line react/no-unused-prop-types

    /* A callback when a valid form is submitted. Will be passed all the form data */
    /* Note that this differs from handleSubmit, which is a redux-form supplied handler that shouldn't be overridden */
    onSubmit: PropTypes.func.isRequired,

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

    liveValidate: PropTypes.bool,
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
    fields: PropTypes.arrayOf(PropTypes.object), // eslint-disable-line react/no-unused-prop-types

    /* React child component class. Mutually exclusive with fields */
    children: PropTypes.node,

    /* Call if submit succeeded */
    onSubmitSucceeded: PropTypes.func,

    setModalConfirm: PropTypes.func,

    initialValues: PropTypes.object,
  }

  static defaultProps = {
    closeOnSuccess: true,
    cancelButtonText: 'Cancel',
    submitButtonText: 'Submit',
  }

  state = { confirming: false }

  // componentDidUpdate(prevProps) {
  //   TODO
  //   const {
  //     onSubmitSucceeded, submitSucceeded, handleClose, confirmCloseIfNotSaved, closeOnSuccess, noModal, dirty,
  //     setModalConfirm: dispatchSetModalConfirm,
  //   } = this.props
  //   if (onSubmitSucceeded && submitSucceeded) {
  //     onSubmitSucceeded()
  //   }
  //   if (submitSucceeded && closeOnSuccess && !noModal) {
  //     handleClose(true)
  //   } else if (confirmCloseIfNotSaved) {
  //     if (dirty && !prevProps.dirty) {
  //       dispatchSetModalConfirm('The form contains unsaved changes. Are you sure you want to close it?')
  //     } else if (!dirty && prevProps.dirty) {
  //       dispatchSetModalConfirm(null)
  //     }
  //   }
  // }

  handledOnSubmit = (values, form, callback) => {
    const { onSubmit } = this.props
    onSubmit(values, form, callback).then(
      () => callback(),
      e => callback({ errors: e.body?.errors || [e.body?.error] || [e.message] }),
    )
  }

  showConfirmDialog = () => this.setState({ confirming: true })

  hideConfirmDialog = () => this.setState({ confirming: false })

  handleUnconfirmedClose = () => {
    const { handleClose } = this.props
    handleClose()
  }

  handleConfirmedSubmit = handleSubmit => () => {
    this.hideConfirmDialog()
    handleSubmit()
  }

  render() {
    const {
      children, confirmDialog, size, loading, submitOnChange, inline, showErrorPanel, successMessage, cancelButtonText,
      submitButtonText, onSubmitSucceeded, noModal, initialValues, liveValidate,
    } = this.props
    const { confirming } = this.state

    const fieldComponents = children || configuredFields(this.props) // TODO only pass needed props

    return (
      <FinalForm onSubmit={this.handledOnSubmit} initialValues={initialValues} subscription={SUBSCRIPTION}>
        {({
          handleSubmit, submitSucceeded, submitFailed, submitting, dirty, hasSubmitErrors, hasValidationErrors,
          errors, submitErrors, dirtySinceLastSubmit,
        }) => {
          const currentFormSubmitFailed = submitFailed && !dirtySinceLastSubmit
          let saveStatus = NONE
          if (submitSucceeded) {
            saveStatus = SUCCEEDED
          } else if (currentFormSubmitFailed) {
            saveStatus = ERROR
          }

          const shouldShowValidationErrors = submitFailed || (liveValidate && dirty)
          let errorMessages
          if (hasSubmitErrors) {
            errorMessages = submitErrors.errors
          } else if (hasValidationErrors && shouldShowValidationErrors) {
            errorMessages = flattenDeep(nestedObjectValues(errors)).filter(err => err)
          }
          const saveErrorMessage = errorMessages?.join('; ') || (currentFormSubmitFailed ? 'Error' : null)

          return (
            <StyledForm
              onSubmit={confirmDialog ? this.showConfirmDialog : handleSubmit}
              size={size}
              loading={submitting || loading}
              hasSubmitButton={!submitOnChange}
              inline={inline}
            >
              {fieldComponents}
              {showErrorPanel && errorMessages && <MessagePanel error visible list={errorMessages} />}
              {submitSucceeded && successMessage && <MessagePanel success visible content={successMessage} />}
              {!submitOnChange && (
                <ButtonPanel
                  cancelButtonText={cancelButtonText}
                  submitButtonText={submitButtonText}
                  saveStatus={saveStatus}
                  saveErrorMessage={saveErrorMessage}
                  handleClose={onSubmitSucceeded || (noModal ? null : this.handleUnconfirmedClose)}
                />
              )}
              <Confirm
                content={confirmDialog}
                open={confirming}
                onCancel={this.hideConfirmDialog}
                onConfirm={this.handleConfirmedSubmit(handleSubmit)}
              />
            </StyledForm>
          )
        }}
      </FinalForm>
    )
  }

}

const mapDispatchToProps = (dispatch, ownProps) => ({
  handleClose: (confirmed) => {
    dispatch(closeModal(ownProps.modalName || ownProps.form, confirmed))
  },
  setModalConfirm: (confirm) => {
    dispatch(setModalConfirm(ownProps.modalName || ownProps.form, confirm))
  },
})

export default connect(null, mapDispatchToProps)(ReduxFormWrapper)
