import React, { createElement } from 'react'
import PropTypes from 'prop-types'
import { Field, reduxForm } from 'redux-form'
import { Form } from 'semantic-ui-react'

import ButtonPanel from 'shared/components/form/ButtonPanel'
import RequestStatus from 'shared/components/form/RequestStatus'

export const validators = {
  required: value => (value ? undefined : 'Required'),
}

const renderField = (props) => {
  const { fieldComponent = Form.Input, meta: { touched, invalid }, input, ...additionalProps } = props
  return createElement(fieldComponent, { error: touched && invalid, ...input, ...additionalProps })
}

renderField.propTypes = {
  fieldComponent: PropTypes.element,
  meta: PropTypes.object,
  input: PropTypes.object,
}

const ReduxFormWrapper = (props) => {
  const { fields, submitting, submitFailed, submitSucceeded, invalid, error, handleSubmit, handleClose, size,
    cancelButtonText = 'Cancel', submitButtonText = 'Submit' } = props
  let saveStatus = RequestStatus.NONE
  if (submitSucceeded) {
    saveStatus = RequestStatus.SUCCEEDED
  } else if (submitFailed) {
    saveStatus = RequestStatus.ERROR
  }
  const saveErrorMessage = error || (invalid ? 'Invalid input' : 'Unknown')

  const fieldComponents = fields.map(({ component, name, ...fieldProps }) =>
    <Field key={name} name={name} component={renderField} fieldComponent={component} {...fieldProps} />,
  )

  return (
    <Form onSubmit={handleSubmit} size={size} loading={submitting}>
      {fieldComponents}
      <ButtonPanel
        cancelButtonText={cancelButtonText}
        submitButtonText={submitButtonText}
        saveStatus={saveStatus}
        saveErrorMessage={saveErrorMessage}
        handleClose={handleClose}
      />
    </Form>
  )
}

ReduxFormWrapper.propTypes = {
  fields: PropTypes.array.isRequired,
  /* eslint-disable react/no-unused-prop-types */
  form: PropTypes.string.isRequired,
  /* eslint-disable react/no-unused-prop-types */
  onSubmit: PropTypes.func,
  handleClose: PropTypes.func,
  // confirmCloseIfNotSaved: PropTypes.bool.isRequired, // TODO implement confirm close unsaved
  cancelButtonText: PropTypes.string,
  submitButtonText: PropTypes.string,
  size: PropTypes.string, // form size (see https://react.semantic-ui.com/collections/form#form-example-size)
  // props provided by reduxForm, do not pass explicitly
  submitting: PropTypes.bool,
  submitFailed: PropTypes.bool,
  submitSucceeded: PropTypes.bool,
  invalid: PropTypes.bool,
  error: PropTypes.string,
  handleSubmit: PropTypes.func,
}

export default reduxForm()(ReduxFormWrapper)
