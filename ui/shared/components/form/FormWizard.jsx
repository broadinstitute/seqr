import React from 'react'
import PropTypes from 'prop-types'

import FormWrapper from './FormWrapper'

class FormWizard extends React.PureComponent {

  static propTypes = {
    onSubmit: PropTypes.func.isRequired,
    onClose: PropTypes.func,
    pages: PropTypes.arrayOf(PropTypes.object),
    successMessage: PropTypes.string,
  }

  state = { pageIndex: 0, asyncValues: {}, formSubmitSucceeded: false, responseJson: {} }

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

  setSubmitSucceeded = responseJson => this.setState({ responseJson, formSubmitSucceeded: true })

  onFormSubmit = (values) => {
    const { onSubmit, onClose } = this.props
    const { asyncValues, formSubmitSucceeded, responseJson } = this.state
    if (!formSubmitSucceeded) {
      return onSubmit(this.setSubmitSucceeded)({ ...asyncValues, ...values })
    }
    if (onClose) {
      return onClose(responseJson)
    }
    return null
  }

  getFormProps = () => {
    const { pages, successMessage } = this.props
    const { pageIndex, formSubmitSucceeded } = this.state
    const { onPageSubmit } = pages[pageIndex]

    if (pageIndex === pages.length - 1) { // last page in the Wizard
      if (formSubmitSucceeded) {
        return ({
          onSubmit: this.onFormSubmit,
          submitButtonText: 'Close',
          successMessage,
        })
      }
      return ({
        onSubmit: this.onFormSubmit,
        submitButtonText: 'Submit',
        closeOnSuccess: false,
      })
    }
    return ({ // for pages before the last page.
      onSubmit: onPageSubmit(this.onPageSubmitSucceeded) || this.resolvedPageSubmit,
      onSubmitSucceeded: this.navigateNext,
      submitButtonText: 'Next',
      submitButtonIcon: 'angle double right',
      closeOnSuccess: false,
    })
  }

  render() {
    const { pages, onSubmit, successMessage, ...props } = this.props
    const { pageIndex } = this.state

    const { fields } = pages[pageIndex]

    const formProps = this.getFormProps()

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
