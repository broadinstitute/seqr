import React from 'react'
import PropTypes from 'prop-types'
import { Header } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import FormWrapper from './FormWrapper'

class FormWizard extends React.PureComponent {

  static propTypes = {
    formatSubmitUrl: PropTypes.func.isRequired,
    formatSubmitValues: PropTypes.func,
    onSubmitSuccess: PropTypes.func,
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

  onPageSubmit = (url, formatUrl) => values => (
    new HttpRequestHelper(
      url || formatUrl(values),
      newValues => this.setState(prevState => ({
        asyncValues: { ...prevState.asyncValues, ...(newValues || {}) },
      })),
    ).post(values)
  )

  setSubmitSucceeded = () => this.setState({ formSubmitSucceeded: true })

  onFormSubmit = (values) => {
    const { formatSubmitUrl, formatSubmitValues, onSubmitSuccess } = this.props
    const { asyncValues } = this.state
    const allValues = { ...asyncValues, ...values }
    return new HttpRequestHelper(
      formatSubmitUrl(allValues), onSubmitSuccess,
    ).post(formatSubmitValues ? formatSubmitValues(allValues) : allValues)
  }

  render() {
    const { pages, formatSubmitUrl: f, formatSubmitValues, onSubmitSuccess, successMessage, ...props } = this.props
    const { pageIndex, formSubmitSucceeded } = this.state

    const { fields, submitUrl, formatSubmitUrl } = pages[pageIndex]

    const formProps = (pageIndex === pages.length - 1) ? {
      onSubmit: this.onFormSubmit,
      onSubmitSucceeded: this.setSubmitSucceeded,
    } : {
      onSubmit: this.onPageSubmit(submitUrl, formatSubmitUrl),
      onSubmitSucceeded: this.navigateNext,
      submitButtonText: 'Next',
      submitButtonIcon: 'angle double right',
    }

    const backButtonProps = pageIndex === 0 ? {} : {
      onCancel: this.navigateBack,
      cancelButtonText: 'Back',
      cancelButtonIcon: 'angle double left',
    }

    return (formSubmitSucceeded ? (
      <Header
        icon="check circle"
        content="Request Submitted"
        subheader={successMessage}
      />
    ) : (
      <FormWrapper
        {...props}
        {...formProps}
        {...backButtonProps}
        fields={fields}
        showErrorPanel
        hideButtonStatus
      />
    ))
  }

}

export default FormWizard
