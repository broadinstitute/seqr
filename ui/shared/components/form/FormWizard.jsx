import React from 'react'
import PropTypes from 'prop-types'

import FormWrapper from './FormWrapper'

class FormWizard extends React.PureComponent {

  static propTypes = {
    onSubmit: PropTypes.func.isRequired,
    pages: PropTypes.arrayOf(PropTypes.object),
    successMessage: PropTypes.string,
  }

  state = { pageIndex: 0, asyncValues: {}, formSubmitSucceeded: false }

  navigateNext = () => {
    this.setState(prevState => ({
      pageIndex: prevState.pageIndex + 1,
    }))
  }

  navigateBack = () => {
    this.setState(prevState => ({
      pageIndex: prevState.pageIndex - 1, formSubmitSucceeded: false,
    }))
  }

  onPageSubmitSucceeded = values => this.setState(prevState => ({
    asyncValues: { ...prevState.asyncValues, ...(values || {}) },
  }))

  resolvedPageSubmit = () => Promise.resolve()

  setSubmitSucceeded = () => this.setState({ formSubmitSucceeded: true })

  onFormSubmit = (values) => {
    const { onSubmit } = this.props
    const { asyncValues } = this.state
    return onSubmit({ ...asyncValues, ...values })
  }

  render() {
    const { pages, onSubmit, successMessage, ...props } = this.props
    const { pageIndex, formSubmitSucceeded, asyncValues } = this.state

    const { onPageSubmit } = pages[pageIndex]
    const fields = pages[pageIndex].fields.map(
      ({ fieldDecorator, ...keys }) => ({ ...keys, ...fieldDecorator ? fieldDecorator(asyncValues) : {} }),
    )

    const formProps = (pageIndex === pages.length - 1) ? {
      onSubmit: this.onFormSubmit,
      onSubmitSucceeded: this.setSubmitSucceeded,
      successMessage: formSubmitSucceeded ? successMessage : null,
    } : {
      onSubmit: onPageSubmit(this.onPageSubmitSucceeded) || this.resolvedPageSubmit,
      onSubmitSucceeded: this.navigateNext,
      submitButtonText: 'Next',
      submitButtonIcon: 'angle double right',
    }

    const backButtonProps = pageIndex === 0 ? {} : {
      onCancel: this.navigateBack,
      cancelButtonText: 'Back',
      cancelButtonIcon: 'angle double left',
    }

    return (
      <FormWrapper
        {...props}
        {...formProps}
        {...backButtonProps}
        fields={fields}
        showErrorPanel
        hideButtonStatus
      />
    )
  }

}

export default FormWizard
