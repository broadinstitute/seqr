import React, { createElement } from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { FormSpy, Form as FinalForm } from 'react-final-form'
import arrayMutators from 'final-form-arrays'
import { Form, Message, Confirm } from 'semantic-ui-react'
import flattenDeep from 'lodash/flattenDeep'

import { closeModal, setModalConfirm } from 'redux/utils/modalReducer'
import ButtonPanel from './ButtonPanel'
import { StyledForm, configuredFields } from './FormHelpers'
import { NONE, SUCCEEDED, ERROR } from '../panel/RequestStatus'

const MessagePanel = styled(Message)`
  margin: 1em 2em !important;
`

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

const SUBMISSION_PANEL_SUBSCRIPTION = [
  'submitSucceeded',
  'submitFailed',
  'dirty',
  'dirtySinceLastSubmit',
  'hasSubmitErrors',
  'hasValidationErrors',
  'errors',
  'submitErrors',
].reduce((acc, k) => ({ ...acc, [k]: true }), {})
const SUBMITTING_SUBSCRIPTION = { submitting: true }
const SUBMIT_SUCCEEDED_SUBSCRIPTION = { submitSucceeded: true }
const DIRTY_SUBSCRIPTION = { dirty: true }

class FormWrapper extends React.PureComponent {

  static propTypes = {
    /* A unique string identifier for the parent modal */
    modalName: PropTypes.string, // eslint-disable-line react/no-unused-prop-types

    /* A callback when a valid form is submitted. Will be passed all the form data */
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
    cancelButtonIcon: PropTypes.string,
    submitButtonText: PropTypes.string,
    submitButtonIcon: PropTypes.string,
    successMessage: PropTypes.string,
    hideButtonStatus: PropTypes.bool,

    /* Submit the form whenever values change rather than with a submit button */
    submitOnChange: PropTypes.bool,

    /* form size (see https://react.semantic-ui.com/collections/form#form-example-size) */
    size: PropTypes.string,

    /* Whether form should be rendered inline instead of the default block display */
    inline: PropTypes.bool,
    verticalAlign: PropTypes.string,

    /* Whether the form should be rendered as loading */
    loading: PropTypes.bool,

    /* Array of objects representing the fields to show in the form. */
    /* Each field must have a name and a component, and can have any extra props accepted by react-final-form's Field */
    fields: PropTypes.arrayOf(PropTypes.object), // eslint-disable-line react/no-unused-prop-types

    /* React child component class. Mutually exclusive with fields */
    children: PropTypes.node,

    /* Call if submit succeeded */
    onSubmitSucceeded: PropTypes.func,

    onCancel: PropTypes.func,

    setModalConfirm: PropTypes.func,

    /* Optional submission error generated outside the form */
    submissionError: PropTypes.string,

    initialValues: PropTypes.object,

    /* decorators for final-form-calculate to calculate field values */
    decorators: PropTypes.arrayOf(PropTypes.func),
  }

  static defaultProps = {
    closeOnSuccess: true,
    cancelButtonText: 'Cancel',
    submitButtonText: 'Submit',
  }

  state = { confirming: false, submitCallback: null }

  componentDidUpdate(prevProps) {
    const { submissionError, loading } = this.props
    const { submitCallback } = this.state
    if (submitCallback && loading !== prevProps.loading) {
      const resolved = submissionError && { errors: [submissionError] }
      submitCallback(resolved)
    }
  }

  onSubmitSucceededChange = ({ submitSucceeded }) => {
    const { onSubmitSucceeded, handleClose, closeOnSuccess, noModal } = this.props
    if (onSubmitSucceeded && submitSucceeded) {
      onSubmitSucceeded()
    }
    if (submitSucceeded && closeOnSuccess && !noModal) {
      handleClose(true)
    }
  }

  onDirtyChange = ({ dirty }) => {
    const { setModalConfirm: dispatchSetModalConfirm } = this.props
    if (dirty) {
      dispatchSetModalConfirm('The form contains unsaved changes. Are you sure you want to close it?')
    } else {
      dispatchSetModalConfirm(null)
    }
  }

  handledOnSubmit = (values, form, callback) => {
    const { onSubmit, loading } = this.props
    if (loading !== undefined) {
      this.setState({ submitCallback: callback })
    }
    onSubmit(values, form, callback)?.then(
      () => callback(),
      e => callback({ errors: e.body?.errors || (e.body?.error ? [e.body.error] : null) || [e.message] }),
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

  renderSubmissionPanel = ({
    submitSucceeded, submitFailed, hasSubmitErrors, hasValidationErrors, errors, submitErrors,
    dirty, dirtySinceLastSubmit,
  }) => {
    const {
      submitOnChange, showErrorPanel, successMessage, cancelButtonText, submitButtonText, submitButtonIcon,
      onCancel, noModal, liveValidate, hideButtonStatus, cancelButtonIcon,
    } = this.props

    const currentFormSubmitFailed = submitFailed && !dirtySinceLastSubmit
    let saveStatus = NONE
    if (!hideButtonStatus && submitSucceeded) {
      saveStatus = SUCCEEDED
    } else if (!hideButtonStatus && currentFormSubmitFailed) {
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

    return [
      showErrorPanel && errorMessages && <MessagePanel key="errorPanel" error visible list={errorMessages} />,
      submitSucceeded && successMessage && <MessagePanel key="infoPanel" success visible content={successMessage} />,
      !submitOnChange && (
        <ButtonPanel
          key="buttonPanel"
          cancelButtonText={cancelButtonText}
          cancelButtonIcon={cancelButtonIcon}
          submitButtonText={submitButtonText}
          submitButtonIcon={submitButtonIcon}
          saveStatus={saveStatus}
          saveErrorMessage={saveErrorMessage}
          handleClose={onCancel || (noModal ? null : this.handleUnconfirmedClose)}
        />
      ),
    ]
  }

  render() {
    const {
      children, confirmDialog, size, loading, submitOnChange, inline, onSubmitSucceeded, noModal, initialValues,
      closeOnSuccess, confirmCloseIfNotSaved, decorators, verticalAlign,
    } = this.props
    const { confirming } = this.state

    const fieldComponents = children || configuredFields(this.props)

    return (
      <FinalForm
        onSubmit={this.handledOnSubmit}
        initialValues={initialValues}
        subscription={SUBMITTING_SUBSCRIPTION}
        mutators={arrayMutators}
        decorators={decorators}
      >
        {({ handleSubmit, submitting }) => (
          <StyledForm
            onSubmit={confirmDialog ? this.showConfirmDialog : handleSubmit}
            size={size}
            loading={loading === undefined ? submitting : loading}
            hasSubmitButton={!submitOnChange}
            inline={inline}
            verticalAlign={verticalAlign}
          >
            {fieldComponents}
            <FormSpy subscription={SUBMISSION_PANEL_SUBSCRIPTION} render={this.renderSubmissionPanel} />
            <Confirm
              content={confirmDialog}
              open={confirming}
              onCancel={this.hideConfirmDialog}
              onConfirm={this.handleConfirmedSubmit(handleSubmit)}
            />
            {(onSubmitSucceeded || (closeOnSuccess && !noModal)) &&
              <FormSpy subscription={SUBMIT_SUCCEEDED_SUBSCRIPTION} onChange={this.onSubmitSucceededChange} />}
            {confirmCloseIfNotSaved && <FormSpy subscription={DIRTY_SUBSCRIPTION} onChange={this.onDirtyChange} />}
          </StyledForm>
        )}
      </FinalForm>
    )
  }

}

const mapDispatchToProps = (dispatch, ownProps) => ({
  handleClose: (confirmed) => {
    dispatch(closeModal(ownProps.modalName, confirmed))
  },
  setModalConfirm: (confirm) => {
    dispatch(setModalConfirm(ownProps.modalName, confirm))
  },
})

export default connect(null, mapDispatchToProps)(FormWrapper)
