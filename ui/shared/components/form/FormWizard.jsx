import React from 'react'
import PropTypes from 'prop-types'

import FormWrapper from './FormWrapper'

class FormWizard extends React.PureComponent {

  static propTypes = {
    onSubmit: PropTypes.func.isRequired,
    pages: PropTypes.arrayOf(PropTypes.object),
  }

  state = { pageIndex: 0 }

  navigateNext = () => {
    this.setState(prevState => ({
      pageIndex: prevState.pageIndex + 1,
    }))
  }

  resolvedPageSubmit = () => Promise.resolve()

  render() {
    const { pages, onSubmit, ...props } = this.props
    const { pageIndex } = this.state

    const { fields, onPageSubmit } = pages[pageIndex]

    const formProps = pageIndex === pages.length - 1 ? { onSubmit } : {
      onSubmit: onPageSubmit || this.resolvedPageSubmit,
      onSubmitSucceeded: this.navigateNext,
      submitButtonText: 'Next',
      submitButtonIcon: 'angle double right',
    }

    return (
      <FormWrapper
        showErrorPanel
        {...props}
        {...formProps}
        fields={fields}
      />
    )
  }

}

export default FormWizard
