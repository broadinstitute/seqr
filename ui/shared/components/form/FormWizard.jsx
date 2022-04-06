import React, { createElement } from 'react'
import PropTypes from 'prop-types'
import { FormSpy, Form as FinalForm } from 'react-final-form'
import { Form, Message, Button } from 'semantic-ui-react'
import flattenDeep from 'lodash/flattenDeep'

import { StyledForm, configuredFields } from './FormHelpers'

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

const SUBMISSION_ERROR_PANEL_SUBSCRIPTION = [
  'hasSubmitErrors',
  'hasValidationErrors',
  'errors',
  'submitErrors',
  'submitFailed',
].reduce((acc, k) => ({ ...acc, [k]: true }), {})
const SUBMITTING_SUBSCRIPTION = { submitting: true }

class FormWizard extends React.PureComponent {

  static propTypes = {
    onSubmit: PropTypes.func.isRequired,
    size: PropTypes.string,
    pages: PropTypes.arrayOf(PropTypes.object),
    initialValues: PropTypes.object,
  }

  state = { pageIndex: 0 }

  handledOnSubmit = (values, form, callback) => {
    const { onSubmit, pages } = this.props
    const { pageIndex } = this.state
    const nextPageIndex = pageIndex + 1

    const navigateNextPage = () => {
      this.setState({ pageIndex: nextPageIndex })
      callback()
    }

    const handleAsyncError = e => callback({ errors: e.body?.errors || [e.body?.error] || [e.message] })

    if (nextPageIndex === pages.length) {
      onSubmit(values).then(() => callback(), handleAsyncError)
    } else if (pages[pageIndex].onSubmit) {
      pages[pageIndex].onSubmit(values).then(navigateNextPage, handleAsyncError)
    } else {
      navigateNextPage()
    }
  }

  renderSubmissionErrors = ({ hasSubmitErrors, hasValidationErrors, errors, submitErrors, submitFailed }) => {
    let errorMessages
    if (hasSubmitErrors) {
      errorMessages = submitErrors.errors
    } else if (submitFailed && hasValidationErrors) {
      errorMessages = flattenDeep(nestedObjectValues(errors)).filter(err => err)
    }
    return (errorMessages && <Message error visible list={errorMessages} />) || null
  }

  render() {
    const { pages, size, initialValues } = this.props
    const { pageIndex } = this.state

    const isFinalPage = pageIndex === pages.length - 1
    const page = pages[pageIndex]
    const fieldComponents = configuredFields(page)

    return (
      <FinalForm
        onSubmit={this.handledOnSubmit}
        initialValues={initialValues}
        size={size}
        subscription={SUBMITTING_SUBSCRIPTION}
      >
        {({ handleSubmit, submitting }) => (
          <StyledForm
            onSubmit={handleSubmit}
            loading={submitting}
            hasSubmitButton
          >
            {fieldComponents}
            <FormSpy subscription={SUBMISSION_ERROR_PANEL_SUBSCRIPTION} render={this.renderSubmissionErrors} />
            <Button
              type="submit"
              primary
              floated="right"
              icon={!isFinalPage && 'angle double right'}
              labelPosition={!isFinalPage && 'right'}
              content={isFinalPage ? 'Submit' : 'Next'}
            />
          </StyledForm>
        )}
      </FinalForm>
    )
  }

}

export default FormWizard
