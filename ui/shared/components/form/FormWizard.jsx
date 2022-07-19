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
      pageIndex: prevState.pageIndex - 1,
    }))
  }

  onPageSubmitSucceeded = values => this.setState(prevState => ({
    asyncValues: { ...prevState.asyncValues, ...(values || {}) },
  }))

  resolvedPageSubmit = () => Promise.resolve()

  onFormSubmitSucceeded = () => this.setState({ formSubmitSucceeded: true })

  onFormSubmit = (values) => {
    const { onSubmit } = this.props
    const { asyncValues } = this.state
    return onSubmit({ ...asyncValues, ...values }, this.onFormSubmitSucceeded)
  }

  render() {
    const { pages, onSubmit, successMessage, ...props } = this.props
    const { pageIndex, formSubmitSucceeded } = this.state

    const { fields, onPageSubmit } = pages[pageIndex]

    const lastPageProps = formSubmitSucceeded ? {
      onSubmit: this.resolvedPageSubmit,
      submitButtonText: 'Close',
      successMessage,
    } : {
      onSubmit: this.onFormSubmit,
      submitButtonText: 'Submit',
      closeOnSuccess: false,
    }

    const formProps = pageIndex === pages.length - 1 ? lastPageProps : {
      onSubmit: onPageSubmit(this.onPageSubmitSucceeded) || this.resolvedPageSubmit,
      onSubmitSucceeded: this.navigateNext,
      submitButtonText: 'Next',
      submitButtonIcon: 'angle double right',
      closeOnSuccess: false,
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
