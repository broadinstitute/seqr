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
    /* eslint-disable react/no-unused-prop-types */
    form: PropTypes.string.isRequired,
    /* eslint-disable react/no-unused-prop-types */
    onSubmit: PropTypes.func.isRequired,
    handleClose: PropTypes.func.isRequired,
    closeOnSuccess: PropTypes.bool,
    // confirmCloseIfNotSaved: PropTypes.bool.isRequired, // TODO implement confirm close if unsaved
    cancelButtonText: PropTypes.string,
    submitButtonText: PropTypes.string,
    size: PropTypes.string, // form size (see https://react.semantic-ui.com/collections/form#form-example-size)
    fields: PropTypes.arrayOf(PropTypes.object),
    children: PropTypes.node,
    // props provided by reduxForm, do not pass explicitly
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
