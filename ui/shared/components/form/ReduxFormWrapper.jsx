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
  fieldComponent: PropTypes.func,
  meta: PropTypes.object,
  input: PropTypes.object,
}

class ReduxFormWrapper extends React.Component {

  static propTypes = {
    /* A unique string identifier for the form */
    form: PropTypes.string.isRequired,

    /* A callback when a valid form is submitted. Will be passed all the form data */
    /* Note that this is different from handleSubmit, which is a redux-form supplied handler that should never be overridden */
    onSubmit: PropTypes.func.isRequired,

    /* A callback for when the cancel button is selected */
    handleClose: PropTypes.func.isRequired,

    /* Whether or not to close the parent modal once form submission succeeds. Defaults to true */
    closeOnSuccess: PropTypes.bool,

    // confirmCloseIfNotSaved: PropTypes.bool.isRequired, // TODO implement confirm close if unsaved
    cancelButtonText: PropTypes.string,
    submitButtonText: PropTypes.string,

    /* form size (see https://react.semantic-ui.com/collections/form#form-example-size) */
    size: PropTypes.string,

    /* Array of objects representing the fields to show in the form. */
    /* Each field must have a name and a component, and can have any additional props accepted by redux-form's Field */
    fields: PropTypes.arrayOf(PropTypes.object),

    /* React child components. Mutually exclusive with fields */
    children: PropTypes.node,

    /*  These props are added by redux-form and should never be passed explicitly */
    submitting: PropTypes.bool,
    submitFailed: PropTypes.bool,
    submitSucceeded: PropTypes.bool,
    invalid: PropTypes.bool,
    error: PropTypes.string,
    handleSubmit: PropTypes.func,
  }

  static defaultProps = {
    closeOnSuccess: true,
    cancelButtonText: 'Cancel',
    submitButtonText: 'Submit',
  }

  render() {
    let saveStatus = RequestStatus.NONE
    if (this.props.submitSucceeded) {
      saveStatus = RequestStatus.SUCCEEDED
    } else if (this.props.submitFailed) {
      saveStatus = RequestStatus.ERROR
    }
    const saveErrorMessage = this.props.error || (this.props.invalid ? 'Invalid input' : 'Unknown')

    const fieldComponents = this.props.children || this.props.fields.map(({ component, name, ...fieldProps }) =>
      <Field key={name} name={name} component={renderField} fieldComponent={component} {...fieldProps} />,
    )

    return (
      <Form onSubmit={this.props.handleSubmit} size={this.props.size} loading={this.props.submitting}>
        {fieldComponents}
        <ButtonPanel
          cancelButtonText={this.props.cancelButtonText}
          submitButtonText={this.props.submitButtonText}
          saveStatus={saveStatus}
          saveErrorMessage={saveErrorMessage}
          handleClose={this.props.handleClose}
        />
      </Form>
    )
  }

  componentWillUpdate(nextProps) {
    if (nextProps.submitSucceeded && nextProps.closeOnSuccess) {
      this.props.handleClose()
    }
  }
}

export default reduxForm()(ReduxFormWrapper)
